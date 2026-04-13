import { execSync } from "node:child_process";

function run(cmd) {
  console.log(`\n$ ${cmd}`);
  execSync(cmd, { stdio: "inherit" });
}

try {
  run("node scripts/check-codebot5-imports.mjs");

  // If build exists, enforce it.
  // If your backend-ts does NOT have a build script yet, this will fail (good).
  run("pnpm -s run build");

  console.log("\n✅ SMOKE PASS");
} catch {
  console.error("\n❌ SMOKE FAIL");
  process.exit(1);
}
