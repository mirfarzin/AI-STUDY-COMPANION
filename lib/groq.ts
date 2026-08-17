import { Groq } from 'groq-sdk';
import * as dotenv from 'dotenv';

dotenv.config();

const apiKey = process.env.GROQ_API_KEY;
if (!apiKey) {
  console.warn('[WARNING] GROQ_API_KEY is not set in environment.');
}

/**
 * Singleton Groq client instance.
 * Automatically picks up GROQ_API_KEY from the environment.
 */
export const groqClient = new Groq({
  apiKey: apiKey || '',
});

/**
 * Helper to get the standard chat model.
 */
export function getChatModel(): string {
  return 'llama-3.1-8b-instant';
}

export interface ChatOptions {
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  jsonMode?: boolean;
}

/**
 * Utility function to send a standard chat completion request.
 */
export async function chatWithContext(messages: Array<{role: string, content: string}>, options: ChatOptions = {}): Promise<string> {
  const model = options.model || getChatModel();
  const temperature = options.temperature !== undefined ? options.temperature : 0.7;
  
  const requestParams: any = {
    model: model,
    messages: messages,
    temperature: temperature,
  };

  if (options.max_tokens !== undefined) {
    requestParams.max_tokens = options.max_tokens;
  }
  if (options.top_p !== undefined) {
    requestParams.top_p = options.top_p;
  }
  if (options.jsonMode) {
    requestParams.response_format = { type: 'json_object' };
  }

  const response = await groqClient.chat.completions.create(requestParams);
  return response.choices[0]?.message?.content || '';
}

/**
 * Generates prediction questions for a given subject.
 * Corrects a legacy defect by clearly separating the Subject, Context, and Prediction Task.
 */
export async function predictQuestions(subject: string, contextTexts: string[], unit?: string, numQuestions = 5): Promise<{ questions: string, subject: string, unit: string | null }> {
  const contextText = contextTexts.join('\n\n---\n\n');
  
  const prompt = `Prediction Task: Generate ${numQuestions} important questions for the subject: ${subject}${unit ? ` - Unit ${unit}` : ''}.
Return the result as a JSON array with 'question' and 'difficulty' fields.

Subject: ${subject}
Retrieved Context:
${contextText}`;

  const messages = [{ role: 'user', content: prompt }];
  
  try {
    const responseText = await chatWithContext(messages, { temperature: 0.7 });
    return {
      questions: responseText,
      subject: subject,
      unit: unit || null
    };
  } catch (error: any) {
    console.error('[ERROR] Predict questions failed:', error);
    // Mimicking python behavior where exceptions were caught and returned as {"error": str(e)}
    // Wait, the new shared error strategy for Vercel is to let exceptions throw, but Python returned {"error": str(e)} here.
    // The instruction says "For the new TypeScript implementation: shared Groq client throws exceptions... endpoint catches exceptions". 
    // I will throw the exception here so the endpoint can catch it.
    throw error;
  }
}

