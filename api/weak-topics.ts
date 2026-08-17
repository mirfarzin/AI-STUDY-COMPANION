import type { VercelRequest, VercelResponse } from '@vercel/node';
import { chatWithContext } from '../lib/groq';
import { WEAK_TOPICS_SYSTEM_PROMPT } from '../lib/prompts';

interface IncorrectQuestion {
  question: string;
  user_answer?: string;
  correct_answer?: string;
  selected?: string;
  correct?: string;
}

interface WeakTopicsRequest {
  subject: string;
  incorrect_questions: IncorrectQuestion[];
}

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method Not Allowed' });
  }

  const body = req.body as WeakTopicsRequest;
  if (!body || !body.incorrect_questions || body.incorrect_questions.length === 0) {
    return res.status(200).json([]);
  }

  let questions_context = "";
  body.incorrect_questions.forEach((q, i) => {
    // Handle frontend fields mapping identical to Python's handle_frontend_fields
    const user_answer = q.user_answer || q.selected || "";
    const correct_answer = q.correct_answer || q.correct || "";

    questions_context += `Q${i + 1}: ${q.question}\nUser selected: ${user_answer}\nCorrect answer: ${correct_answer}\n\n`;
  });

  const messages = [
    { role: "system", content: WEAK_TOPICS_SYSTEM_PROMPT },
    { role: "user", content: `Subject: ${body.subject}\n\nMissed Questions:\n${questions_context}` },
  ];

  let response_text = "";
  try {
    response_text = await chatWithContext(messages, { temperature: 0.7 });
  } catch (error: any) {
    console.error(`[ERROR] Groq call failed in weak-topics: ${error}`);
    return res.status(502).json({ detail: "AI service temporarily unavailable." });
  }

  if (!response_text || response_text.startsWith("Error:")) {
    return res.status(502).json({ detail: `AI service error: ${response_text}` });
  }

  try {
    const cleaned = response_text.replace(/```json/g, "").replace(/```/g, "").trim();
    const analysis = JSON.parse(cleaned);
    
    if (!Array.isArray(analysis)) {
      throw new Error("LLM did not return a JSON list");
    }
    
    return res.status(200).json(analysis);
  } catch (error: any) {
    console.error(`Error parsing weak topics JSON: ${error}\nRaw: ${response_text}`);
    return res.status(400).json({ detail: "Invalid JSON from LLM" });
  }
}
