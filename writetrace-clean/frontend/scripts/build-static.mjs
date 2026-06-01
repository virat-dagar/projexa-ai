import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDir = dirname(fileURLToPath(import.meta.url));
const frontendRoot = join(scriptsDir, "..");
const dist = join(frontendRoot, "dist");
const apiBaseUrl = process.env.WRITETRACE_API_BASE_URL ?? process.env.VITE_API_BASE_URL;
const runtimeConfig = apiBaseUrl === undefined ? {} : { apiBaseUrl };

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

for (const entry of ["index.html", "editor.css", "editor.js", "student", "teacher"]) {
  await cp(join(frontendRoot, entry), join(dist, entry), { recursive: true });
}

await writeFile(
  join(dist, "runtime-config.js"),
  `window.WRITETRACE_CONFIG = ${JSON.stringify(runtimeConfig, null, 2)};\n`,
  "utf-8",
);
