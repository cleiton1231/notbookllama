import React, { useState, useRef } from 'react';
import { UploadCloud, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { uploadDocument } from '../services/api';
import { DocumentMetadata } from '../types';

interface FileUploadProps {
  onUploadSuccess: (doc: DocumentMetadata) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
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

    try {
      const response = await uploadDocument(file);
      setStatusMessage({ type: 'success', text: response.message });
      onUploadSuccess(response.document);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Falha ao indexar arquivo' });
    } finally {
      setIsUploading(false);
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
        className={`rounded-xl p-3 text-center cursor-pointer transition-all border ${
          isDragging
            ? 'border-coral-500 bg-coral-500/10'
            : 'border-white/[0.08] hover:border-white/[0.15] bg-white/[0.02] hover:bg-white/[0.04]'
        } ${isUploading ? 'opacity-60 pointer-events-none' : ''}`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept=".pdf,.md,.markdown,.txt,.csv,.json"
          className="hidden"
        />

        <div className="flex items-center justify-center space-x-2.5">
          {isUploading ? (
            <div className="flex items-center space-x-2 py-1">
              <Loader2 className="w-4 h-4 text-coral-400 animate-spin" />
              <span className="text-xs text-zinc-300 font-medium">Indexando no ChromaDB...</span>
            </div>
          ) : (
            <>
              <UploadCloud className="w-4 h-4 text-coral-400 shrink-0" />
              <div className="text-left">
                <p className="text-xs font-medium text-zinc-200">
                  Adicionar Documento
                </p>
                <p className="text-[10px] text-zinc-500 font-mono">
                  PDF, TXT ou MD
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      {statusMessage && (
        <div
          className={`mt-2 flex items-start space-x-2 p-2 rounded-lg text-xs border ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-300'
              : 'bg-rose-950/20 border-rose-800/40 text-rose-300'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
          )}
          <span className="text-[11px] leading-tight">{statusMessage.text}</span>
        </div>
      )}
    </div>
  );
};
