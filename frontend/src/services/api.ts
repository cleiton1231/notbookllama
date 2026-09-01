import { DocumentListResponse, HealthResponse, SourceReference, DocumentMetadata } from '../types';

const API_BASE = '/api';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Falha ao obter status: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentListResponse> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) {
    throw new Error(`Falha ao listar documentos: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadDocument(file: File): Promise<{ message: string; document: DocumentMetadata }> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Erro no upload' }));
    throw new Error(errorData.detail || 'Erro ao enviar documento');
  }

  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${docId}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    throw new Error(`Erro ao excluir documento: ${res.statusText}`);
  }
}

export interface StreamChatParams {
  message: string;
  history: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>;
  doc_ids?: string[];
  use_rerank?: boolean;
  signal?: AbortSignal;
  onSources: (sources: SourceReference[]) => void;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (error: string) => void;
}

export async function streamChat({
  message,
  history,
  doc_ids,
  use_rerank = true,
  signal,
  onSources,
  onToken,
  onDone,
  onError,
}: StreamChatParams): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        history,
        doc_ids,
        use_rerank,
        temperature: 0.3,
      }),
      signal,
    });

    if (!response.ok) {
      const err = await response.text();
      onError(`Erro na requisição (${response.status}): ${err}`);
      return;
    }

    if (!response.body) {
      onError('Corpo de resposta vazio do servidor');
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = '';

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          const dataStr = line.slice(5).trim();
          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            if (currentEvent === 'sources') {
              onSources(data.sources || []);
            } else if (currentEvent === 'token') {
              onToken(data.token || '');
            } else if (currentEvent === 'error') {
              onError(data.error || 'Erro desconhecido');
            } else if (currentEvent === 'done') {
              onDone();
            }
          } catch (e) {
            console.error('Erro ao decodificar JSON do evento SSE:', dataStr, e);
          }
        }
      }
    }

    onDone();
  } catch (error: any) {
    if (error.name === 'AbortError') {
      console.log('Stream abortado pelo usuário.');
      onDone();
    } else {
      onError(error.message || 'Falha na conexão de streaming');
    }
  }
}
