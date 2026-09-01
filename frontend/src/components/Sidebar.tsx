import React, { useState } from 'react';
import { DocumentMetadata } from '../types';
import { FileUpload } from './FileUpload';
import {
  FileText,
  Trash2,
  CheckSquare,
  Square,
  Search,
  Plus,
  SlidersHorizontal,
  FolderOpen,
  Sparkles
} from 'lucide-react';

interface SidebarProps {
  documents: DocumentMetadata[];
  selectedDocIds: string[];
  onToggleDoc: (docId: string) => void;
  onSelectAllDocs: () => void;
  onClearDocSelection: () => void;
  onDeleteDoc: (docId: string) => void;
  onUploadSuccess: (doc: DocumentMetadata) => void;
  onNewChat: () => void;
  useRerank: boolean;
  onToggleRerank: (enabled: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  documents,
  selectedDocIds,
  onToggleDoc,
  onSelectAllDocs,
  onClearDocSelection,
  onDeleteDoc,
  onUploadSuccess,
  onNewChat,
  useRerank,
  onToggleRerank,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const filteredDocs = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Deseja remover este documento da base?')) {
      setDeletingId(docId);
      try {
        await onDeleteDoc(docId);
      } finally {
        setDeletingId(null);
      }
    }
  };

  const isAllSelected = documents.length > 0 && selectedDocIds.length === documents.length;

  return (
    <aside className="w-72 h-full bg-[#141414] border-r border-white/[0.08] flex flex-col shrink-0 select-none text-zinc-300">
      {/* App Header & New Chat */}
      <div className="p-4 border-b border-white/[0.06] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#da7756] text-white flex items-center justify-center font-bold text-sm shadow-sm">
              D
            </div>
            <span className="font-semibold text-white tracking-tight text-base">DocMind</span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.06] text-zinc-400">
            Local RAG
          </span>
        </div>

        {/* New Chat Button */}
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-white font-medium text-xs transition border border-white/[0.08]"
        >
          <Plus className="w-4 h-4 text-coral-400" />
          <span>Nova Conversa</span>
        </button>
      </div>

      {/* Upload Drop Area */}
      <div className="p-3 border-b border-white/[0.06]">
        <FileUpload onUploadSuccess={onUploadSuccess} />
      </div>

      {/* Reranker Config */}
      <div className="px-4 py-3 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <SlidersHorizontal className="w-3.5 h-3.5 text-coral-400" />
          <div>
            <p className="text-xs font-medium text-zinc-200">Reranker 2-Estágios</p>
            <p className="text-[10px] text-zinc-500 font-mono">
              {useRerank ? 'Cross-Encoder (:8082)' : 'Cosseno direto'}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onToggleRerank(!useRerank)}
          className={`relative inline-flex h-4 w-8 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
            useRerank ? 'bg-coral-500' : 'bg-zinc-700'
          }`}
          title={useRerank ? 'Desativar Reranker' : 'Ativar Reranker'}
        >
          <span
            className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
              useRerank ? 'translate-x-4' : 'translate-x-0'
            }`}
          />
        </button>
      </div>

      {/* Search & Document Actions */}
      <div className="p-3 space-y-2 border-b border-white/[0.06]">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-zinc-500" />
          <input
            type="text"
            placeholder="Buscar documentos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#1c1c1e] border border-white/[0.08] rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-coral-500/60 transition"
          />
        </div>

        {documents.length > 0 && (
          <div className="flex items-center justify-between text-[11px] text-zinc-400 px-1 pt-0.5">
            <button
              onClick={isAllSelected ? onClearDocSelection : onSelectAllDocs}
              className="flex items-center space-x-1.5 hover:text-white transition"
            >
              {isAllSelected ? (
                <CheckSquare className="w-3.5 h-3.5 text-coral-400" />
              ) : (
                <Square className="w-3.5 h-3.5 text-zinc-500" />
              )}
              <span>{isAllSelected ? 'Todos marcados' : 'Marcar todos'}</span>
            </button>
            <span className="font-mono text-zinc-500 text-[10px]">{documents.length} arquivos</span>
          </div>
        )}
      </div>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filteredDocs.length === 0 ? (
          <div className="text-center py-10 px-4 text-zinc-500 text-xs">
            <FolderOpen className="w-8 h-8 text-zinc-600 mx-auto mb-2 stroke-[1.5]" />
            <p className="font-medium text-zinc-400">
              {searchTerm ? 'Nenhum documento encontrado.' : 'Nenhum documento.'}
            </p>
            <p className="text-[11px] text-zinc-500 mt-1">
              Envie PDFs ou textos para pesquisar.
            </p>
          </div>
        ) : (
          filteredDocs.map((doc) => {
            const isSelected = selectedDocIds.includes(doc.doc_id);
            const isDeleting = deletingId === doc.doc_id;

            return (
              <div
                key={doc.doc_id}
                onClick={() => onToggleDoc(doc.doc_id)}
                className={`group relative flex items-start space-x-2.5 p-2.5 rounded-xl text-xs cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-white/[0.08] text-white'
                    : 'hover:bg-white/[0.04] text-zinc-400 hover:text-zinc-200'
                } ${isDeleting ? 'opacity-30 pointer-events-none' : ''}`}
              >
                <div className="pt-0.5 shrink-0">
                  {isSelected ? (
                    <CheckSquare className="w-3.5 h-3.5 text-coral-400" />
                  ) : (
                    <Square className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400" />
                  )}
                </div>

                <FileText className="w-4 h-4 text-zinc-400 shrink-0 mt-0.5" />

                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate text-zinc-200 text-xs" title={doc.filename}>
                    {doc.filename}
                  </p>
                  <div className="flex items-center space-x-2 text-[10px] text-zinc-500 mt-0.5 font-mono">
                    <span className="text-coral-400/90">{doc.total_chunks} chunks</span>
                    <span>•</span>
                    <span>{formatFileSize(doc.file_size)}</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={(e) => handleDelete(doc.doc_id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-zinc-500 hover:text-rose-400 hover:bg-white/10 rounded-md transition shrink-0"
                  title="Excluir documento"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-white/[0.06] text-[11px] text-zinc-500 flex items-center justify-between font-mono">
        <span className="flex items-center gap-1.5">
          <Sparkles className="w-3 h-3 text-coral-400" />
          <span>ChromaDB Vector Store</span>
        </span>
      </div>
    </aside>
  );
};
