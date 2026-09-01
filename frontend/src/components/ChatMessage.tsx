import React, { useState, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Message, SourceReference } from '../types';
import { Bot, User, Copy, Check, BookOpen } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
  onOpenSource: (source: SourceReference) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = memo(({ message, onOpenSource }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getScoreBadgeClass = (score: number | null | undefined) => {
    if (score === null || score === undefined) return 'bg-slate-800 text-slate-400 border-slate-700';
    if (score >= 0.85) return 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60';
    if (score >= 0.60) return 'bg-indigo-950/40 text-indigo-300 border-indigo-800/60';
    return 'bg-slate-800/80 text-slate-300 border-slate-700';
  };

  return (
    <div
      className={`group flex items-start space-x-4 py-5 px-4 sm:px-8 transition-colors ${
        isUser
          ? 'bg-transparent'
          : 'bg-slate-900/35 border-y border-slate-800/40'
      }`}
    >
      {/* Role Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${
          isUser
            ? 'bg-slate-800/80 border-slate-700 text-slate-200'
            : 'bg-gradient-to-br from-indigo-900/50 to-indigo-700/30 border-indigo-500/40 text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.15)]'
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Message Body */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Header Bar */}
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-200">
              {isUser ? 'Você' : 'DocMind'}
            </span>
            {!isUser && (
              <span className="text-[10px] px-2 py-0.2 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono font-medium">
                RAG Engine Local
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition"
              title="Copiar mensagem"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Message Content */}
        {isUser ? (
          <p className="text-sm text-slate-100 whitespace-pre-wrap leading-relaxed font-normal">
            {message.content}
          </p>
        ) : (
          <div className="markdown-content text-sm text-slate-200 leading-relaxed">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {message.isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-indigo-400 animate-pulse align-middle rounded-sm shadow-[0_0_8px_rgba(99,102,241,0.8)]" />
            )}
          </div>
        )}

        {/* Sources & Citations Badges */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="pt-3 mt-3 border-t border-slate-800/60">
            <div className="flex items-center space-x-1.5 text-[11px] font-medium text-slate-400 mb-2.5">
              <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
              <span className="font-sans">Fontes consultadas ({message.sources.length}):</span>
            </div>

            <div className="flex flex-wrap gap-2">
              {message.sources.map((src, idx) => {
                const displayScore = src.rerank_score !== null && src.rerank_score !== undefined ? src.rerank_score : src.score;
                const badgeStyle = getScoreBadgeClass(displayScore);

                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => onOpenSource(src)}
                    className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs transition border hover:scale-[1.02] active:scale-[0.98] ${badgeStyle}`}
                    title={`Ver trecho: ${src.filename} (Score: ${(displayScore ? displayScore * 100 : 0).toFixed(0)}%)`}
                  >
                    <span className="font-mono font-bold text-indigo-400 text-[10px]">#{idx + 1}</span>
                    <span className="max-w-[130px] truncate font-medium">{src.filename}</span>
                    {src.page_number && (
                      <span className="text-[10px] text-slate-400 font-mono bg-slate-900/60 px-1 rounded">
                        p.{src.page_number}
                      </span>
                    )}
                    {displayScore !== null && displayScore !== undefined && (
                      <span className="text-[10px] font-mono font-semibold">
                        {(displayScore * 100).toFixed(0)}%
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});
