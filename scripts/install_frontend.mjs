// GreatOCR frontend dependency installer
// Runs via node.exe -- no .cmd batch wrappers involved
import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, "..");
const frontendDir = resolve(rootDir, "frontend");
const registry = "https://registry.npmmirror.com";

function run(cmd, opts = {}) {
  execSync(cmd, {
    stdio: "inherit",
    shell: "cmd.exe",
    cwd: rootDir,
    timeout: 10 * 60 * 1000,
    ...opts,
  });
}

// Step 1: Check if already installed
process.chdir(frontendDir);
if (existsSync("node_modules")) {
  console.log("    Frontend dependencies already installed. Skipping.");
  process.exit(0);
}

// Step 2: Find node dir for npm-cli.js (avoids npm.cmd wrapper)
const nodeDir = resolve(process.execPath, "..");
const npmCli = resolve(nodeDir, "node_modules", "npm", "bin", "npm-cli.js");

// Step 3: Install pnpm via node-run npm (no .cmd wrapper)
console.log("    Installing pnpm...");
try {
  run(`"${process.execPath}" "${npmCli}" install -g pnpm --registry ${registry}`);
} catch {
  console.error("    [ERROR] Failed to install pnpm.");
  console.error("    Try manually: npm install -g pnpm");
  process.exit(1);
}

// Step 4: Install frontend dependencies via pnpm
console.log("    Installing frontend dependencies...");
try {
  run(`pnpm install --registry ${registry}`, { cwd: frontendDir });
} catch {
  console.error("    [ERROR] Frontend dependency installation failed.");
  console.error("    Possible causes: network issue.");
  process.exit(1);
}

console.log("    Frontend dependencies installed.");
