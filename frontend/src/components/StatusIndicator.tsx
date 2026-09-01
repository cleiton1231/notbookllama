import React from 'react';
import { HealthResponse } from '../types';
import { RefreshCw } from 'lucide-react';

interface StatusIndicatorProps {
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ health, loading, onRefresh }) => {
  if (!health) {
    return (
      <div className="flex items-center space-x-2 text-xs text-zinc-500 font-mono">
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        <span>Conectando...</span>
      </div>
    );
  }

  const allOnline = health.chat_endpoint.online && health.embed_endpoint.online;
  const isRerankOnline = health.rerank_endpoint.online;

  return (
    <div className="flex items-center space-x-3 text-xs">
      <div
        className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-zinc-300 font-mono cursor-pointer hover:bg-white/[0.08] transition"
        onClick={onRefresh}
        title={`Chat: ${health.chat_endpoint.online ? 'Online' : 'Offline'} | Embed: ${health.embed_endpoint.online ? 'Online' : 'Offline'} | Rerank: ${isRerankOnline ? 'Online' : 'Offline'}`}
      >
        <span
          className={`w-2 h-2 rounded-full ${
            allOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-amber-400'
          }`}
        />
        <span className="text-[11px] font-sans font-medium text-zinc-300">
          {allOnline ? 'Local Engine' : 'Degradado'}
        </span>
        {health.chat_endpoint.latency_ms !== null && health.chat_endpoint.latency_ms !== undefined && (
          <span className="text-[10px] text-zinc-500 pl-1 border-l border-white/10">
            {health.chat_endpoint.latency_ms}ms
          </span>
        )}
        <RefreshCw className={`w-3 h-3 text-zinc-500 hover:text-zinc-300 ml-1 ${loading ? 'animate-spin' : ''}`} />
      </div>

      <div className="hidden sm:flex items-center space-x-1.5 text-zinc-500 text-xs font-mono">
        <span>{health.total_indexed_documents} doc(s)</span>
        <span>•</span>
        <span>{health.total_indexed_chunks} chunks</span>
      </div>
    </div>
  );
};
