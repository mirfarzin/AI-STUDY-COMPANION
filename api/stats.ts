import type { VercelRequest, VercelResponse } from '@vercel/node';
import { getCollectionStats, getQdrantClient } from '../lib/qdrant';

export default async function handler(
  req: VercelRequest,
  res: VercelResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ detail: 'Method Not Allowed' });
  }

  const qdrantUrl = process.env.QDRANT_URL;
  const qdrantApiKey = process.env.QDRANT_API_KEY;

  if (!qdrantUrl || !qdrantApiKey) {
    return res.status(503).json({
      detail: "Qdrant not initialized: Qdrant credentials (QDRANT_URL, QDRANT_API_KEY) not configured. Please configure QDRANT_URL and QDRANT_API_KEY environment variables."
    });
  }

  try {
    // Emulate VECTOR_DB_READY check by testing connection
    const client = getQdrantClient();
    await client.getCollections(); 
  } catch (error: any) {
    return res.status(503).json({
      detail: `Qdrant not initialized: ${error.message}. Please configure QDRANT_URL and QDRANT_API_KEY environment variables.`
    });
  }

  try {
    const stats = await getCollectionStats();
    return res.status(200).json(stats);
  } catch (error: any) {
    return res.status(500).json({
      detail: `Failed to retrieve stats: ${error.message}`
    });
  }
}
