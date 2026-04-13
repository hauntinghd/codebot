import { execSync } from "node:child_process";

const out = execSync(
  `rg -n "codebot5/layers|codebot5/prompts|codebot5/utils|codebot5/types" src --glob '!src/codebot5/**' || true`,
  { encoding: "utf8" }
);

if (out.trim().length) {
  console.error("❌ Forbidden: direct imports into codebot5 internals.");
  console.error("✅ Fix: import only from 'src/codebot5' (the barrel index.ts).");
  console.error(out);
  process.exit(1);
}

console.log("✅ CodeBot5 import boundary OK.");
