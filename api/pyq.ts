import type { VercelRequest, VercelResponse } from '@vercel/node';
import { queryChunks } from '../lib/qdrant';
import { chatWithContext } from '../lib/groq';
import { PYQ_SYSTEM_PROMPT } from '../lib/prompts';

interface PYQRequest {
  question: string;
  subject?: string;
}

interface SourceCitation {
  subject: string;
  filename: string;
  page: number;
  excerpt: string;
}

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method Not Allowed' });
  }

  const body = req.body as PYQRequest;
  if (!body || typeof body.question !== 'string') {
    return res.status(422).json({ detail: "Field required: question" });
  }

  const question = body.question.trim();
  if (!question) {
    return res.status(400).json({ detail: "Question cannot be empty." });
  }

  const subject = body.subject?.trim() || undefined;
  const where_clause = subject ? { subject: { $eq: subject } } : undefined;

  // Top-k=5 chunks
  const chunk_results = await queryChunks(question, 5, where_clause);

  if (!chunk_results || chunk_results.length === 0) {
    return res.status(404).json({ detail: "No relevant context found for this question." });
  }

  const texts = chunk_results.map(c => c.text);

  const sources: SourceCitation[] = chunk_results.map(c => ({
    subject: c.subject || "Unknown",
    filename: c.filename || "Unknown Document",
    page: (c as any).page || 1,
    excerpt: c.text.length > 100 ? c.text.slice(0, 100) + "..." : c.text
  }));

  // Deduplicate sources based on filename and excerpt
  const seen = new Set<string>();
  const unique_sources: SourceCitation[] = [];
  for (const s of sources) {
    const key = `${s.filename}_${s.excerpt}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique_sources.push(s);
    }
  }

  const context_text = texts.join("\n\n---\n\n");
  const messages = [
    {
      role: "system",
      content: PYQ_SYSTEM_PROMPT
    },
    {
      role: "user",
      content: `Context:\n${context_text}\n\nQuestion: ${question}`
    }
  ];

  let answer = "";
  try {
    answer = await chatWithContext(messages, { temperature: 0.7 });
  } catch (error: any) {
    console.error(`[ERROR] Groq call failed in pyq: ${error}`);
    return res.status(502).json({ detail: "AI service temporarily unavailable." });
  }

  if (!answer || answer.startsWith("Error:")) {
    return res.status(502).json({ detail: `AI service error: ${answer}` });
  }

  const confidence = chunk_results.length >= 3 ? "High" : "Medium";

  return res.status(200).json({
    answer: answer,
    sources: unique_sources,
    confidence: confidence
  });
}
