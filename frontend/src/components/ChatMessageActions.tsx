import React, { useState, useEffect, useRef } from 'react';
import { Copy, Check, RotateCw, Pencil, X, Send } from 'lucide-react';

export interface ChatMessageActionsProps {
  messageIndex: number;
  role: 'user' | 'assistant';
  content: string;
  isLast: boolean;
  isGenerating: boolean;
  onRegenerate?: () => void;
  onEdit?: (newContent: string) => void;
}

export const ChatMessageActions: React.FC<ChatMessageActionsProps> = ({
  role,
  content,
  isGenerating,
  onRegenerate,
  onEdit,
}) => {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(content);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isUser = role === 'user';

  // Sync editContent when content prop changes
  useEffect(() => {
    setEditContent(content);
  }, [content]);

  // Auto-focus and adjust height when entering edit mode
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.selectionStart = textareaRef.current.value.length;
      textareaRef.current.selectionEnd = textareaRef.current.value.length;
    }
  }, [isEditing]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Falha ao copiar texto:', err);
    }
  };

  const handleStartEdit = () => {
    setEditContent(content);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditContent(content);
  };

  const handleSubmitEdit = () => {
    const trimmed = editContent.trim();
    if (!trimmed || isGenerating) return;

    if (onEdit) {
      onEdit(trimmed);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmitEdit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancelEdit();
    }
  };

  // If in inline editing mode for a user message
  if (isEditing && isUser) {
    return (
      <div className="w-full mt-2 space-y-2">
        <textarea
          ref={textareaRef}
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isGenerating}
          rows={3}
          className="w-full bg-zinc-800/90 text-zinc-100 text-sm rounded-lg p-3 border border-white/10 focus:border-[#da7756] focus:outline-none focus:ring-1 focus:ring-[#da7756] resize-y placeholder-zinc-500 font-sans transition"
          placeholder="Edite sua pergunta..."
        />
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span className="text-[11px]">
            Pressione <kbd className="px-1 py-0.5 bg-zinc-800 border border-white/10 rounded text-zinc-300 font-mono">Enter</kbd> para enviar, <kbd className="px-1 py-0.5 bg-zinc-800 border border-white/10 rounded text-zinc-300 font-mono">Shift+Enter</kbd> para nova linha, <kbd className="px-1 py-0.5 bg-zinc-800 border border-white/10 rounded text-zinc-300 font-mono">Esc</kbd> para cancelar
          </span>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleCancelEdit}
              disabled={isGenerating}
              className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-medium text-zinc-400 hover:text-zinc-200 bg-white/5 hover:bg-white/10 rounded-md transition"
              title="Cancelar edição (Esc)"
            >
              <X className="w-3.5 h-3.5" />
              <span>Cancelar</span>
            </button>
            <button
              type="button"
              onClick={handleSubmitEdit}
              disabled={isGenerating || !editContent.trim()}
              className="inline-flex items-center space-x-1 px-3 py-1 text-xs font-medium text-white bg-[#da7756] hover:bg-[#c66848] disabled:opacity-50 disabled:cursor-not-allowed rounded-md shadow-sm transition"
              title="Salvar e reenviar pergunta (Enter)"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Salvar e Enviar</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center space-x-1 text-xs text-zinc-400">
      {/* Copy Button */}
      <button
        type="button"
        onClick={handleCopy}
        className="inline-flex items-center space-x-1 p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition"
        title="Copiar texto"
      >
        {copied ? (
          <>
            <Check className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-[11px] text-emerald-400 font-medium">Copiado</span>
          </>
        ) : (
          <>
            <Copy className="w-3.5 h-3.5" />
          </>
        )}
      </button>

      {/* Edit Button for User Messages */}
      {isUser && onEdit && (
        <button
          type="button"
          onClick={handleStartEdit}
          disabled={isGenerating}
          className="inline-flex items-center space-x-1 p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition"
          title="Editar pergunta"
        >
          <Pencil className="w-3.5 h-3.5" />
          <span className="text-[11px]">Editar</span>
        </button>
      )}

      {/* Regenerate Button for Assistant Messages */}
      {!isUser && onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          disabled={isGenerating}
          className="inline-flex items-center space-x-1 p-1 rounded text-zinc-500 hover:text-zinc-300 hover:bg-white/5 disabled:opacity-40 disabled:cursor-not-allowed transition"
          title="Regenerar resposta"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin text-coral-400' : ''}`} />
          <span className="text-[11px]">Regenerar</span>
        </button>
      )}
    </div>
  );
};
