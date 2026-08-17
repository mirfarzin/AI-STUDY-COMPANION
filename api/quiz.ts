import type { VercelRequest, VercelResponse } from '@vercel/node';
import { queryChunks } from '../lib/qdrant';
import { chatWithContext } from '../lib/groq';
import { getQuizSystemPrompt } from '../lib/prompts';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ detail: 'Method Not Allowed' });
  }

  const subject = req.query.subject as string;
  const difficulty = (req.query.difficulty as string) || "medium";
  const topic = req.query.topic as string | undefined;

  if (!subject) {
    return res.status(422).json({ detail: "Field required: subject" });
  }

  const query_text = topic ? topic : `core concepts and important definitions in ${subject}`;
  const where_clause = { subject: { $eq: subject } };

  const chunk_results = await queryChunks(query_text, 8, where_clause);

  if (!chunk_results || chunk_results.length === 0) {
    return res.status(404).json({ detail: "No relevant context found to generate a quiz for this subject." });
  }

  const texts = chunk_results.map(c => c.text);
  const context_text = texts.join("\n\n---\n\n");

  const sys_prompt = getQuizSystemPrompt(difficulty);

  const messages = [
    { role: "system", content: sys_prompt },
    { role: "user", content: `Context:\n${context_text}` }
  ];

  let response_text = "";
  try {
    response_text = await chatWithContext(messages);
  } catch (error: any) {
    console.error(`[ERROR] Groq call failed in quiz: ${error}`);
    return res.status(502).json({ detail: "AI service temporarily unavailable." });
  }

  if (!response_text || response_text.startsWith("Error:")) {
    return res.status(502).json({ detail: `AI service error: ${response_text}` });
  }

  try {
    const cleaned_text = response_text.replace(/```json/g, "").replace(/```/g, "").trim();
    const quiz_data = JSON.parse(cleaned_text);
    if (!Array.isArray(quiz_data) || quiz_data.length === 0) {
      throw new Error("LLM did not return a valid list of questions.");
    }
    return res.status(200).json(quiz_data);
  } catch (error: any) {
    console.error(`Error parsing quiz JSON from Groq: ${error}\nRaw output: ${response_text}`);
    return res.status(400).json({ detail: "Invalid JSON from LLM" });
  }
}
