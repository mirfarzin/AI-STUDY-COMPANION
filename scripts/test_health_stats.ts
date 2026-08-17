import healthHandler from '../api/health';
import statsHandler from '../api/stats';

async function runTests() {
  console.log("=== Testing /health ===");
  const reqHealth = { method: 'GET' } as any;
  let resHealthStatus = 200;
  let resHealthData: any;
  
  const resHealth = {
    status: (code: number) => { resHealthStatus = code; return resHealth; },
    json: (data: any) => { resHealthData = data; }
  } as any;
  
  await healthHandler(reqHealth, resHealth);
  console.log("Health Status:", resHealthStatus);
  console.log("Health Data:", JSON.stringify(resHealthData, null, 2));

  console.log("\n=== Testing /stats ===");
  const reqStats = { method: 'GET' } as any;
  let resStatsStatus = 200;
  let resStatsData: any;
  
  const resStats = {
    status: (code: number) => { resStatsStatus = code; return resStats; },
    json: (data: any) => { resStatsData = data; }
  } as any;
  
  await statsHandler(reqStats, resStats);
  console.log("Stats Status:", resStatsStatus);
  console.log("Stats Data:", JSON.stringify(resStatsData, null, 2));
}

runTests().catch(console.error);
