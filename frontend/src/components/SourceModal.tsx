import React, { useState } from 'react';
import { SourceReference } from '../types';
import { X, Check, Copy, Sparkles, BookOpen, Target } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-[#0b101b] border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80 bg-[#090d16]">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                {source.filename}
                {source.page_number && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono font-medium border border-slate-700">
                    Página {source.page_number}
                  </span>
                )}
              </h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Identificador: <span className="text-slate-300">{source.doc_id}_c{source.chunk_index}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-1.5">
            <button
              onClick={handleCopy}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
              title="Copiar trecho recuperado"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
              title="Fechar"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scores & Pipeline Breakdown */}
        <div className="flex flex-wrap items-center gap-2 px-6 py-3 bg-[#080c14] border-b border-slate-800/80 text-xs">
          {source.rerank_score !== null && source.rerank_score !== undefined ? (
            <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-emerald-950/30 border border-emerald-800/50 text-emerald-300 font-mono text-[11px]">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span>Score Reranker: <strong>{(source.rerank_score * 100).toFixed(1)}%</strong></span>
            </div>
          ) : null}

          {source.score !== null && source.score !== undefined ? (
            <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-indigo-950/30 border border-indigo-800/50 text-indigo-300 font-mono text-[11px]">
              <Target className="w-3.5 h-3.5 text-indigo-400" />
              <span>Similaridade Vetorial: <strong>{(source.score * 100).toFixed(1)}%</strong></span>
            </div>
          ) : null}
        </div>

        {/* Content Snippet */}
        <div className="p-6 overflow-y-auto flex-1">
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/80 font-['JetBrains_Mono',monospace] text-xs text-slate-200 leading-relaxed whitespace-pre-wrap selection:bg-indigo-500/30">
            {source.snippet}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800/80 bg-[#090d16] flex items-center justify-between text-xs text-slate-500">
          <span className="font-mono text-[11px]">Fonte entregue ao prompt RAG da LLM</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition text-xs"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};
