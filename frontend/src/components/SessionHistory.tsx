import React, { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  Plus,
  Trash2,
  Search,
  Loader2,
  Clock,
  AlertCircle
} from 'lucide-react';

export interface SessionItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface SessionHistoryProps {
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  refreshTrigger?: number;
}

export const SessionHistory: React.FC<SessionHistoryProps> = ({
  currentSessionId,
  onSelectSession,
  onNewChat,
  refreshTrigger = 0,
}) => {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/sessions');
      if (!res.ok) {
        throw new Error(`Erro ao buscar histórico (${res.status})`);
      }
      const data: SessionItem[] = await res.json();
      setSessions(data);
    } catch (err: any) {
      console.error('Falha ao carregar sessões:', err);
      setError(err.message || 'Falha ao carregar conversas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions, refreshTrigger]);

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Tem certeza que deseja excluir esta conversa?')) {
      return;
    }

    try {
      setDeletingId(sessionId);
      const res = await fetch(`/api/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        throw new Error('Falha ao excluir sessão');
      }

      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        onNewChat();
      }
    } catch (err: any) {
      console.error('Erro ao deletar sessão:', err);
      alert(err.message || 'Erro ao deletar sessão');
    } finally {
      setDeletingId(null);
    }
  };

  const formatTimestamp = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return '';

      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffMinutes < 1) return 'Agora mesmo';
      if (diffMinutes < 60) return `${diffMinutes} min atrás`;
      if (diffHours < 24) {
        return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      }
      if (diffDays === 1) return 'Ontem';
      if (diffDays < 7) return `${diffDays} dias atrás`;

      return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
    } catch {
      return '';
    }
  };

  const filteredSessions = sessions.filter((session) =>
    session.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full text-zinc-300">
      {/* Header / Nova Conversa Button */}
      <div className="p-3 space-y-2 border-b border-white/[0.06]">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-lg bg-[#da7756]/15 hover:bg-[#da7756]/25 text-[#da7756] hover:text-[#e0896c] border border-[#da7756]/30 font-medium text-xs transition duration-150 shadow-sm"
          title="Iniciar nova conversa"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Nova Conversa</span>
        </button>

        {/* Filter input */}
        {sessions.length > 2 && (
          <div className="relative">
            <Search className="w-3 h-3 absolute left-2.5 top-2 text-zinc-500" />
            <input
              type="text"
              placeholder="Filtrar conversas..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-[#1c1c1e] border border-white/[0.08] rounded-md pl-7 pr-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-[#da7756]/60 transition"
            />
          </div>
        )}
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
        {loading && sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-zinc-500 text-xs space-y-2">
            <Loader2 className="w-4 h-4 animate-spin text-[#da7756]" />
            <span>Carregando histórico...</span>
          </div>
        ) : error ? (
          <div className="p-3 rounded-lg bg-red-950/20 border border-red-900/30 text-xs text-red-400 space-y-2">
            <div className="flex items-center space-x-1.5">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span className="font-medium">Erro ao carregar</span>
            </div>
            <p className="text-[11px] text-red-300/80">{error}</p>
            <button
              onClick={fetchSessions}
              className="text-[11px] underline hover:text-red-300"
            >
              Tentar novamente
            </button>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center px-4">
            <MessageSquare className="w-6 h-6 text-zinc-600 mb-2 stroke-[1.5]" />
            <p className="text-xs font-medium text-zinc-400">
              {searchTerm ? 'Nenhuma conversa encontrada' : 'Nenhuma conversa salva'}
            </p>
            <p className="text-[10px] text-zinc-500 mt-0.5">
              {searchTerm
                ? 'Tente outro termo de busca'
                : 'Suas conversas anteriores aparecerão aqui'}
            </p>
          </div>
        ) : (
          filteredSessions.map((session) => {
            const isSelected = currentSessionId === session.id;
            const isDeleting = deletingId === session.id;

            return (
              <div
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                className={`group relative flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition duration-150 border ${
                  isSelected
                    ? 'bg-white/[0.08] text-white border-white/[0.15] shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] border-transparent'
                }`}
                title={session.title}
              >
                <div className="flex items-center space-x-2.5 min-w-0 pr-2 flex-1">
                  <MessageSquare
                    className={`w-3.5 h-3.5 shrink-0 ${
                      isSelected ? 'text-[#da7756]' : 'text-zinc-500 group-hover:text-zinc-400'
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium truncate text-xs leading-snug">
                      {session.title || 'Conversa sem título'}
                    </p>
                    <div className="flex items-center space-x-1 text-[10px] text-zinc-500 mt-0.5 font-mono">
                      <Clock className="w-2.5 h-2.5" />
                      <span>{formatTimestamp(session.updated_at || session.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <button
                  onClick={(e) => handleDeleteSession(session.id, e)}
                  disabled={isDeleting}
                  className={`p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400 text-zinc-500 transition shrink-0 ${
                    isDeleting ? 'opacity-100' : ''
                  }`}
                  title="Excluir conversa"
                >
                  {isDeleting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-red-400" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default SessionHistory;
