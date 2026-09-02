export interface DocumentMetadata {
  doc_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  sha256: string;
  total_chunks: number;
  total_pages?: number | null;
  created_at: string;
}

export interface DocumentListResponse {
  documents: DocumentMetadata[];
  total_documents: number;
  total_chunks: number;
}

export interface SourceReference {
  doc_id: string;
  filename: string;
  chunk_index: number;
  page_number?: number | null;
  snippet: string;
  score?: number | null;
  rerank_score?: number | null;
}

export interface EndpointStatus {
  name: string;
  url: string;
  online: boolean;
  latency_ms?: number | null;
  details?: string | null;
}

export interface HealthResponse {
  status: string;
  chat_endpoint: EndpointStatus;
  embed_endpoint: EndpointStatus;
  rerank_endpoint: EndpointStatus;
  total_indexed_documents: number;
  total_indexed_chunks: number;
}

export interface Message {
  id: string;
  session_id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: SourceReference[];
  timestamp?: string;
  created_at?: string;
  isStreaming?: boolean;
}

export interface SessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

