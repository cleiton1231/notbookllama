import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect } from 'vitest';

vi.mock('../services/api', () => ({
  uploadDocument: vi.fn(),
}));

import { uploadDocument } from '../services/api';
import { FileUpload } from './FileUpload';

describe('FileUpload OCR notice', () => {
  it('shows OCR notice when document.ocr_used is true', async () => {
    vi.mocked(uploadDocument).mockResolvedValue({
      message: "Documento 'scan.pdf' indexado com OCR (PDF escaneado).",
      document: {
        doc_id: '1',
        filename: 'scan.pdf',
        file_type: 'pdf',
        file_size: 10,
        sha256: 'a',
        total_chunks: 1,
        created_at: '2026-01-01',
        ocr_used: true,
      },
    });

    render(<FileUpload onUploadSuccess={() => {}} />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['x'], 'scan.pdf', { type: 'application/pdf' });
    await userEvent.upload(input, file);

    expect(await screen.findByText(/Texto extraído via Tesseract/i)).toBeInTheDocument();
    expect(screen.getByTestId('ocr-upload-notice')).toBeInTheDocument();
  });

  it('does not show OCR notice when ocr_used is false', async () => {
    vi.mocked(uploadDocument).mockResolvedValue({
      message: "Documento 'doc.pdf' indexado com sucesso!",
      document: {
        doc_id: '2',
        filename: 'doc.pdf',
        file_type: 'pdf',
        file_size: 10,
        sha256: 'b',
        total_chunks: 1,
        created_at: '2026-01-01',
        ocr_used: false,
      },
    });

    render(<FileUpload onUploadSuccess={() => {}} />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['x'], 'doc.pdf', { type: 'application/pdf' });
    await userEvent.upload(input, file);

    expect(await screen.findByText(/indexado com sucesso/i)).toBeInTheDocument();
    expect(screen.queryByTestId('ocr-upload-notice')).not.toBeInTheDocument();
  });
});
