import handler from '../api/chat';

async function runUnitTests() {
  console.log("=== Unit Test: /chat (Method Not Allowed) ===");
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

  console.log("\n=== Unit Test: /chat (Empty Body) ===");
  const reqEmpty = { method: 'POST', body: {} } as any;
  let resEmptyStatus = 200;
  let resEmptyData: any;
  const resEmpty = {
    status: (code: number) => { resEmptyStatus = code; return resEmpty; },
    json: (data: any) => { resEmptyData = data; }
  } as any;
  await handler(reqEmpty, resEmpty);
  console.log("Status:", resEmptyStatus);
  console.log("Data:", JSON.stringify(resEmptyData, null, 2));

  console.log("\n=== Unit Test: /chat (Blank Query/Message) ===");
  const reqBlank = { method: 'POST', body: { query: "   ", message: "" } } as any;
  let resBlankStatus = 200;
  let resBlankData: any;
  const resBlank = {
    status: (code: number) => { resBlankStatus = code; return resBlank; },
    json: (data: any) => { resBlankData = data; }
  } as any;
  await handler(reqBlank, resBlank);
  console.log("Status:", resBlankStatus);
  console.log("Data:", JSON.stringify(resBlankData, null, 2));

  console.log("\n=== Unit Test: /chat (Valid Query with Subject, Missing Credentials -> 404 No Context) ===");
  const reqValid = {
    method: 'POST',
    body: {
      query: "What is an Operating System?",
      subject: "Operating Systems"
    }
  } as any;
  let resValidStatus = 200;
  let resValidData: any;
  const resValid = {
    status: (code: number) => { resValidStatus = code; return resValid; },
    json: (data: any) => { resValidData = data; }
  } as any;
  // Without credentials, semanticSearch will log error and return [], leading to 404 with subject message
  await handler(reqValid, resValid);
  console.log("Status:", resValidStatus);
  console.log("Data:", JSON.stringify(resValidData, null, 2));

  console.log("\n=== Unit Test: /chat (Valid Message without Subject, Missing Credentials -> 404 No Context) ===");
  const reqValidNoSubj = {
    method: 'POST',
    body: {
      message: "Explain Von Neumann Architecture"
    }
  } as any;
  let resValidNoSubjStatus = 200;
  let resValidNoSubjData: any;
  const resValidNoSubj = {
    status: (code: number) => { resValidNoSubjStatus = code; return resValidNoSubj; },
    json: (data: any) => { resValidNoSubjData = data; }
  } as any;
  await handler(reqValidNoSubj, resValidNoSubj);
  console.log("Status:", resValidNoSubjStatus);
  console.log("Data:", JSON.stringify(resValidNoSubjData, null, 2));

  console.log("\n✅ All unit test scenarios executed successfully.");
}

runUnitTests().catch(console.error);
