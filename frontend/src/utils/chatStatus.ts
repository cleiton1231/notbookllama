import type { HealthResponse } from '../types';

export function isChatReady(health: HealthResponse | null): boolean {
  return Boolean(health?.chat_endpoint.online && health?.embed_endpoint.online);
}

export function emptyChatMode(documentsLength: number): 'no-docs' | 'ready' {
  return documentsLength === 0 ? 'no-docs' : 'ready';
}
