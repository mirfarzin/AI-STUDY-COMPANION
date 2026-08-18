import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getCollectionStats, AUTHORITATIVE_FIRST_YEAR_SUBJECTS } from '../lib/qdrant';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    const stats = await getCollectionStats();
    const subjects = stats.subjects || [];
    
    if (subjects.length > 0) {
      return res.status(200).json({ subjects });
    }
  } catch (error) {
    console.error("Error fetching subjects from Qdrant:", error);
  }

  // Return authoritative 14 subjects if Qdrant is not available or empty
  return res.status(200).json({ subjects: AUTHORITATIVE_FIRST_YEAR_SUBJECTS });
}

