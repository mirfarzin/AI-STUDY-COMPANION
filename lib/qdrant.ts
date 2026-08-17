import { QdrantClient } from '@qdrant/js-client-rest';
import * as dotenv from 'dotenv';
import { getQueryEmbedding } from './embeddings';

dotenv.config();

const qdrantUrl = process.env.QDRANT_URL;
const qdrantApiKey = process.env.QDRANT_API_KEY;

export const COLLECTION_NAME = 'vtu_study_companion';

let clientInstance: QdrantClient | null = null;

/**
 * Retrieves a singleton instance of the Qdrant Client.
 */
export function getQdrantClient(): QdrantClient {
  if (!clientInstance) {
    if (!qdrantUrl || !qdrantApiKey) {
      console.warn('[WARNING] QDRANT_URL or QDRANT_API_KEY is missing.');
    }
    
    clientInstance = new QdrantClient({
      url: qdrantUrl || 'http://localhost:6333',
      apiKey: qdrantApiKey || '',
    });
  }
  return clientInstance;
}

/**
 * Fetch collection statistics and extract unique subjects.
 */
export async function getCollectionStats() {
  const client = getQdrantClient();
  try {
    const collectionInfo = await client.getCollection(COLLECTION_NAME);
    const total_chunks = collectionInfo.points_count || 0;
    
    const subjects = new Set<string>();
    let offset: any = undefined;
    
    do {
      const response = await client.scroll(COLLECTION_NAME, {
        limit: 1000,
        offset: offset,
        with_payload: true,
        with_vector: false
      });
      
      for (const point of response.points) {
        if (point.payload && typeof point.payload.subject === 'string') {
          subjects.add(point.payload.subject);
        }
      }
      
      // The scroll API returns next_page_offset
      offset = response.next_page_offset;
    } while (offset !== null && offset !== undefined);
    
    return {
      total_chunks,
      subjects: Array.from(subjects).sort(),
      doc_types: {}
    };
  } catch (error) {
    console.error('[ERROR] Qdrant stats failed:', error);
    return { total_chunks: 0, subjects: [], doc_types: {} };
  }
}

/**
 * Fetch all chunks (used by Predict endpoint)
 */
export async function getAllChunks(where?: any): Promise<Array<{text: string, metadata: any}>> {
  const client = getQdrantClient();
  try {
    const out: Array<{text: string, metadata: any}> = [];
    let offset: any = undefined;
    
    const subjectEq = where?.subject?.$eq;
    const filter = subjectEq ? { must: [{ key: 'subject', match: { value: subjectEq } }] } : undefined;

    do {
      const response = await client.scroll(COLLECTION_NAME, {
        filter: filter,
        limit: 1000,
        offset: offset,
        with_payload: true,
        with_vector: false
      });
      
      for (const p of response.points) {
        const payload = p.payload || {};
        const text = (payload.text as string) || '';
        const metadata = { ...payload };
        delete metadata.text;
        
        out.push({ text, metadata });
      }
      
      offset = response.next_page_offset;
    } while (offset !== null && offset !== undefined);
    
    return out;
  } catch (error) {
    console.error('[ERROR] Qdrant scroll failed:', error);
    return [];
  }
}

export interface SearchResult {
  text: string;
  subject: string;
  unit: string;
  doc_type: string;
  filename: string;
  score: number;
}

/**
 * Perform a semantic vector search
 */
export async function semanticSearch(
  query: string,
  n_results = 5,
  subject?: string,
  unit?: string,
  doc_type?: string
): Promise<SearchResult[]> {
  const client = getQdrantClient();
  
  try {
    const qEmb = await getQueryEmbedding(query);
    
    const mustConditions: any[] = [];
    if (subject) mustConditions.push({ key: 'subject', match: { value: subject } });
    if (unit) mustConditions.push({ key: 'unit', match: { value: unit } });
    if (doc_type) mustConditions.push({ key: 'doc_type', match: { value: doc_type } });
    
    const filter = mustConditions.length > 0 ? { must: mustConditions } : undefined;
    
    const results = await client.query(COLLECTION_NAME, {
      query: qEmb,
      filter: filter,
      limit: n_results,
      with_payload: true,
    });
    
    return results.points.map((r: any) => ({
      text: (r.payload?.text as string) || '',
      subject: (r.payload?.subject as string) || '',
      unit: (r.payload?.unit as string) || '',
      doc_type: (r.payload?.doc_type as string) || '',
      filename: (r.payload?.filename as string) || '',
      score: r.score,
    }));
  } catch (error) {
    console.error('[ERROR] Qdrant search failed:', error);
    return [];
  }
}

/**
 * Query chunks for legacy wrapper
 */
export async function queryChunks(q: string, n = 5, where?: any): Promise<SearchResult[]> {
  const subject = where?.subject?.$eq;
  return semanticSearch(q, n, subject);
}
