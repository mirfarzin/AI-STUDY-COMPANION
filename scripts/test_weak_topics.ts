import handler from '../api/weak-topics';

async function runUnitTests() {
  console.log("=== Unit Test: /weak-topics (Empty Request) ===");
  const reqEmpty = { 
    method: 'POST',
    body: { subject: "Computer Networks", incorrect_questions: [] }
  } as any;
  
  let resStatus = 200;
  let resData: any;
  const resEmpty = {
    status: (code: number) => { resStatus = code; return resEmpty; },
    json: (data: any) => { resData = data; }
  } as any;
  
  await handler(reqEmpty, resEmpty);
  console.log("Status:", resStatus);
  console.log("Data:", JSON.stringify(resData, null, 2));

  console.log("\n=== Unit Test: /weak-topics (Missing Groq Key) ===");
  const reqValid = { 
    method: 'POST',
    body: { 
      subject: "Computer Networks", 
      incorrect_questions: [
        { question: "What is TCP?", selected: "User Datagram Protocol", correct: "Transmission Control Protocol" }
      ] 
    }
  } as any;
  
  let resValidStatus = 200;
  let resValidData: any;
  const resValid = {
    status: (code: number) => { resValidStatus = code; return resValid; },
    json: (data: any) => { resValidData = data; }
  } as any;
  
  // Since we don't load dotenv here and don't set GROQ_API_KEY, Groq will throw an error.
  // The API should catch it and return 502.
  await handler(reqValid, resValid);
  console.log("Status:", resValidStatus);
  console.log("Data:", JSON.stringify(resValidData, null, 2));
}

runUnitTests().catch(console.error);
