const { test, before, after } = require("node:test");
const assert = require("node:assert/strict");
const { createApp } = require("../src/app");

let server;
let base;

before(async () => {
  server = createApp({ version: "abc123" }).listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(() => server.close());

test("GET /healthz reports ok and the deployed version", async () => {
  const res = await fetch(`${base}/healthz`);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { status: "ok", version: "abc123" });
});

test("GET /api/hello greets the caller", async () => {
  const res = await fetch(`${base}/api/hello?name=castle`);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { message: "hello castle" });
});

test("unknown routes return 404 and hide the framework", async () => {
  const res = await fetch(`${base}/nope`);
  assert.equal(res.status, 404);
  assert.equal(res.headers.get("x-powered-by"), null);
});
