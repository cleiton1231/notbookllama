import React, { useState } from 'react';
import { SourceReference } from '../types';
import { X, Check, Copy, BookOpen } from 'lucide-react';

interface SourceModalProps {
  source: SourceReference | null;
  onClose: () => void;
}

export const SourceModal: React.FC<SourceModalProps> = ({ source, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!source) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(source.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-[#1f1f21] border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] text-zinc-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.08] bg-[#1a1a1c]">
          <div className="flex items-center space-x-3">
            <BookOpen className="w-5 h-5 text-coral-400" />
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                {source.filename}
                {source.page_number && (
                  <span className="text-[11px] px-2 py-0.5 rounded-md bg-white/[0.08] text-zinc-300 font-mono">
                    Página {source.page_number}
                  </span>
                )}
              </h3>
            </div>
          </div>

          <div className="flex items-center space-x-1.5">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition"
              title="Copiar trecho"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition"
              title="Fechar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scores */}
        <div className="flex items-center gap-2 px-6 py-2.5 bg-[#171719] border-b border-white/[0.06] text-xs font-mono">
          {source.rerank_score !== null && source.rerank_score !== undefined && (
            <span className="px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40">
              Reranker: {(source.rerank_score * 100).toFixed(1)}%
            </span>
          )}
          {source.score !== null && source.score !== undefined && (
            <span className="px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300">
              Similaridade: {(source.score * 100).toFixed(1)}%
            </span>
          )}
        </div>

        {/* Snippet Content */}
        <div className="p-6 overflow-y-auto flex-1">
          <div className="p-4 rounded-xl bg-[#141416] border border-white/[0.08] font-mono text-[13px] text-zinc-200 leading-relaxed whitespace-pre-wrap">
            {source.snippet}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/[0.08] bg-[#1a1a1c] flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-white/[0.08] hover:bg-white/[0.12] text-white text-xs font-medium transition"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};
