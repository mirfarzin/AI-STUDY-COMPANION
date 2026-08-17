import handler from '../api/quiz';

async function runUnitTests() {
  console.log("=== Unit Test: /quiz (Missing Subject) ===");
  const reqEmpty = { 
    method: 'GET',
    query: {}
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

  console.log("\n=== Unit Test: /quiz (Missing Tokens/Keys) ===");
  const reqValid = { 
    method: 'GET',
    query: { subject: "Computer Networks" }
  } as any;
  
  let resValidStatus = 200;
  let resValidData: any;
  const resValid = {
    status: (code: number) => { resValidStatus = code; return resValid; },
    json: (data: any) => { resValidData = data; }
  } as any;
  
  // Since we don't load dotenv here, HF_TOKEN or QDRANT_URL won't be set.
  // Qdrant or Embedding will fail, resulting in 404 because queryChunks returns empty [] on error.
  await handler(reqValid, resValid);
  console.log("Status:", resValidStatus);
  console.log("Data:", JSON.stringify(resValidData, null, 2));
}

runUnitTests().catch(console.error);
