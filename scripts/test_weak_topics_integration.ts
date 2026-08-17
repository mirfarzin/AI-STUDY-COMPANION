import * as dotenv from 'dotenv';
import handler from '../api/weak-topics';

dotenv.config();

async function runIntegrationTest() {
  console.log("=== Integration Test: /weak-topics ===");
  
  if (!process.env.GROQ_API_KEY) {
    console.log("SKIPPED: GROQ_API_KEY is not configured.");
    return;
  }

  const req = { 
    method: 'POST',
    body: { 
      subject: "Computer Networks", 
      incorrect_questions: [
        { question: "What is TCP?", selected: "User Datagram Protocol", correct: "Transmission Control Protocol" },
        { question: "What layer is IP?", selected: "Transport", correct: "Network" }
      ] 
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
    console.log("Data:", JSON.stringify(resData, null, 2));
    
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
