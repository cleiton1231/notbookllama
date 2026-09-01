import React, { useState } from 'react';
import { DocumentMetadata } from '../types';
import { FileUpload } from './FileUpload';
import {
  Brain,
  FileText,
  Trash2,
  CheckSquare,
  Square,
  Search,
  Database,
  Layers,
  FileCode,
  ShieldCheck,
  HardDrive
} from 'lucide-react';

interface SidebarProps {
  documents: DocumentMetadata[];
  selectedDocIds: string[];
  onToggleDoc: (docId: string) => void;
  onSelectAllDocs: () => void;
  onClearDocSelection: () => void;
  onDeleteDoc: (docId: string) => void;
  onUploadSuccess: (doc: DocumentMetadata) => void;
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

  const getDocIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-rose-400 shrink-0" />;
      case 'markdown':
        return <FileCode className="w-4 h-4 text-sky-400 shrink-0" />;
      default:
        return <FileText className="w-4 h-4 text-indigo-400 shrink-0" />;
    }
  };

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Deseja realmente remover este documento e seus vetores indexados da base local?')) {
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
    <aside className="w-80 h-full bg-[#080c14] border-r border-slate-800/80 flex flex-col shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80 flex items-center justify-between bg-[#080c14]">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white flex items-center justify-center shadow-[0_0_15px_rgba(99,102,241,0.3)]">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <h1 className="font-bold text-slate-100 text-sm tracking-tight">DocMind</h1>
              <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span>100% Local RAG</span>
            </p>
          </div>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="p-3 border-b border-slate-800/60 bg-slate-950/30">
        <FileUpload onUploadSuccess={onUploadSuccess} />
      </div>

      {/* RAG 2-Stage Rerank Control */}
      <div className="px-4 py-3 border-b border-slate-800/60 bg-slate-900/30 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className={`p-1.5 rounded-lg border ${useRerank ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400' : 'bg-slate-800 border-slate-700 text-slate-400'}`}>
            <Layers className="w-3.5 h-3.5" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-200">Reranker (2 Estágios)</p>
            <p className="text-[10px] text-slate-400 font-mono">
              {useRerank ? 'Cross-Encoder Ativo (:8082)' : 'Busca Vetorial Pura'}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onToggleRerank(!useRerank)}
          className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
            useRerank ? 'bg-indigo-600 shadow-[0_0_10px_rgba(99,102,241,0.5)]' : 'bg-slate-700'
          }`}
          title={useRerank ? 'Desativar Reranker' : 'Ativar Reranker de 2 Estágios'}
        >
          <span
            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
              useRerank ? 'translate-x-4' : 'translate-x-0'
            }`}
          />
        </button>
      </div>

      {/* Search and Selection Tools */}
      <div className="p-3 border-b border-slate-800/60 space-y-2 bg-[#090d16]/50">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
          <input
            type="text"
            placeholder="Filtrar base de documentos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950/70 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 focus:ring-1 focus:ring-indigo-500/30 transition"
          />
        </div>

        {documents.length > 0 && (
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <button
              onClick={isAllSelected ? onClearDocSelection : onSelectAllDocs}
              className="flex items-center space-x-1.5 hover:text-indigo-300 transition"
            >
              {isAllSelected ? (
                <CheckSquare className="w-3.5 h-3.5 text-indigo-400" />
              ) : (
                <Square className="w-3.5 h-3.5 text-slate-500" />
              )}
              <span>{isAllSelected ? 'Todos marcados' : 'Marcar todos'}</span>
            </button>
            <span className="font-mono text-slate-500">{documents.length} doc(s)</span>
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filteredDocs.length === 0 ? (
          <div className="text-center py-10 px-4 text-slate-500 text-xs">
            <HardDrive className="w-8 h-8 text-slate-700 mx-auto mb-2 stroke-[1.5]" />
            <p className="font-medium text-slate-400">
              {searchTerm ? 'Nenhum resultado para o filtro.' : 'Nenhum documento indexado.'}
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              Envie PDFs ou textos para começar a pesquisar.
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
                className={`group relative flex items-start space-x-2.5 p-2.5 rounded-xl text-xs cursor-pointer transition-all border ${
                  isSelected
                    ? 'bg-indigo-600/10 border-indigo-500/40 text-slate-100 shadow-sm'
                    : 'bg-slate-900/30 hover:bg-slate-900/80 border-slate-800/40 hover:border-slate-700/60 text-slate-300'
                } ${isDeleting ? 'opacity-40 pointer-events-none' : ''}`}
              >
                <div className="pt-0.5 shrink-0">
                  {isSelected ? (
                    <CheckSquare className="w-3.5 h-3.5 text-indigo-400" />
                  ) : (
                    <Square className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400" />
                  )}
                </div>

                <div className="shrink-0 pt-0.5">{getDocIcon(doc.file_type)}</div>

                <div className="flex-1 min-w-0">
                  <p className="font-semibold truncate text-slate-200 text-xs" title={doc.filename}>
                    {doc.filename}
                  </p>
                  <div className="flex items-center space-x-2 text-[10px] text-slate-400 mt-0.5 font-mono">
                    <span className="text-indigo-400 font-medium">{doc.total_chunks} chunks</span>
                    <span>•</span>
                    <span>{formatFileSize(doc.file_size)}</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={(e) => handleDelete(doc.doc_id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg transition shrink-0"
                  title="Excluir documento do ChromaDB"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60 text-[11px] text-slate-400 flex items-center justify-between font-mono">
        <span className="flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-indigo-400" />
          <span>ChromaDB VectorStore</span>
        </span>
        <span className="text-slate-500 text-[10px]">Lock thread-safe</span>
      </div>
    </aside>
  );
};
