import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getAllChunks } from '../lib/qdrant';
import { predictQuestions } from '../lib/groq';

interface PredictRequest {
  subject: string;
}

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method Not Allowed' });
  }

  const body = req.body as PredictRequest;
  if (!body || !body.subject) {
    return res.status(422).json({ detail: "Field required: subject" });
  }

  try {
    // Get all chunks matching the subject
    const chunks = await getAllChunks({ subject: { $eq: body.subject } });
    
    if (!chunks || chunks.length === 0) {
      return res.status(404).json({ detail: "Subject not found or contains no content." });
    }

    // Extract just the text strings (up to 20)
    const texts = chunks.slice(0, 20).map(c => c.text);

    // Call the shared groq client
    // predictQuestions now properly accepts subject and context texts
    const questionsResult = await predictQuestions(body.subject, texts);

    // Return the legacy nested structure matching Python perfectly, 
    // EXCEPT we no longer pass the array of chunks into the `subject` field, 
    // because that was part of the internal implementation defect.
    return res.status(200).json({
      questions: questionsResult, // { questions: string, subject: string, unit: null }
      subject: body.subject
    });
  } catch (error: any) {
    console.error('[ERROR] /predict failed:', error);
    // Mimic the Python error handling where exceptions inside predict_questions
    // returned {"error": str(e)} which the route blindly passed through in `questions`
    return res.status(200).json({
      questions: { error: String(error.message || error) },
      subject: body.subject
    });
  }
}
