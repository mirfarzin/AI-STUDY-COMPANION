/**
 * lib/embeddings.ts
 * Generates dense vector embeddings for search queries at runtime.
 * Uses the exact same model (BAAI/bge-small-en-v1.5) as the offline ingestion.
 */

const MODEL = 'BAAI/bge-small-en-v1.5';
const HF_API_URL = `https://api-inference.huggingface.co/pipeline/feature-extraction/${MODEL}`;

/**
 * Fetch a 384-dimensional dense vector for a query string.
 */
export async function getQueryEmbedding(query: string): Promise<number[]> {
  const token = process.env.HF_TOKEN || process.env.HUGGINGFACE_API_KEY;
  if (!token) {
    throw new Error('HuggingFace API token missing (HF_TOKEN or HUGGINGFACE_API_KEY)');
  }

  const response = await fetch(HF_API_URL, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ inputs: query }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Embedding API failed (${response.status}): ${text}`);
  }

  const result = await response.json();
  
  // The API returns either a 1D array of numbers, or a 2D array if multiple inputs.
  // We passed a single string, so it should be number[] or [number[]]
  if (Array.isArray(result) && Array.isArray(result[0])) {
    return result[0];
  } else if (Array.isArray(result) && typeof result[0] === 'number') {
    return result as number[];
  }

  throw new Error('Unexpected embedding format received from HuggingFace API');
}
