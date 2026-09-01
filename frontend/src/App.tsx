import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatMessage } from './components/ChatMessage';
import { StatusIndicator } from './components/StatusIndicator';
import { SourceModal } from './components/SourceModal';
import { DocumentMetadata, HealthResponse, Message, SourceReference } from './types';
import { fetchDocuments, fetchHealth, deleteDocument, streamChat } from './services/api';
import {
  Send,
  Square,
  Sparkles,
  Trash2,
  BrainCircuit,
  MessageSquare,
  HelpCircle,
  FileSearch,
} from 'lucide-react';

export const App: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [useRerank, setUseRerank] = useState(true);
  const [activeSource, setActiveSource] = useState<SourceReference | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Carregar documentos e status inicial
  useEffect(() => {
    loadHealth();
    loadDocuments();
  }, []);

  // Auto-scroll ao receber novas mensagens
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadHealth = async () => {
    setLoadingHealth(true);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (e) {
      console.error('Erro ao carregar status:', e);
    } finally {
      setLoadingHealth(false);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await fetchDocuments();
      setDocuments(data.documents);
    } catch (e) {
      console.error('Erro ao carregar documentos:', e);
    }
  };

  const handleUploadSuccess = (newDoc: DocumentMetadata) => {
    setDocuments((prev) => [newDoc, ...prev.filter((d) => d.doc_id !== newDoc.doc_id)]);
    loadHealth();
  };

  const handleDeleteDoc = async (docId: string) => {
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
      setSelectedDocIds((prev) => prev.filter((id) => id !== docId));
      loadHealth();
    } catch (e) {
      console.error('Erro ao deletar documento:', e);
    }
  };

  const handleToggleDoc = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleSelectAllDocs = () => {
    setSelectedDocIds(documents.map((d) => d.doc_id));
  };

  const handleClearDocSelection = () => {
    setSelectedDocIds([]);
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = textToSend || input.trim();
    if (!query || isGenerating) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    const assistantMsgId = (Date.now() + 1).toString();
    const placeholderAssistant: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      sources: [],
      timestamp: new Date().toISOString(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, placeholderAssistant]);
    setInput('');
    setIsGenerating(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Histórico para envio
    const historyPayload = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    await streamChat({
      message: query,
      history: historyPayload,
      doc_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      useRerank,
      signal: abortController.signal,
      onSources: (sources) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, sources } : m))
        );
      },
      onToken: (token) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId ? { ...m, content: m.content + token } : m
          )
        );
      },
      onDone: () => {
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMsgId ? { ...m, isStreaming: false } : m))
        );
        setIsGenerating(false);
        abortControllerRef.current = null;
      },
      onError: (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: m.content + `\n\n⚠️ ${err}`, isStreaming: false }
              : m
          )
        );
        setIsGenerating(false);
        abortControllerRef.current = null;
      },
    });
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleClearChat = () => {
    if (confirm('Deseja limpar todo o histórico da conversa atual?')) {
      setMessages([]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const suggestions = [
    'Resuma os principais pontos dos documentos carregados.',
    'Quais são os requisitos técnicos e arquiteturais descritos?',
    'Liste os pontos de atenção e possíveis riscos.',
    'Encontre dados estatísticos ou métricas mencionadas.',
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Sidebar Lateral */}
      <Sidebar
        documents={documents}
        selectedDocIds={selectedDocIds}
        onToggleDoc={handleToggleDoc}
        onSelectAllDocs={handleSelectAllDocs}
        onClearDocSelection={handleClearDocSelection}
        onDeleteDoc={handleDeleteDoc}
        onUploadSuccess={handleUploadSuccess}
        useRerank={useRerank}
        onToggleRerank={setUseRerank}
      />

      {/* Área Principal */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-gradient-to-b from-[#0e1320] to-[#0a0d14]">
        {/* Status Superior */}
        <StatusIndicator health={health} loading={loadingHealth} onRefresh={loadHealth} />

        {/* Barra Superior do Chat */}
        <div className="px-6 py-3 border-b border-slate-800/80 bg-slate-900/40 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MessageSquare className="w-4 h-4 text-indigo-400" />
            <span className="text-xs font-semibold text-slate-200">Chat com a Base</span>
            {selectedDocIds.length > 0 && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
                Filtro: {selectedDocIds.length} doc(s)
              </span>
            )}
          </div>

          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="flex items-center space-x-1 px-2.5 py-1 text-xs text-slate-400 hover:text-rose-300 hover:bg-slate-800 rounded-lg transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Limpar Conversa</span>
            </button>
          )}
        </div>

        {/* Conteúdo do Chat / Mensagens */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-xl mx-auto px-4 text-center">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 shadow-xl shadow-indigo-500/5">
                <BrainCircuit className="w-7 h-7" />
              </div>
              <h2 className="text-lg font-bold text-slate-100 mb-1">
                Converse com seus Documentos
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed mb-6">
                Faça o upload de PDFs, notas em Markdown ou arquivos de texto na barra lateral e
                faça perguntas em linguagem natural. O RAG recupera e cita os trechos exatos.
              </p>

              {/* Sugestões de Perguntas */}
              <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {suggestions.map((sug, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(sug)}
                    className="p-3 rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 hover:border-indigo-500/30 text-xs text-slate-300 hover:text-white transition flex items-start space-x-2 group"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                    <span className="leading-snug">{sug}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/30">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} onOpenSource={setActiveSource} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Barra de Input / Envio */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/60">
          <div className="max-w-4xl mx-auto relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                documents.length === 0
                  ? 'Envie um documento primeiro na barra lateral...'
                  : 'Faça uma pergunta sobre seus documentos (Enter para enviar, Shift+Enter para nova linha)...'
              }
              rows={2}
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-4 pr-24 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 focus:ring-1 focus:ring-indigo-500/50 resize-none transition"
            />

            <div className="absolute right-3 bottom-4 flex items-center space-x-1.5">
              {isGenerating ? (
                <button
                  onClick={handleStopGeneration}
                  className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium shadow-md transition"
                >
                  <Square className="w-3 h-3 fill-current" />
                  <span>Parar</span>
                </button>
              ) : (
                <button
                  onClick={() => handleSendMessage()}
                  disabled={!input.trim()}
                  className="flex items-center space-x-1 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white text-xs font-medium shadow-md transition"
                >
                  <span>Enviar</span>
                  <Send className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          <div className="max-w-4xl mx-auto mt-2 flex items-center justify-between text-[10px] text-slate-500 px-1">
            <span>
              Modelo de chat, embeddings e rerank conectados via <strong>llama-server</strong> local
            </span>
            <span>DocMind • RAG 2-Estágios</span>
          </div>
        </div>
      </main>

      {/* Modal de Detalhes da Fonte Citada */}
      <SourceModal source={activeSource} onClose={() => setActiveSource(null)} />
    </div>
  );
};
export default App;
