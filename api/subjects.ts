import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getCollectionStats } from '../lib/qdrant';

const DEFAULT_SUBJECTS = [
    "AI and ML",
    "Analysis and Design of Algorithms",
    "Computer Networks",
    "Data Science",
    "Database Management Systems",
    "Microcontrollers",
    "Operating Systems",
    "Software Engineering",
    "Mathematics ChemistryCycle",
    "Mathematics PhysicsCycle",
    "PLC",
    "Physics",
    "Principles of Programming C",
    "Professional Writing English"
];

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

  // Return default subjects if Qdrant is not available or empty
  return res.status(200).json({ subjects: DEFAULT_SUBJECTS });
}
