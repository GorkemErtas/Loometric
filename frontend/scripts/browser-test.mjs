import { spawn, spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:net";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// Own both local servers; never attach to or stop a user's existing listener.
const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(frontend, "..");
const evidence = join(root, ".tmp", "frontend");
mkdirSync(evidence, { recursive: true });
const token = randomBytes(32).toString("base64url");
const redact = (value) => value.replaceAll(token, "[redacted session]");
const children = [];
const cleanEnv = { ...process.env };
delete cleanEnv.LOOMETRIC_API_TOKEN;
delete cleanEnv.LOOMETRIC_BROWSER_TOKEN;
delete cleanEnv.FORCE_COLOR;
const pause = (ms) => new Promise((done) => setTimeout(done, ms));
async function freePort(port) {
  const server = createServer();
  await new Promise((done, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", done);
  });
  const address = server.address();
  if (address === null || typeof address === "string") throw new Error("No local port available");
  await new Promise((done, reject) => server.close((error) => (error ? reject(error) : done())));
  return address.port;
}
function start(command, args, cwd, env) {
  const child = spawn(command, args, {
    cwd,
    env,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    detached: process.platform !== "win32",
  });
  child.captured = "";
  child.spawnFailure = false;
  child.on("error", () => {
    child.spawnFailure = true;
  });
  const capture = (chunk) => {
    child.captured = (child.captured + chunk.toString()).slice(-4 * 1024 * 1024);
  };
  child.stdout.on("data", capture);
  child.stderr.on("data", capture);
  children.push(child);
  return child;
}
async function ready(url, child) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (child.spawnFailure || child.exitCode !== null)
      throw new Error("A local server failed to start");
    try {
      if ((await fetch(url, { signal: AbortSignal.timeout(700) })).ok) return;
    } catch {
      /* Starting. */
    }
    await pause(200);
  }
  throw new Error("Local server readiness deadline exceeded");
}
function stop() {
  for (const child of [...children].reverse()) {
    if (child.pid && child.exitCode === null) {
      if (process.platform === "win32")
        spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
          windowsHide: true,
          stdio: "ignore",
        });
      else {
        try {
          process.kill(-child.pid, "SIGTERM");
        } catch {
          /* Already exited. */
        }
      }
    }
  }
}
function redactEvidence(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) redactEvidence(path);
    else if (/\.(json|md|txt|log|html)$/.test(entry.name)) {
      const value = readFileSync(path, "utf8");
      if (value.includes(token)) writeFileSync(path, redact(value));
    }
  }
}
for (const signal of ["SIGINT", "SIGTERM"])
  process.once(signal, () => {
    stop();
    process.exit(130);
  });
let code = 1;
let apiPort;
let frontendOwned = false;
const reuseFrontend = process.env.LOOMETRIC_TEST_REUSE_FRONTEND === "1";
try {
  if (reuseFrontend) {
    const packageReply = await fetch("http://127.0.0.1:5173/package.json", {
      signal: AbortSignal.timeout(1500),
    });
    const metadata = await packageReply.json();
    const path = join(frontend, "src/domain/scenario.ts").replaceAll("\\", "/");
    const moduleReply = await fetch(`http://127.0.0.1:5173/@fs/${path}`, {
      signal: AbortSignal.timeout(1500),
    });
    if (
      !packageReply.ok ||
      metadata.name !== "loometric-dashboard" ||
      !moduleReply.ok ||
      !(await moduleReply.text()).includes("baseline_instance_id")
    )
      throw new Error("Existing frontend does not match this workspace. No listener was changed.");
  } else await freePort(5173); // Strict CORS origin; never move ports or take over another process.
  apiPort = await freePort(0);
  const python = join(
    root,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  if (!existsSync(python))
    throw new Error("Install requirements/m05a.txt in the repository .venv first");
  const origin = `http://127.0.0.1:${apiPort}`;
  const api = start(python, ["-m", "loometric.api"], root, {
    ...cleanEnv,
    LOOMETRIC_API_TOKEN: token,
    LOOMETRIC_API_PORT: String(apiPort),
  });
  const vite = reuseFrontend
    ? null
    : start(
        process.execPath,
        [join(frontend, "node_modules/vite/bin/vite.js")],
        frontend,
        cleanEnv,
      );
  frontendOwned = vite !== null;
  await Promise.all([
    ready(`${origin}/api/v1/health`, api),
    ...(vite ? [ready("http://127.0.0.1:5173", vite)] : []),
  ]);
  const browser = start(
    process.execPath,
    [join(frontend, "node_modules/@playwright/test/cli.js"), "test"],
    frontend,
    { ...cleanEnv, LOOMETRIC_BROWSER_TOKEN: token, LOOMETRIC_BROWSER_ORIGIN: origin },
  );
  code = await new Promise((done) => {
    browser.once("exit", (exit) => done(exit ?? 1));
    browser.once("error", () => done(1));
  });
  // Playwright can include fill arguments in a failure; redact before any output.
  process.stdout.write(redact(browser.captured));
} catch (error) {
  process.stderr.write(
    `${redact(error instanceof Error ? error.message : "Browser harness failed")}\n`,
  );
  for (const child of children) process.stderr.write(redact(child.captured));
} finally {
  stop();
  redactEvidence(evidence);
  await pause(300);
  try {
    if (frontendOwned) await freePort(5173);
    if (apiPort) await freePort(apiPort);
    process.stdout.write(
      `${reuseFrontend ? "Owned API listener closed; existing frontend left untouched." : "Owned frontend/API listeners closed."} Session credentials discarded.\n`,
    );
  } catch {
    process.stderr.write("An owned local listener did not close.\n");
    code = 1;
  }
}
process.exitCode = code;
