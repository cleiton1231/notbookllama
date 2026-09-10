import { describe, it, expect, vi } from 'vitest';
import { createSseParser } from './sse';

function handlers() {
  return {
    onSources: vi.fn(),
    onToken: vi.fn(),
    onDone: vi.fn(),
    onError: vi.fn(),
  };
}

describe('createSseParser', () => {
  it('keeps event type across TCP fragments', () => {
    const h = handlers();
    const parser = createSseParser(h);
    parser.push('event: token\n');
    parser.push('data: {"token":"Hi"}\n\n');
    expect(h.onToken).toHaveBeenCalledWith('Hi');
  });

  it('fires onDone only once when event:done is followed by finish', () => {
    const h = handlers();
    const parser = createSseParser(h);
    parser.push('event: done\ndata: {}\n\n');
    parser.finish();
    expect(h.onDone).toHaveBeenCalledTimes(1);
  });

  it('does not call onDone after event:error', () => {
    const h = handlers();
    const parser = createSseParser(h);
    parser.push('event: error\ndata: {"error":"boom"}\n\n');
    parser.finish();
    expect(h.onError).toHaveBeenCalledTimes(1);
    expect(h.onError).toHaveBeenCalledWith('boom');
    expect(h.onDone).not.toHaveBeenCalled();
  });
});
