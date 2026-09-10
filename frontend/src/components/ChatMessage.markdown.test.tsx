import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ChatMessage } from './ChatMessage';

describe('ChatMessage markdown', () => {
  it('renders GFM tables and highlighted fenced code', () => {
    const content = [
      '| A | B |',
      '| --- | --- |',
      '| 1 | 2 |',
      '',
      '```python',
      'def f():',
      '    return 1',
      '```',
    ].join('\n');

    render(
      <ChatMessage
        message={{
          id: '1',
          role: 'assistant',
          content,
          timestamp: '2026-01-01',
        }}
        messageIndex={0}
        isLast
        isGenerating={false}
        onOpenSource={() => {}}
      />
    );

    expect(screen.getByRole('table')).toBeInTheDocument();
    const code = document.querySelector('pre code');
    expect(code).toBeTruthy();
    expect(
      code?.className.includes('hljs') ||
        code?.className.includes('language-python') ||
        Boolean(code?.querySelector('.hljs-keyword'))
    ).toBe(true);
  });

  it('opens markdown links in a new tab with noopener', () => {
    render(
      <ChatMessage
        message={{
          id: '2',
          role: 'assistant',
          content: '[docs](https://example.com)',
          timestamp: '2026-01-01',
        }}
        messageIndex={0}
        isLast
        isGenerating={false}
        onOpenSource={() => {}}
      />
    );

    const link = screen.getByRole('link', { name: 'docs' });
    expect(link).toHaveAttribute('href', 'https://example.com');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link.getAttribute('rel') || '').toContain('noopener');
  });
});
