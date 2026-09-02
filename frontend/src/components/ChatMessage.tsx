import React, { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import { Message, SourceReference } from '../types';
import { BookOpen } from 'lucide-react';
import { ChatMessageActions } from './ChatMessageActions';

interface ChatMessageProps {
  message: Message;
  messageIndex: number;
  isLast: boolean;
  isGenerating: boolean;
  onOpenSource: (source: SourceReference) => void;
  onRegenerate?: (messageIndex: number) => void;
  onEdit?: (messageIndex: number, newContent: string) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = memo(({
  message,
  messageIndex,
  isLast,
  isGenerating,
  onOpenSource,
  onRegenerate,
  onEdit,
}) => {
  const isUser = message.role === 'user';

  return (
    <div className={`w-full py-6 px-4 md:px-0 flex justify-center ${isUser ? '' : 'bg-transparent'}`}>
      <div className="w-full max-w-3xl flex items-start space-x-4">
        {/* Avatar */}
        <div
          className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-semibold select-none mt-1 ${
            isUser
              ? 'bg-zinc-700 text-zinc-200'
              : 'bg-[#da7756] text-white shadow-sm'
          }`}
        >
          {isUser ? 'V' : 'D'}
        </div>

        {/* Message Content Area */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Header */}
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-semibold text-zinc-200 text-sm">
              {isUser ? 'Você' : 'DocMind'}
            </span>
            <ChatMessageActions
              messageIndex={messageIndex}
              role={isUser ? 'user' : 'assistant'}
              content={message.content}
              isLast={isLast}
              isGenerating={isGenerating}
              onRegenerate={onRegenerate ? () => onRegenerate(messageIndex) : undefined}
              onEdit={onEdit ? (newContent) => onEdit(messageIndex, newContent) : undefined}
            />
          </div>

          {/* Text / Markdown */}
          {isUser ? (
            <div className="text-[15px] text-zinc-100 whitespace-pre-wrap leading-relaxed">
              {message.content}
            </div>
          ) : (
            <div className="markdown-content">
              <ReactMarkdown>{message.content}</ReactMarkdown>
              {message.isStreaming && (
                <span className="inline-block w-1.5 h-4 ml-1 bg-coral-400 animate-pulse align-middle rounded-sm" />
              )}
            </div>
          )}

          {/* Sources Section */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="pt-4 mt-4 border-t border-white/[0.08]">
              <div className="flex items-center space-x-1.5 text-xs font-medium text-zinc-400 mb-2">
                <BookOpen className="w-3.5 h-3.5 text-coral-400" />
                <span>Fontes consultadas ({message.sources.length}):</span>
              </div>

              <div className="flex flex-wrap gap-2">
                {message.sources.map((src, idx) => {
                  const displayScore = src.rerank_score ?? src.score;

                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => onOpenSource(src)}
                      className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/[0.15] text-zinc-300 transition"
                      title={`Ver trecho: ${src.filename}`}
                    >
                      <span className="font-mono text-coral-400 text-[10px] font-bold">#{idx + 1}</span>
                      <span className="max-w-[140px] truncate font-medium">{src.filename}</span>
                      {src.page_number && (
                        <span className="text-[10px] text-zinc-400 font-mono">
                          p.{src.page_number}
                        </span>
                      )}
                      {displayScore !== null && displayScore !== undefined && (
                        <span className="text-[10px] font-mono text-emerald-400 font-medium">
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
    </div>
  );
});
