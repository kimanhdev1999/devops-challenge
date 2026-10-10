// Minimal Vite-style build: content-hash every asset so it can be cached forever,
// and rewrite index.html to point at the hashed names.
import { createHash } from "node:crypto";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ASSETS = ["app.js", "styles.css"];

export async function build({ srcDir = path.join(root, "src"), outDir = path.join(root, "dist"), version = process.env.GITHUB_SHA || "dev" } = {}) {
  await rm(outDir, { recursive: true, force: true });
  await mkdir(path.join(outDir, "assets"), { recursive: true });

  let html = await readFile(path.join(srcDir, "index.html"), "utf8");
  const files = {};
  for (const asset of ASSETS) {
    const content = await readFile(path.join(srcDir, asset));
    const hash = createHash("sha256").update(content).digest("hex").slice(0, 10);
    const { name, ext } = path.parse(asset);
    const hashed = `assets/${name}.${hash}${ext}`;
    await writeFile(path.join(outDir, hashed), content);
    html = html.replace(`"${asset}"`, `"/${hashed}"`);
    files[asset] = hashed;
  }
  await writeFile(path.join(outDir, "index.html"), html);
  // Placeholder; the deploy job overwrites it with the target environment's values.
  await writeFile(path.join(outDir, "config.json"), JSON.stringify({ environment: "local", apiBaseUrl: "http://localhost:3000" }, null, 2));
  await writeFile(path.join(outDir, "manifest.json"), JSON.stringify({ version, files }, null, 2));
  return { outDir, files };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { outDir, files } = await build();
  console.log(`built ${Object.keys(files).length} assets into ${outDir}`);
}
