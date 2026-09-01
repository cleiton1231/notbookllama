import React from 'react';
import { HealthResponse } from '../types';
import { Activity, RefreshCw, Cpu, Database, Layers } from 'lucide-react';

interface StatusIndicatorProps {
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ health, loading, onRefresh }) => {
  if (!health) {
    return (
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/60 border-b border-slate-800 text-xs">
        <div className="flex items-center space-x-2 text-slate-400">
          <Activity className="w-3.5 h-3.5 animate-pulse text-amber-400" />
          <span>Verificando endpoints locais...</span>
        </div>
        <button
          onClick={onRefresh}
          className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
          title="Recarregar status"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    );
  }

  const endpoints = [
    { label: 'LLM Chat', status: health.chat_endpoint, icon: Cpu },
    { label: 'Embeddings', status: health.embed_endpoint, icon: Database },
    { label: 'Reranker', status: health.rerank_endpoint, icon: Layers },
  ];

  return (
    <div className="flex flex-wrap items-center justify-between px-4 py-2 bg-slate-900/80 border-b border-slate-800/80 text-xs gap-2">
      <div className="flex items-center gap-3">
        {endpoints.map((ep, idx) => {
          const Icon = ep.icon;
          return (
            <div
              key={idx}
              className="flex items-center space-x-1.5 px-2 py-1 rounded-md bg-slate-800/40 border border-slate-700/40"
              title={`${ep.status.name} em ${ep.status.url} (${ep.status.details || ''})`}
            >
              <Icon className="w-3 h-3 text-slate-400" />
              <span className="text-slate-300 font-medium">{ep.label}:</span>
              <span className="flex items-center gap-1">
                <span
                  className={`w-2 h-2 rounded-full ${
                    ep.status.online ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]'
                  }`}
                />
                <span className={ep.status.online ? 'text-emerald-400' : 'text-rose-400'}>
                  {ep.status.online ? 'Online' : 'Offline'}
                </span>
              </span>
            </div>
          );
        })}
      </div>

      <div className="flex items-center space-x-3 text-slate-400">
        <span className="hidden sm:inline">
          <strong className="text-slate-200">{health.total_indexed_documents}</strong> docs (
          <strong className="text-slate-200">{health.total_indexed_chunks}</strong> chunks)
        </span>
        <button
          onClick={onRefresh}
          className="p-1 hover:text-white rounded hover:bg-slate-800 transition"
          title="Verificar status dos servidores"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </div>
  );
};
