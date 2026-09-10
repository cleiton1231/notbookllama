import { SourceReference } from '../types';

export type SseHandlers = {
  onSources: (sources: SourceReference[]) => void;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (error: string) => void;
};

export function createSseParser(handlers: SseHandlers) {
  let buffer = '';
  let currentEvent = '';
  let isTerminal = false;

  const markDone = () => {
    if (isTerminal) return;
    isTerminal = true;
    handlers.onDone();
  };

  const markError = (message: string) => {
    if (isTerminal) return;
    isTerminal = true;
    handlers.onError(message);
  };

  const dispatch = (eventName: string, dataStr: string) => {
    if (isTerminal || !dataStr) return;
    try {
      const data = JSON.parse(dataStr);
      if (eventName === 'sources') {
        handlers.onSources(data.sources || []);
      } else if (eventName === 'token') {
        handlers.onToken(data.token || '');
      } else if (eventName === 'error') {
        markError(data.error || 'Erro desconhecido');
      } else if (eventName === 'done') {
        markDone();
      }
    } catch (e) {
      console.error('Erro ao decodificar JSON do evento SSE:', dataStr, e);
    }
  };

  const consumeLine = (rawLine: string) => {
    const line = rawLine.trim();
    if (!line) {
      currentEvent = '';
      return;
    }
    if (line.startsWith('event:')) {
      currentEvent = line.slice(6).trim();
      return;
    }
    if (line.startsWith('data:')) {
      dispatch(currentEvent, line.slice(5).trim());
    }
  };

  return {
    push(chunk: string) {
      if (isTerminal) return;
      buffer += chunk;
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        consumeLine(line);
      }
    },
    finish() {
      if (buffer.trim()) {
        consumeLine(buffer);
        buffer = '';
      }
      markDone();
    },
  };
}
