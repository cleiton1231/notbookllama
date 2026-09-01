import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatMessage } from './components/ChatMessage';
import { StatusIndicator } from './components/StatusIndicator';
import { SourceModal } from './components/SourceModal';
import { DocumentMetadata, HealthResponse, Message, SourceReference } from './types';
import { fetchDocuments, fetchHealth, deleteDocument, streamChat } from './services/api';
import {
  ArrowUp,
  Square,
  Sparkles,
  RotateCcw,
  BookOpen,
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

  useEffect(() => {
    loadHealth();
    loadDocuments();
  }, []);

  const handleScroll = () => {
    if (!chatContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    isUserScrolledUp.current = distanceFromBottom > 100;
  };

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
      console.error('Erro ao verificar status:', e);
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

  const handleNewChat = useCallback(() => {
    if (messages.length > 0) {
      if (confirm('Iniciar uma nova conversa e limpar o histórico atual?')) {
        setMessages([]);
      }
    }
  }, [messages.length]);

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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const suggestions = [
    'Quais são os pontos e conclusões centrais do documento?',
    'Explique as diferenças e comparações destacadas no texto.',
    'Quais são os requisitos técnicos e definições apresentadas?',
    'Resuma os exemplos práticos e códigos fornecidos.',
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#191919] text-[#ececec]">
      {/* Sidebar Lateral */}
      <Sidebar
        documents={documents}
        selectedDocIds={selectedDocIds}
        onToggleDoc={handleToggleDoc}
        onSelectAllDocs={handleSelectAllDocs}
        onClearDocSelection={handleClearDocSelection}
        onDeleteDoc={handleDeleteDoc}
        onUploadSuccess={handleUploadSuccess}
        onNewChat={handleNewChat}
        useRerank={useRerank}
        onToggleRerank={setUseRerank}
      />

      {/* Área Principal de Chat */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-[#191919] relative">
        {/* Top Minimal Bar */}
        <header className="h-14 px-6 border-b border-white/[0.06] flex items-center justify-between shrink-0 bg-[#191919]/90 backdrop-blur-md z-10">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-zinc-300">
              {selectedDocIds.length > 0
                ? `${selectedDocIds.length} documento(s) selecionado(s)`
                : 'Todos os documentos'}
            </span>
          </div>

          <div className="flex items-center space-x-4">
            <StatusIndicator health={health} loading={loadingHealth} onRefresh={loadHealth} />

            {messages.length > 0 && (
              <button
                onClick={handleNewChat}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition"
                title="Limpar conversa"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            )}
          </div>
        </header>

        {/* Scrollable Messages Area */}
        <div
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto pb-40"
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto px-6 text-center py-12">
              <div className="w-12 h-12 rounded-2xl bg-[#da7756]/15 border border-[#da7756]/30 text-coral-400 flex items-center justify-center mb-6 shadow-sm">
                <Sparkles className="w-6 h-6" />
              </div>
              <h1 className="text-2xl font-semibold text-white tracking-tight mb-2">
                Como posso ajudar com seus documentos?
              </h1>
              <p className="text-sm text-zinc-400 max-w-md mb-10 leading-relaxed">
                Faça perguntas, compare dados ou extraia explicações técnicas diretamente da sua base local.
              </p>

              {/* Suggestions Grid */}
              <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                {suggestions.map((sug, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(sug)}
                    className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] text-sm text-zinc-300 hover:text-white transition leading-snug group"
                  >
                    <span className="text-zinc-400 group-hover:text-coral-400 transition-colors">
                      {sug}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.04]">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} onOpenSource={setActiveSource} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Floating Input Dock (Claude / Gemini style) */}
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-[#191919] via-[#191919]/90 to-transparent pointer-events-none">
          <div className="max-w-3xl mx-auto pointer-events-auto">
            <div className="relative bg-[#222222] border border-white/10 rounded-2xl shadow-2xl focus-within:border-white/20 transition-all p-3">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  documents.length === 0
                    ? 'Adicione um documento na barra lateral para começar...'
                    : 'Pergunte qualquer coisa sobre os documentos...'
                }
                rows={1}
                className="w-full bg-transparent text-[15px] text-white placeholder-zinc-500 focus:outline-none resize-none max-h-48 overflow-y-auto px-1 py-1"
                style={{ minHeight: '28px' }}
              />

              <div className="flex items-center justify-between pt-2 mt-1 border-t border-white/[0.04]">
                <div className="flex items-center space-x-2 text-[11px] text-zinc-500 font-mono">
                  <span className="flex items-center gap-1">
                    <BookOpen className="w-3 h-3 text-coral-400" />
                    <span>DocMind Local RAG</span>
                  </span>
                </div>

                <div>
                  {isGenerating ? (
                    <button
                      onClick={handleStopGeneration}
                      className="p-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white transition shadow-sm"
                      title="Parar geração"
                    >
                      <Square className="w-4 h-4 fill-current" />
                    </button>
                  ) : (
                    <button
                      onClick={() => handleSendMessage()}
                      disabled={!input.trim()}
                      className="p-1.5 rounded-xl bg-[#da7756] hover:bg-[#c66545] disabled:opacity-30 disabled:hover:bg-[#da7756] text-white transition shadow-sm"
                      title="Enviar pergunta"
                    >
                      <ArrowUp className="w-4 h-4 stroke-[2.5]" />
                    </button>
                  )}
                </div>
              </div>
            </div>

            <p className="text-center text-[11px] text-zinc-500 mt-2 font-sans">
              DocMind processa documentos de forma 100% privada e local com llama.cpp.
            </p>
          </div>
        </div>
      </main>

      {/* Modal de Detalhes da Fonte Citada */}
      <SourceModal source={activeSource} onClose={() => setActiveSource(null)} />
    </div>
  );
};

export default App;
