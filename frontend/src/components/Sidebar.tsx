import React, { useState } from 'react';
import { DocumentMetadata } from '../types';
import { FileUpload } from './FileUpload';
import {
  BrainCircuit,
  FileText,
  Trash2,
  CheckSquare,
  Square,
  Search,
  ChevronRight,
  Database,
  Layers,
  FileCode,
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
        return <FileText className="w-4 h-4 text-rose-400" />;
      case 'markdown':
        return <FileCode className="w-4 h-4 text-sky-400" />;
      default:
        return <FileText className="w-4 h-4 text-indigo-400" />;
    }
  };

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Deseja realmente remover este documento e seus vetores indexados?')) {
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
    <aside className="w-80 h-full bg-slate-900/90 border-r border-slate-800/80 flex flex-col shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center space-x-3 bg-slate-900">
        <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 text-white shadow-lg shadow-indigo-500/20">
          <BrainCircuit className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-slate-100 text-sm tracking-tight flex items-center gap-1.5">
            DocMind
            <span className="text-[10px] uppercase font-semibold px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              RAG Local
            </span>
          </h1>
          <p className="text-[11px] text-slate-400">Segundo Cérebro com llama.cpp</p>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="p-3 border-b border-slate-800/60 bg-slate-950/20">
        <FileUpload onUploadSuccess={onUploadSuccess} />
      </div>

      {/* RAG Settings Control */}
      <div className="px-4 py-2.5 border-b border-slate-800/60 bg-slate-900/40 flex items-center justify-between text-xs">
        <span className="flex items-center space-x-1.5 text-slate-300 font-medium">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Reranker (2 Estágios)</span>
        </span>
        <button
          onClick={() => onToggleRerank(!useRerank)}
          className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
            useRerank ? 'bg-indigo-600' : 'bg-slate-700'
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
              useRerank ? 'translate-x-4' : 'translate-x-0'
            }`}
          />
        </button>
      </div>

      {/* Search and Selection Tools */}
      <div className="p-3 border-b border-slate-800/60 space-y-2">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Filtrar documentos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950/60 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
          />
        </div>

        {documents.length > 0 && (
          <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
            <button
              onClick={isAllSelected ? onClearDocSelection : onSelectAllDocs}
              className="flex items-center space-x-1 hover:text-indigo-300 transition"
            >
              {isAllSelected ? (
                <CheckSquare className="w-3.5 h-3.5 text-indigo-400" />
              ) : (
                <Square className="w-3.5 h-3.5" />
              )}
              <span>{isAllSelected ? 'Todos marcados' : 'Marcar todos'}</span>
            </button>
            <span>{documents.length} doc(s)</span>
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {filteredDocs.length === 0 ? (
          <div className="text-center py-8 px-4 text-slate-500 text-xs">
            {searchTerm ? 'Nenhum documento encontrado.' : 'Nenhum documento na base. Faça o upload acima!'}
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
                    ? 'bg-indigo-600/10 border border-indigo-500/30 text-slate-100 shadow-sm'
                    : 'bg-slate-800/30 hover:bg-slate-800/60 border border-transparent text-slate-300'
                } ${isDeleting ? 'opacity-40 pointer-events-none' : ''}`}
              >
                <div className="pt-0.5 shrink-0">
                  {isSelected ? (
                    <CheckSquare className="w-3.5 h-3.5 text-indigo-400" />
                  ) : (
                    <Square className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400" />
                  )}
                </div>

                <div className="shrink-0 pt-0.5">{getDocIcon(doc.file_type)}</div>

                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate text-slate-200" title={doc.filename}>
                    {doc.filename}
                  </p>
                  <div className="flex items-center space-x-2 text-[10px] text-slate-400 mt-0.5 font-mono">
                    <span>{doc.total_chunks} chunks</span>
                    <span>•</span>
                    <span>{formatFileSize(doc.file_size)}</span>
                  </div>
                </div>

                <button
                  onClick={(e) => handleDelete(doc.doc_id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 hover:bg-slate-700/50 rounded transition shrink-0"
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
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40 text-[11px] text-slate-400 flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <Database className="w-3.5 h-3.5 text-indigo-400" />
          <span>ChromaDB Persistente</span>
        </span>
        <span className="font-mono text-slate-500 text-[10px]">v1.0</span>
      </div>
    </aside>
  );
};
