import React, { useState, useRef } from 'react';
import { UploadCloud, Loader2, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import { uploadDocument } from '../services/api';
import { DocumentMetadata } from '../types';

interface FileUploadProps {
  onUploadSuccess: (doc: DocumentMetadata) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState<string>('');
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFile(e.target.files[0]);
    }
  };

  const processFile = async (file: File) => {
    setStatusMessage(null);
    setIsUploading(true);
    setUploadStage('Fatiando e gerando embeddings locais...');

    try {
      const response = await uploadDocument(file);
      setStatusMessage({ type: 'success', text: response.message });
      onUploadSuccess(response.document);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Falha ao indexar o documento' });
    } finally {
      setIsUploading(false);
      setUploadStage('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="w-full">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`group relative rounded-xl p-4 text-center cursor-pointer transition-all duration-200 border ${
          isDragging
            ? 'border-indigo-500 bg-indigo-500/10 shadow-[0_0_20px_rgba(99,102,241,0.15)] scale-[0.99]'
            : 'border-slate-800 hover:border-slate-700 bg-slate-900/40 hover:bg-slate-900/80 shadow-sm'
        } ${isUploading ? 'opacity-70 pointer-events-none cursor-wait' : ''}`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept=".pdf,.md,.markdown,.txt,.csv,.json"
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center space-y-2.5">
          {isUploading ? (
            <div className="flex flex-col items-center space-y-2 py-1.5">
              <div className="relative">
                <Loader2 className="w-7 h-7 text-indigo-400 animate-spin" />
                <Sparkles className="w-3 h-3 text-indigo-300 absolute -top-1 -right-1 animate-ping" />
              </div>
              <div className="text-center">
                <p className="text-xs font-medium text-slate-200">{uploadStage}</p>
                <p className="text-[10px] text-slate-400 font-mono mt-0.5">Processamento 100% local</p>
              </div>
            </div>
          ) : (
            <>
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-105 group-hover:bg-indigo-500/15 group-hover:border-indigo-500/30 transition-all">
                <UploadCloud className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-200 group-hover:text-indigo-200 transition-colors">
                  Arraste ou clique para indexar
                </p>
                <div className="flex items-center justify-center gap-1.5 mt-1">
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">PDF</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">MD</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">TXT</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {statusMessage && (
        <div
          className={`mt-2 flex items-start space-x-2 p-2.5 rounded-lg text-xs animate-in fade-in duration-150 border ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300'
              : 'bg-rose-950/30 border-rose-800/40 text-rose-300'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          )}
          <span className="leading-snug text-[11px]">{statusMessage.text}</span>
        </div>
      )}
    </div>
  );
};
