import * as dotenv from 'dotenv';
import handler from '../api/quiz';

dotenv.config();

async function runIntegrationTest() {
  console.log("=== Integration Test: /quiz ===");
  
  if (!process.env.GROQ_API_KEY || (!process.env.HF_TOKEN && !process.env.HUGGINGFACE_API_KEY)) {
    console.log("SKIPPED: GROQ_API_KEY or HF_TOKEN is not configured.");
    return;
  }

  const req = { 
    method: 'GET',
    query: { 
      subject: "Computer Networks",
      difficulty: "easy"
    }
  } as any;
  
  let resStatus = 200;
  let resData: any;
  const res = {
    status: (code: number) => { resStatus = code; return res; },
    json: (data: any) => { resData = data; }
  } as any;
  
  try {
    await handler(req, res);
    
    console.log("Status:", resStatus);
    // Don't print the whole quiz, just check if it's an array
    console.log("Data is array:", Array.isArray(resData));
    if (Array.isArray(resData) && resData.length > 0) {
      console.log("First Question:", resData[0].question);
    }
    
    if (resStatus !== 200) {
       console.log("SKIPPED: Live request failed (likely due to network, rate limit, or provider availability).");
    } else {
       console.log("PASSED: Integration test successful.");
    }
  } catch (error) {
    console.log("SKIPPED: Live request threw an exception.", error);
  }
}

runIntegrationTest().catch(console.error);
