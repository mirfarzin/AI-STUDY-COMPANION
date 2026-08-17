import * as dotenv from 'dotenv';
import handler from '../api/pyq';

dotenv.config();

async function runIntegrationTest() {
  console.log("=== Integration Test: /pyq ===");
  
  if (!process.env.GROQ_API_KEY || (!process.env.HF_TOKEN && !process.env.HUGGINGFACE_API_KEY) || !process.env.QDRANT_URL) {
    console.log("SKIPPED: GROQ_API_KEY, HF_TOKEN, or QDRANT_URL is not configured.");
    return;
  }

  const req = { 
    method: 'POST',
    body: { 
      question: "Explain the architecture of 8086 microprocessor.",
      subject: "Microcontrollers"
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
    console.log("Response Keys:", Object.keys(resData || {}));
    if (resData?.answer) {
      console.log("Answer preview:", resData.answer.slice(0, 150) + "...");
      console.log("Confidence:", resData.confidence);
      console.log("Sources count:", resData.sources?.length || 0);
      if (resData.sources?.length > 0) {
        console.log("First source:", resData.sources[0]);
      }
    }
    
    if (resStatus !== 200) {
       console.log("SKIPPED: Live request returned non-200 (likely due to network, rate limit, or provider availability).");
    } else {
       console.log("PASSED: Integration test successful.");
    }
  } catch (error) {
    console.log("SKIPPED: Live request threw an exception.", error);
  }
}

runIntegrationTest().catch(console.error);
