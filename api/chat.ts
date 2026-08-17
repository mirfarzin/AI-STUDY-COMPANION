import type { VercelRequest, VercelResponse } from '@vercel/node';
import { semanticSearch, SearchResult } from '../lib/qdrant';
import { chatWithContext } from '../lib/groq';
import { CHAT_SYSTEM_PROMPT } from '../lib/prompts';

interface ChatRequest {
  query?: string;
  message?: string;
  subject?: string;
}

interface Citation {
  source: string;
  type: string;
  similarity: number;
}

function distanceToSimilarity(score: number): number {
  return Math.max(0, Math.min(100, Math.round(score * 100)));
}

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method Not Allowed' });
  }

  const body = (req.body || {}) as ChatRequest;
  const user_query = (body.query || body.message || '').trim();

  if (!user_query) {
    return res.status(400).json({ detail: 'Query cannot be empty.' });
  }

  const subject = body.subject?.trim() || null;

  let chunk_results: SearchResult[] = [];
  try {
    chunk_results = await semanticSearch(user_query, 5, subject || undefined);
  } catch (error: any) {
    console.error(`[ERROR] Qdrant semantic_search failed: ${error}`);
    return res.status(503).json({ detail: 'Vector database query failed. Please try again.' });
  }

  // Fallback retrieval: if no chunks found with subject filter, search across all subjects
  if ((!chunk_results || chunk_results.length === 0) && subject) {
    try {
      chunk_results = await semanticSearch(user_query, 5);
    } catch (error: any) {
      console.warn(`[WARN] Fallback semantic_search failed: ${error}`);
    }
  }

  if (!chunk_results || chunk_results.length === 0) {
    const subjectMsg = subject ? ` for subject: ${subject}` : '';
    return res.status(404).json({
      detail: `No relevant content found${subjectMsg}. Please ensure notes are uploaded.`
    });
  }

  const texts = chunk_results.map(c => c.text);
  const citations: Citation[] = chunk_results.map(c => ({
    source: c.filename || c.subject || 'Unknown Document',
    type: 'PDF Notes',
    similarity: distanceToSimilarity(c.score),
  }));

  const seen: Record<string, Citation> = {};
  for (const cit of citations) {
    const key = cit.source;
    if (!seen[key] || cit.similarity > seen[key].similarity) {
      seen[key] = cit;
    }
  }

  const unique_citations = Object.values(seen).sort((a, b) => b.similarity - a.similarity);

  const context_text = texts.join('\n\n---\n\n');
  const messages = [
    {
      role: 'system',
      content: CHAT_SYSTEM_PROMPT,
    },
    {
      role: 'user',
      content: `Context from study notes:\n\n${context_text}\n\nQuestion: ${user_query}`,
    },
  ];

  let answer = '';
  try {
    answer = await chatWithContext(messages, { temperature: 0.7 });
  } catch (error: any) {
    console.error(`[ERROR] Groq call failed in chat: ${error}`);
    return res.status(502).json({ detail: 'AI service temporarily unavailable.' });
  }

  if (!answer || answer.startsWith('Error:')) {
    return res.status(502).json({ detail: `AI service error: ${answer}` });
  }

  return res.status(200).json({
    answer: answer,
    subject: subject,
    citations: unique_citations,
  });
}
