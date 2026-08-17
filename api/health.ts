import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  const groqOk = !!process.env.GROQ_API_KEY;
  const qdrantOk = !!(process.env.QDRANT_URL && process.env.QDRANT_API_KEY);
  
  const status = (groqOk && qdrantOk) ? "healthy" : "degraded";

  return res.status(200).json({
    status: status,
    ready: status === "healthy",
    groq: groqOk ? "configured" : "missing",
    qdrant: qdrantOk ? "configured" : "missing"
  });
}
