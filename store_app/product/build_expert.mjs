#!/usr/bin/env node
// Generate the OS product Expert from the bridge's already-tested installer.

import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const bridgeRoot = resolve(
  process.env.EXTELLA_BRIDGE_SOURCE ||
    resolve(HERE, "../../../extella-codex-bridge"),
);
const sourcePath = resolve(
  bridgeRoot,
  "plugins/extella-codex-bridge/integrations/extella-desktop/codex-installer.js",
);
const outputPath = resolve(HERE, "expert_extella_codex_product_setup.py");

const source = await readFile(sourcePath, "utf8");
const marker = "  var EXPERT_CODE = [";
const assignment = source.indexOf(marker);
const arrayStart = source.indexOf("[", assignment);
const joinStart = source.indexOf("].join('\\n');", arrayStart);
if (assignment < 0 || arrayStart < 0 || joinStart < 0) {
  throw new Error("bridge installer Expert is not extractable");
}
const expression = source.slice(arrayStart, joinStart + 1);
const extracted = Function(`return ${expression}`)();
if (!Array.isArray(extracted)) throw new Error("bridge installer Expert is not an array");
const lines = extracted.join("\n").split("\n");
lines[0] = 'def extella_codex_product_setup(action="preflight") -> str:';
lines.splice(2, 0, "    step = action");
const generated = lines.join("\n").trimEnd() + "\n";

if (process.argv.includes("--check")) {
  const current = await readFile(outputPath, "utf8");
  if (current !== generated) throw new Error("generated product Expert is stale");
  process.stdout.write("OS product Expert matches bridge installer\n");
} else {
  await writeFile(outputPath, generated);
  process.stdout.write(`Generated ${outputPath}\n`);
}
