import handler from '../api/predict';

async function runUnitTests() {
  console.log("=== Unit Test: /predict (Missing Subject) ===");
  const reqEmpty = { 
    method: 'POST',
    body: {}
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

  console.log("\n=== Unit Test: /predict (Missing Tokens/Keys) ===");
  const reqValid = { 
    method: 'POST',
    body: { subject: "Computer Networks" }
  } as any;
  
  let resValidStatus = 200;
  let resValidData: any;
  const resValid = {
    status: (code: number) => { resValidStatus = code; return resValid; },
    json: (data: any) => { resValidData = data; }
  } as any;
  
  // Qdrant stats check will fail, returning empty array, resulting in 404
  await handler(reqValid, resValid);
  console.log("Status:", resValidStatus);
  console.log("Data:", JSON.stringify(resValidData, null, 2));
}

runUnitTests().catch(console.error);
