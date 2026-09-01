import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Message, SourceReference } from '../types';
import { Bot, User, Copy, Check, Sparkles, BookOpen, Layers } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
  onOpenSource: (source: SourceReference) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onOpenSource }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`group flex items-start space-x-3.5 py-4 px-4 sm:px-6 transition-colors ${
        isUser ? 'bg-transparent' : 'bg-slate-900/40 border-y border-slate-800/40'
      }`}
    >
      {/* Role Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${
          isUser
            ? 'bg-slate-800 border-slate-700 text-slate-300'
            : 'bg-indigo-600/20 border-indigo-500/30 text-indigo-400 shadow-[0_0_12px_rgba(99,102,241,0.2)]'
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Message Body */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Header */}
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-200 flex items-center gap-2">
            {isUser ? 'Você' : 'DocMind'}
            {!isUser && (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-normal">
                RAG Engine
              </span>
            )}
          </span>

          <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition"
              title="Copiar mensagem"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        {/* Content */}
        {isUser ? (
          <p className="text-sm text-slate-100 whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        ) : (
          <div className="markdown-content text-sm text-slate-200">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {message.isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-indigo-400 animate-pulse align-middle" />
            )}
          </div>
        )}

        {/* Sources & Citations Badges */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="pt-2 mt-2 border-t border-slate-800/60">
            <div className="flex items-center space-x-1.5 text-[11px] font-medium text-slate-400 mb-2">
              <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
              <span>Fontes consultadas ({message.sources.length}):</span>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {message.sources.map((src, idx) => (
                <button
                  key={idx}
                  onClick={() => onOpenSource(src)}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-indigo-900/30 border border-slate-700/60 hover:border-indigo-500/40 text-xs text-slate-300 hover:text-indigo-200 transition group/badge"
                  title={`Ver trecho: ${src.filename} (score: ${src.rerank_score || src.score})`}
                >
                  <span className="font-semibold text-indigo-400 text-[11px]">#{idx + 1}</span>
                  <span className="max-w-[140px] truncate">{src.filename}</span>
                  {src.page_number && (
                    <span className="text-[10px] text-slate-400 font-mono">p.{src.page_number}</span>
                  )}
                  {src.rerank_score !== null && src.rerank_score !== undefined && (
                    <span className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-1 rounded">
                      {(src.rerank_score * 100).toFixed(0)}%
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
