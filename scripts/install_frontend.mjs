import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, "..");
const frontendDir = resolve(rootDir, "frontend");
const nodeModulesDir = resolve(frontendDir, "node_modules");
const nodeExe = process.execPath;
const npmCli = resolve(dirname(nodeExe), "node_modules", "npm", "bin", "npm-cli.js");

const registries = [
  "https://registry.npmmirror.com",
  "https://registry.npmjs.org",
];

function runNodeCli(cliPath, args, cwd) {
  execFileSync(nodeExe, [cliPath, ...args], {
    cwd,
    stdio: "inherit",
    timeout: 10 * 60 * 1000,
  });
}

function readNodeCli(cliPath, args, cwd) {
  return execFileSync(nodeExe, [cliPath, ...args], {
    cwd,
    stdio: ["ignore", "pipe", "pipe"],
    encoding: "utf-8",
    timeout: 60 * 1000,
  }).trim();
}

function findPnpmCli() {
  try {
    const globalRoot = readNodeCli(npmCli, ["root", "-g"], rootDir);
    const pnpmCli = resolve(globalRoot, "pnpm", "bin", "pnpm.cjs");
    return existsSync(pnpmCli) ? pnpmCli : null;
  } catch {
    return null;
  }
}

function ensurePnpm() {
  const existing = findPnpmCli();
  if (existing) {
    console.log("    pnpm already installed. Skipping.");
    return existing;
  }

  console.log("    Installing pnpm...");
  for (const registry of registries) {
    try {
      runNodeCli(npmCli, ["install", "-g", "pnpm", "--registry", registry], rootDir);
      const installed = findPnpmCli();
      if (installed) {
        return installed;
      }
    } catch {
      console.log(`    Registry ${registry} failed, trying next...`);
    }
  }

  throw new Error("Could not install pnpm.");
}

if (existsSync(nodeModulesDir)) {
  console.log("    Frontend dependencies already installed. Skipping.");
  process.exit(0);
}

const pnpmCli = ensurePnpm();

console.log("    Installing frontend dependencies...");
let installOk = false;
for (const registry of registries) {
  try {
    runNodeCli(
      pnpmCli,
      ["install", "--dir", frontendDir, "--registry", registry],
      rootDir,
    );
    installOk = true;
    break;
  } catch {
    console.log(`    Registry ${registry} failed, trying next...`);
  }
}

if (!installOk) {
  console.error("    [ERROR] Frontend dependency installation failed.");
  console.error("    Check your internet connection and run install.bat again.");
  process.exit(1);
}

console.log("    Frontend dependencies installed.");
