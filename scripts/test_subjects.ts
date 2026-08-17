import handler from '../api/subjects';

async function runTest() {
  const req = { method: 'GET' } as any;
  let responseData: any;
  let responseStatus: number = 200;
  
  const res = {
    status: (code: number) => {
      responseStatus = code;
      return res;
    },
    json: (data: any) => {
      responseData = data;
    }
  } as any;
  
  await handler(req, res);
  
  console.log("Status:", responseStatus);
  console.log("JSON Output:");
  console.log(JSON.stringify(responseData, null, 2));
}

runTest().catch(console.error);
