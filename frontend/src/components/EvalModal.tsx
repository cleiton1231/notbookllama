import React, { useEffect, useState } from 'react';
import { X, BarChart3 } from 'lucide-react';
import { evaluateRagTurn } from '../services/api';
import type { EvalTurnPayload } from '../services/evalPayload';
import type { RAGEvalResponse } from '../types';

interface EvalModalProps {
  payload: EvalTurnPayload | null;
  onClose: () => void;
}

function ScoreBar({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {
  const display =
    value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`;
  const width =
    value === null || value === undefined ? 0 : Math.max(0, Math.min(100, value * 100));

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="font-mono text-zinc-200">{display}</span>
      </div>
      <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className="h-full rounded-full bg-[#da7756] transition-all"
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

export const EvalModal: React.FC<EvalModalProps> = ({ payload, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RAGEvalResponse | null>(null);

  useEffect(() => {
    if (!payload) {
      setResult(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setResult(null);

    evaluateRagTurn(payload)
      .then((data) => {
        if (!cancelled) setResult(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message || 'Falha ao avaliar');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [payload]);

  if (!payload) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-[#1f1f21] border border-white/10 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[85vh] text-zinc-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.08] bg-[#1a1a1c]">
          <div className="flex items-center space-x-3">
            <BarChart3 className="w-5 h-5 text-coral-400" />
            <h3 className="text-sm font-semibold text-white">Avaliação do turno RAG</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition"
            title="Fechar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          {loading && <p className="text-sm text-zinc-400">Calculando métricas determinísticas…</p>}
          {error && (
            <p className="text-sm text-rose-300 bg-rose-950/20 border border-rose-800/40 rounded-lg p-3">
              {error}
            </p>
          )}
          {result && (
            <div className="space-y-4">
              <ScoreBar label="Overall" value={result.overall_score} />
              <ScoreBar label="Fidelidade lexical" value={result.lexical_faithfulness} />
              <ScoreBar label="Relevância da resposta" value={result.answer_relevance} />
              <ScoreBar label="Chunk recall" value={result.chunk_recall} />
              <ScoreBar label="Chunk precision" value={result.chunk_precision} />
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-white/[0.08] bg-[#1a1a1c] flex justify-end">
          <button
            type="button"
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
