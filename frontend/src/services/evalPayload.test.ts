import { describe, it, expect } from 'vitest';
import { buildEvalTurnPayload } from './evalPayload';

describe('buildEvalTurnPayload', () => {
  it('builds payload from preceding user message and assistant sources', () => {
    const messages = [
      { role: 'user', content: 'O que é RAG?' },
      {
        role: 'assistant',
        content: 'RAG combina recuperação e geração.',
        sources: [
          { filename: 'doc.pdf', chunk_index: 3, snippet: 'Retrieval Augmented Generation' },
          { filename: 'doc.pdf', chunk_index: 4, snippet: '' },
        ],
      },
    ];

    const payload = buildEvalTurnPayload(messages, 1);
    expect(payload).toEqual({
      query: 'O que é RAG?',
      answer: 'RAG combina recuperação e geração.',
      context_chunks: ['Retrieval Augmented Generation'],
      retrieved_chunk_ids: ['doc.pdf#3', 'doc.pdf#4'],
    });
  });

  it('returns null when there is no preceding user message', () => {
    const messages = [{ role: 'assistant', content: 'Olá' }];
    expect(buildEvalTurnPayload(messages, 0)).toBeNull();
  });

  it('returns null for non-assistant target or empty answer', () => {
    const messages = [
      { role: 'user', content: 'Oi' },
      { role: 'assistant', content: '   ' },
    ];
    expect(buildEvalTurnPayload(messages, 0)).toBeNull();
    expect(buildEvalTurnPayload(messages, 1)).toBeNull();
  });
});
