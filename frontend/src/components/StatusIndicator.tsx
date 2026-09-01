import React from 'react';
import { HealthResponse } from '../types';
import { Activity, RefreshCw, Cpu, Database, Layers, Radio } from 'lucide-react';

interface StatusIndicatorProps {
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ health, loading, onRefresh }) => {
  if (!health) {
    return (
      <header className="flex items-center justify-between px-5 py-2.5 bg-[#090d16]/90 backdrop-blur-md border-b border-slate-800/80 text-xs select-none">
        <div className="flex items-center space-x-2 text-slate-400 font-mono text-[11px]">
          <Activity className="w-3.5 h-3.5 animate-pulse text-amber-400" />
          <span>Sincronizando com serviços locais (llama-server)...</span>
        </div>
        <button
          onClick={onRefresh}
          className="p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800/60 transition"
          title="Verificar conexões"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </header>
    );
  }

  const endpoints = [
    {
      id: 'chat',
      label: 'Chat LLM',
      status: health.chat_endpoint,
      icon: Cpu,
      port: ':8080'
    },
    {
      id: 'embed',
      label: 'Embeddings',
      status: health.embed_endpoint,
      icon: Database,
      port: ':8081'
    },
    {
      id: 'rerank',
      label: 'Reranker',
      status: health.rerank_endpoint,
      icon: Layers,
      port: ':8082'
    },
  ];

  return (
    <header className="flex flex-wrap items-center justify-between px-5 py-2 bg-[#090d16]/95 backdrop-blur-md border-b border-slate-800/80 text-xs gap-3 select-none">
      {/* Endpoints Status Bar */}
      <div className="flex items-center flex-wrap gap-2">
        <div className="flex items-center space-x-1.5 mr-1 text-[11px] text-slate-400 font-medium">
          <Radio className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
          <span className="uppercase tracking-wider font-semibold text-slate-300">Local Engine:</span>
        </div>

        {endpoints.map((ep) => {
          const Icon = ep.icon;
          const isOnline = ep.status.online;

          return (
            <div
              key={ep.id}
              className={`flex items-center space-x-2 px-2.5 py-1 rounded-lg border text-[11px] font-mono transition-all ${
                isOnline
                  ? 'bg-slate-900/80 border-slate-800 text-slate-200 hover:border-slate-700'
                  : 'bg-rose-950/20 border-rose-900/40 text-rose-300'
              }`}
              title={`${ep.status.name} (${ep.status.url}) • ${ep.status.details || ''}`}
            >
              <Icon className={`w-3 h-3 ${isOnline ? 'text-indigo-400' : 'text-rose-400'}`} />
              <span className="font-sans font-medium text-slate-300">{ep.label}</span>
              <span className="text-[10px] text-slate-500 font-mono">{ep.port}</span>

              <span className="flex items-center gap-1 pl-1 border-l border-slate-800">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isOnline
                      ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]'
                      : 'bg-rose-500 shadow-[0_0_6px_rgba(244,63,94,0.8)]'
                  }`}
                />
                <span className={`text-[10px] ${isOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isOnline ? (ep.status.latency_ms ? `${ep.status.latency_ms}ms` : 'Ativo') : 'Off'}
                </span>
              </span>
            </div>
          );
        })}
      </div>

      {/* Database Stats and Sync Button */}
      <div className="flex items-center space-x-3 text-xs">
        <div className="hidden sm:flex items-center space-x-2 px-2.5 py-1 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px] font-mono text-slate-400">
          <span>
            <strong className="text-slate-200 font-semibold">{health.total_indexed_documents}</strong> docs
          </span>
          <span>•</span>
          <span>
            <strong className="text-slate-200 font-semibold">{health.total_indexed_chunks}</strong> chunks
          </span>
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/50 transition text-[11px]"
          title="Atualizar status das conexões locais"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span className="hidden md:inline">Sync</span>
        </button>
      </div>
    </header>
  );
};
