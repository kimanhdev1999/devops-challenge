import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, access } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { build } from "../scripts/build.mjs";

test("index.html references content-hashed assets that exist", async () => {
  const outDir = await mkdtemp(path.join(tmpdir(), "fe-"));
  const { files } = await build({ outDir, version: "abc123" });
  const html = await readFile(path.join(outDir, "index.html"), "utf8");
  for (const hashed of Object.values(files)) {
    assert.match(hashed, /^assets\/[a-z]+\.[0-9a-f]{10}\.(js|css)$/);
    assert.ok(html.includes(`"/${hashed}"`), `index.html should reference ${hashed}`);
    await access(path.join(outDir, hashed));
  }
  const manifest = JSON.parse(await readFile(path.join(outDir, "manifest.json"), "utf8"));
  assert.equal(manifest.version, "abc123");
});

test("builds are reproducible: same source, same hashes", async () => {
  const a = await build({ outDir: await mkdtemp(path.join(tmpdir(), "fe-")) });
  const b = await build({ outDir: await mkdtemp(path.join(tmpdir(), "fe-")) });
  assert.deepEqual(a.files, b.files);
});
