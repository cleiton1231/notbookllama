export interface EvalTurnPayload {
  query: string;
  answer: string;
  context_chunks: string[];
  retrieved_chunk_ids: string[];
}

type EvalMessage = {
  role: string;
  content: string;
  sources?: Array<{ filename: string; chunk_index: number; snippet: string }>;
};

export function buildEvalTurnPayload(
  messages: EvalMessage[],
  assistantIndex: number
): EvalTurnPayload | null {
  const assistant = messages[assistantIndex];
  if (!assistant || assistant.role !== 'assistant') return null;

  const answer = assistant.content.trim();
  if (!answer) return null;

  let query: string | null = null;
  for (let i = assistantIndex - 1; i >= 0; i--) {
    if (messages[i].role === 'user') {
      query = messages[i].content;
      break;
    }
  }
  if (query === null) return null;

  const sources = assistant.sources || [];
  const context_chunks = sources
    .map((s) => (s.snippet || '').trim())
    .filter((snippet) => snippet.length > 0);
  const retrieved_chunk_ids = sources.map((s) => `${s.filename}#${s.chunk_index}`);

  return {
    query,
    answer,
    context_chunks,
    retrieved_chunk_ids,
  };
}
