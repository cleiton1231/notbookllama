import { describe, it, expect } from 'vitest';
import { emptyChatMode, isChatReady } from './chatStatus';
import type { HealthResponse } from '../types';

const baseHealth = (online: { chat: boolean; embed: boolean; rerank?: boolean }): HealthResponse => ({
  status: online.chat && online.embed ? 'healthy' : 'degraded',
  chat_endpoint: {
    name: 'chat',
    url: 'http://127.0.0.1:8080',
    online: online.chat,
  },
  embed_endpoint: {
    name: 'embed',
    url: 'http://127.0.0.1:8081',
    online: online.embed,
  },
  rerank_endpoint: {
    name: 'rerank',
    url: 'http://127.0.0.1:8082',
    online: online.rerank ?? false,
  },
  total_indexed_documents: 0,
  total_indexed_chunks: 0,
});

describe('isChatReady', () => {
  it('is false when health is null or any required endpoint is offline', () => {
    expect(isChatReady(null)).toBe(false);
    expect(isChatReady(baseHealth({ chat: true, embed: false }))).toBe(false);
    expect(isChatReady(baseHealth({ chat: false, embed: true }))).toBe(false);
  });

  it('is true when chat and embed are online even if rerank is offline', () => {
    expect(isChatReady(baseHealth({ chat: true, embed: true, rerank: false }))).toBe(true);
  });
});

describe('emptyChatMode', () => {
  it('returns no-docs when library is empty', () => {
    expect(emptyChatMode(0)).toBe('no-docs');
    expect(emptyChatMode(2)).toBe('ready');
  });
});
