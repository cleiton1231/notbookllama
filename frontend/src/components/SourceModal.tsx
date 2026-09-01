import React, { useState } from 'react';
import { SourceReference } from '../types';
import { X, FileText, Check, Copy, Sparkles, BookOpen } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                {source.filename}
                {source.page_number && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                    Pág. {source.page_number}
                  </span>
                )}
              </h3>
              <p className="text-xs text-slate-400 font-mono">Chunk #{source.chunk_index}</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
              title="Copiar trecho"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
              title="Fechar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Badges / Scores */}
        <div className="flex items-center gap-2 px-5 py-2.5 bg-slate-950/40 border-b border-slate-800/60 text-xs">
          {source.rerank_score !== null && source.rerank_score !== undefined ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-medium text-[11px]">
              <Sparkles className="w-3 h-3" />
              Score Rerank: {(source.rerank_score * 100).toFixed(1)}%
            </span>
          ) : null}

          {source.score !== null && source.score !== undefined ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-medium text-[11px]">
              Similaridade: {(source.score * 100).toFixed(1)}%
            </span>
          ) : null}
        </div>

        {/* Content Snippet */}
        <div className="p-5 overflow-y-auto flex-1">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 font-['JetBrains_Mono',monospace] text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
            {source.snippet}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-900/60 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};
