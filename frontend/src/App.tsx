import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  Brain,
  MessageSquare,
  ShieldCheck,
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
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isUserScrolledUp = useRef(false);

  // Carregar documentos e status inicial
  useEffect(() => {
    loadHealth();
    loadDocuments();
  }, []);

  // Monitorar rolagem manual do usuário
  const handleScroll = () => {
    if (!chatContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    isUserScrolledUp.current = distanceFromBottom > 120;
  };

  // Auto-scroll inteligente (só rola se o usuário estiver no fim da conversa)
  useEffect(() => {
    if (!isUserScrolledUp.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const loadHealth = async () => {
    setLoadingHealth(true);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (e) {
      console.error('Erro ao verificar saúde dos endpoints:', e);
    } finally {
      setLoadingHealth(false);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await fetchDocuments();
      setDocuments(data.documents);
    } catch (e) {
      console.error('Erro ao listar documentos:', e);
    }
  };

  const handleUploadSuccess = useCallback((newDoc: DocumentMetadata) => {
    setDocuments((prev) => [newDoc, ...prev.filter((d) => d.doc_id !== newDoc.doc_id)]);
    loadHealth();
  }, []);

  const handleDeleteDoc = useCallback(async (docId: string) => {
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
      setSelectedDocIds((prev) => prev.filter((id) => id !== docId));
      loadHealth();
    } catch (e) {
      console.error('Erro ao deletar documento:', e);
    }
  }, []);

  const handleToggleDoc = useCallback((docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  }, []);

  const handleSelectAllDocs = useCallback(() => {
    setSelectedDocIds(documents.map((d) => d.doc_id));
  }, [documents]);

  const handleClearDocSelection = useCallback(() => {
    setSelectedDocIds([]);
  }, []);

  const handleSendMessage = async (textToSend?: string) => {
    const query = textToSend || input.trim();
    if (!query || isGenerating) return;

    isUserScrolledUp.current = false;

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

    const historyPayload = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    await streamChat({
      message: query,
      history: historyPayload,
      doc_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      use_rerank: useRerank,
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
    'Quais são as principais conclusões dos documentos?',
    'Resuma os conceitos e requisitos técnicos apresentados.',
    'Quais são as diferenças e comparações destacadas?',
    'Liste os exemplos práticos de código citados.',
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#070a10]">
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

      {/* Área Principal de Trabalho */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-gradient-to-b from-[#090d16] via-[#070a10] to-[#05070c]">
        {/* Status Superior dos Serviços */}
        <StatusIndicator health={health} loading={loadingHealth} onRefresh={loadHealth} />

        {/* Barra Superior do Chat */}
        <div className="px-6 py-3 border-b border-slate-800/80 bg-[#080c14]/80 flex items-center justify-between backdrop-blur-sm">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-xs font-bold text-slate-200">Área de Pesquisa & Chat</h2>
              <p className="text-[10px] text-slate-400 font-mono">
                {selectedDocIds.length > 0
                  ? `Consultando ${selectedDocIds.length} documento(s) selecionado(s)`
                  : 'Consultando todos os documentos da base'}
              </p>
            </div>
          </div>

          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="flex items-center space-x-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-rose-300 hover:bg-slate-800/60 rounded-lg border border-slate-800 transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Limpar Histórico</span>
            </button>
          )}
        </div>

        {/* Lista de Mensagens do Chat */}
        <div
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto"
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-xl mx-auto px-4 text-center py-10">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-indigo-700/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mb-4 shadow-[0_0_25px_rgba(99,102,241,0.15)]">
                <Brain className="w-7 h-7" />
              </div>
              <h2 className="text-lg font-bold text-slate-100 tracking-tight mb-1.5">
                DocMind AI Workstation
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed max-w-md mb-8">
                Pesquise, cruze referências e extraia respostas precisas de PDFs, apostilas e notas com busca vetorial e reranking local.
              </p>

              {/* Sugestões de Perguntas */}
              <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
                {suggestions.map((sug, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(sug)}
                    className="p-3.5 rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 hover:border-indigo-500/40 text-xs text-slate-300 hover:text-white transition flex items-start space-x-2.5 group shadow-sm"
                  >
                    <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
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
        <div className="p-4 border-t border-slate-800/80 bg-[#080c14]/90 backdrop-blur-md">
          <div className="max-w-4xl mx-auto relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                documents.length === 0
                  ? 'Faça o upload de um documento na barra lateral para começar...'
                  : 'Faça uma pergunta sobre a sua base local (Enter para enviar, Shift+Enter para quebra)...'
              }
              rows={2}
              className="w-full bg-slate-950/90 border border-slate-800/80 rounded-xl pl-4 pr-24 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 focus:ring-1 focus:ring-indigo-500/40 resize-none transition shadow-inner font-sans"
            />

            <div className="absolute right-3 bottom-4 flex items-center space-x-2">
              {isGenerating ? (
                <button
                  onClick={handleStopGeneration}
                  className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-md transition"
                >
                  <Square className="w-3 h-3 fill-current" />
                  <span>Parar</span>
                </button>
              ) : (
                <button
                  onClick={() => handleSendMessage()}
                  disabled={!input.trim()}
                  className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white text-xs font-semibold shadow-[0_0_12px_rgba(99,102,241,0.3)] transition"
                >
                  <span>Enviar</span>
                  <Send className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          <div className="max-w-4xl mx-auto mt-2 flex items-center justify-between text-[11px] text-slate-500 font-mono px-1">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span>Privacidade Total • RAG Local 2-Estágios</span>
            </span>
            <span>DocMind • llama.cpp Engine</span>
          </div>
        </div>
      </main>

      {/* Modal de Detalhes da Fonte Citada */}
      <SourceModal source={activeSource} onClose={() => setActiveSource(null)} />
    </div>
  );
};

export default App;
