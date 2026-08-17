import handler from '../api/pyq';

async function runUnitTests() {
  console.log("=== Unit Test: /pyq (Method Not Allowed) ===");
  const reqGet = { method: 'GET' } as any;
  let resGetStatus = 200;
  let resGetData: any;
  const resGet = {
    status: (code: number) => { resGetStatus = code; return resGet; },
    json: (data: any) => { resGetData = data; }
  } as any;
  await handler(reqGet, resGet);
  console.log("Status:", resGetStatus);
  console.log("Data:", JSON.stringify(resGetData, null, 2));

  console.log("\n=== Unit Test: /pyq (Missing Body/Question) ===");
  const reqEmpty = { 
    method: 'POST',
    body: {}
  } as any;
  let resEmptyStatus = 200;
  let resEmptyData: any;
  const resEmpty = {
    status: (code: number) => { resEmptyStatus = code; return resEmpty; },
    json: (data: any) => { resEmptyData = data; }
  } as any;
  await handler(reqEmpty, resEmpty);
  console.log("Status:", resEmptyStatus);
  console.log("Data:", JSON.stringify(resEmptyData, null, 2));

  console.log("\n=== Unit Test: /pyq (Empty/Blank Question) ===");
  const reqBlank = { 
    method: 'POST',
    body: { question: "   " }
  } as any;
  let resBlankStatus = 200;
  let resBlankData: any;
  const resBlank = {
    status: (code: number) => { resBlankStatus = code; return resBlank; },
    json: (data: any) => { resBlankData = data; }
  } as any;
  await handler(reqBlank, resBlank);
  console.log("Status:", resBlankStatus);
  console.log("Data:", JSON.stringify(resBlankData, null, 2));

  console.log("\n=== Unit Test: /pyq (Valid Question, Missing Credentials -> 404 No Context) ===");
  const reqValid = { 
    method: 'POST',
    body: { 
      question: "Explain TCP three-way handshake.",
      subject: "Computer Networks" 
    }
  } as any;
  let resValidStatus = 200;
  let resValidData: any;
  const resValid = {
    status: (code: number) => { resValidStatus = code; return resValid; },
    json: (data: any) => { resValidData = data; }
  } as any;
  // Since we don't load dotenv here, HF_TOKEN or QDRANT_URL will be missing.
  // Qdrant or Embedding will fail, resulting in 404 because queryChunks returns empty [] on error.
  await handler(reqValid, resValid);
  console.log("Status:", resValidStatus);
  console.log("Data:", JSON.stringify(resValidData, null, 2));

  console.log("\n✅ All unit test scenarios executed successfully.");
}

runUnitTests().catch(console.error);
