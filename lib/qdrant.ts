import { QdrantClient } from '@qdrant/js-client-rest';
import * as dotenv from 'dotenv';
import * as path from 'path';
import { getQueryEmbedding } from './embeddings';

// Load backend/.env as well as root .env
dotenv.config({ path: path.resolve(process.cwd(), 'backend/.env') });
dotenv.config();

export const COLLECTION_NAME = 'vtu_study_companion';

/**
 * Authoritative 14 First-Year CSE / AIML subjects
 * Physics Cycle:
 * 1. Mathematics
 * 2. Physics
 * 3. Communication English
 * 4. Kannada Kali / Manasu
 * 5. A Scientific Approach to Health
 * 6. Principles of Programming Using C
 * 7. ESC
 * 8. PLC
 * 
 * Chemistry Cycle:
 * 9. Chemistry
 * 10. Professional Writing Skills in English
 * 11. Constitution of India
 * 12. Design Thinking
 * 13. Computer-Aided Engineering Drawing
 * 14. ETC
 */
export const AUTHORITATIVE_FIRST_YEAR_SUBJECTS: string[] = [
  "Mathematics",
  "Physics",
  "Communication English",
  "Kannada Kali / Manasu",
  "A Scientific Approach to Health",
  "Principles of Programming Using C",
  "ESC",
  "PLC",
  "Chemistry",
  "Professional Writing Skills in English",
  "Constitution of India",
  "Design Thinking",
  "Computer-Aided Engineering Drawing",
  "ETC"
];

// Set of explicitly excluded second-year or extraneous subjects
export const EXCLUDED_SUBJECTS = new Set<string>([
  "AI and ML",
  "Analysis and Design of Algorithms",
  "Computer Networks",
  "Data Science",
  "Database Management Systems",
  "Microcontrollers",
  "Operating Systems",
  "Software Engineering"
]);

// Map raw Qdrant payload subject strings to canonical first-year names
export const RAW_TO_CANONICAL_SUBJECT_MAP: Record<string, string> = {
  "CAED": "Computer-Aided Engineering Drawing",
  "Computer-Aided Engineering Drawing": "Computer-Aided Engineering Drawing",
  "Chemistry": "Chemistry",
  "Communication English": "Communication English",
  "Constitution of India": "Constitution of India",
  "Design Thinking": "Design Thinking",
  "ESC": "ESC",
  "ETC": "ETC",
  "Kannada Kali Manasu": "Kannada Kali / Manasu",
  "Kannada Kali / Manasu": "Kannada Kali / Manasu",
  "Mathematics ChemistryCycle": "Mathematics",
  "Mathematics PhysicsCycle": "Mathematics",
  "Mathematics": "Mathematics",
  "Physics": "Physics",
  "PLC": "PLC",
  "Principles of Programming C": "Principles of Programming Using C",
  "Principles of Programming Using C": "Principles of Programming Using C",
  "Professional Writing English": "Professional Writing Skills in English",
  "Professional Writing Skills in English": "Professional Writing Skills in English",
  "Scientific Approach to Health": "A Scientific Approach to Health",
  "A Scientific Approach to Health": "A Scientific Approach to Health"
};

// Map canonical first-year subjects to all matching raw subject values in Qdrant payloads
export const CANONICAL_TO_RAW_SUBJECT_MAP: Record<string, string[]> = {
  "Mathematics": ["Mathematics", "Mathematics ChemistryCycle", "Mathematics PhysicsCycle"],
  "Physics": ["Physics"],
  "Communication English": ["Communication English"],
  "Kannada Kali / Manasu": ["Kannada Kali / Manasu", "Kannada Kali Manasu"],
  "A Scientific Approach to Health": ["A Scientific Approach to Health", "Scientific Approach to Health"],
  "Principles of Programming Using C": ["Principles of Programming Using C", "Principles of Programming C"],
  "ESC": ["ESC"],
  "PLC": ["PLC"],
  "Chemistry": ["Chemistry"],
  "Professional Writing Skills in English": ["Professional Writing Skills in English", "Professional Writing English"],
  "Constitution of India": ["Constitution of India"],
  "Design Thinking": ["Design Thinking"],
  "Computer-Aided Engineering Drawing": ["Computer-Aided Engineering Drawing", "CAED"],
  "ETC": ["ETC"]
};

export function getRawSubjectFilterValues(subject: string): string[] {
  if (!subject) return [];
  const trimmed = subject.trim();
  if (CANONICAL_TO_RAW_SUBJECT_MAP[trimmed]) {
    return CANONICAL_TO_RAW_SUBJECT_MAP[trimmed];
  }
  const canonical = RAW_TO_CANONICAL_SUBJECT_MAP[trimmed];
  if (canonical && CANONICAL_TO_RAW_SUBJECT_MAP[canonical]) {
    return CANONICAL_TO_RAW_SUBJECT_MAP[canonical];
  }
  return [trimmed];
}

let clientInstance: QdrantClient | null = null;

/**
 * Retrieves a singleton instance of the Qdrant Client.
 */
export function getQdrantClient(): QdrantClient {
  if (!clientInstance) {
    const url = process.env.QDRANT_URL;
    const apiKey = process.env.QDRANT_API_KEY;

    if (!url || !apiKey) {
      console.warn('[WARNING] QDRANT_URL or QDRANT_API_KEY is missing.');
    }
    
    clientInstance = new QdrantClient({
      url: url || 'http://localhost:6333',
      apiKey: apiKey || '',
      checkCompatibility: false,
    });
  }
  return clientInstance;
}

/**
 * Fetch collection statistics and extract the 14 authoritative first-year subjects.
 */
export async function getCollectionStats() {
  const client = getQdrantClient();
  try {
    const collectionInfo = await client.getCollection(COLLECTION_NAME);
    const total_chunks = collectionInfo.points_count || 0;
    
    return {
      total_chunks,
      subjects: [...AUTHORITATIVE_FIRST_YEAR_SUBJECTS],
      doc_types: {}
    };
  } catch (error) {
    console.error('[ERROR] Qdrant stats failed:', error);
    return {
      total_chunks: 0,
      subjects: [...AUTHORITATIVE_FIRST_YEAR_SUBJECTS],
      doc_types: {}
    };
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
    let filter: any = undefined;

    if (subjectEq) {
      const rawValues = getRawSubjectFilterValues(subjectEq);
      filter = {
        must: [
          rawValues.length === 1
            ? { key: 'subject', match: { value: rawValues[0] } }
            : { key: 'subject', match: { any: rawValues } }
        ]
      };
    }

    do {
      const response = await client.scroll(COLLECTION_NAME, {
        filter: filter,
        limit: 1000,
        offset: offset,
        with_payload: true,
        with_vector: false
      });
      
      for (const p of response.points) {
        const payload = (p.payload || {}) as Record<string, any>;
        const rawSubj = payload.subject;
        if (rawSubj && EXCLUDED_SUBJECTS.has(rawSubj)) {
          continue;
        }

        const text = (payload.text as string) || '';
        const metadata = { ...payload };
        delete metadata.text;

        if (metadata.subject && RAW_TO_CANONICAL_SUBJECT_MAP[metadata.subject]) {
          metadata.subject = RAW_TO_CANONICAL_SUBJECT_MAP[metadata.subject];
        }
        
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
    if (subject) {
      const rawValues = getRawSubjectFilterValues(subject);
      if (rawValues.length === 1) {
        mustConditions.push({ key: 'subject', match: { value: rawValues[0] } });
      } else if (rawValues.length > 1) {
        mustConditions.push({ key: 'subject', match: { any: rawValues } });
      }
    }
    if (unit) mustConditions.push({ key: 'unit', match: { value: unit } });
    if (doc_type) mustConditions.push({ key: 'doc_type', match: { value: doc_type } });
    
    const filter = mustConditions.length > 0 ? { must: mustConditions } : undefined;
    
    const results = await client.query(COLLECTION_NAME, {
      query: qEmb,
      filter: filter,
      limit: n_results,
      with_payload: true,
    });
    
    return results.points
      .filter((r: any) => {
        const rawSubj = r.payload?.subject;
        return !(rawSubj && EXCLUDED_SUBJECTS.has(rawSubj));
      })
      .map((r: any) => {
        const rawSubj = (r.payload?.subject as string) || '';
        const canonicalSubj = RAW_TO_CANONICAL_SUBJECT_MAP[rawSubj] || rawSubj;
        return {
          text: (r.payload?.text as string) || '',
          subject: canonicalSubj,
          unit: (r.payload?.unit as string) || '',
          doc_type: (r.payload?.doc_type as string) || '',
          filename: (r.payload?.filename as string) || '',
          score: r.score,
        };
      });
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

