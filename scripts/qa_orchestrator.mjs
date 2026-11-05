#!/usr/bin/env node
/**
 * SpaOS Root QA & Verification Orchestrator
 * Chuẩn hóa khẩu lệnh Seed Data + Playwright E2E trên môi trường QA cô lập,
 * tuyệt đối không ghi đè hay làm bẩn database ứng dụng của người dùng.
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), "..");

const ISOLATED_SEED_PYTHON = `
import asyncio, os, subprocess, sys, uuid
from sqlalchemy.engine import make_url
from app.core.config import settings
from scripts.operator_qa_server import database

name = "spaos_e2e_" + uuid.uuid4().hex
print(f"[Seed QA] Khởi tạo DB tạm cô lập: {name}", flush=True)
asyncio.run(database(name, True))
try:
    env = dict(os.environ)
    env["DATABASE_URL"] = make_url(settings.DATABASE_URL).set(database=name).render_as_string(hide_password=False)
    env["MIGRATION_DATABASE_URL"] = make_url(settings.MIGRATION_DATABASE_URL).set(database=name).render_as_string(hide_password=False)
    env.update(
        ENVIRONMENT="test",
        OPERATOR_PHONE="0998888777",
        OPERATOR_NAME="QA Operator",
        OPERATOR_PASSWORD="OperatorOnlyForQa@2026",
        VAPID_PUBLIC_KEY="",
        VAPID_PRIVATE_KEY="",
    )
    for step_label, cmd in (
        ("Alembic Migrate (head)", [sys.executable, "-m", "alembic", "upgrade", "head"]),
        ("Operator Seed (app.seed)", [sys.executable, "-m", "app.seed"]),
        ("Demo Spa Seed (app.seed_demo)", [sys.executable, "-m", "app.seed_demo"]),
    ):
        print(f"[Seed QA] -> {step_label}", flush=True)
        subprocess.run(cmd, env=env, check=True)
finally:
    asyncio.run(database(name, False))
    print(f"[Seed QA] Đã dọn DB tạm {name}; giữ nguyên DB ứng dụng.", flush=True)
`;

function resolveCompose() {
  const v2 = spawnSync("docker", ["compose", "version"], { cwd: ROOT, stdio: "ignore" });
  if (v2.status === 0) {
    return { bin: "docker", prefix: ["compose"] };
  }
  const v1 = spawnSync("docker-compose", ["version"], { cwd: ROOT, stdio: "ignore" });
  if (v1.status === 0) {
    return { bin: "docker-compose", prefix: [] };
  }
  console.error("[SpaOS QA] Không tìm thấy `docker compose` hoặc `docker-compose` trong PATH.");
  process.exit(1);
}

function resolveAutomationPython() {
  const candidates = [
    path.join(ROOT, "automation_test", ".venv", "Scripts", "python.exe"),
    path.join(ROOT, "automation_test", ".venv", "bin", "python"),
    path.join(ROOT, ".venv", "Scripts", "python.exe"),
    path.join(ROOT, ".venv", "bin", "python"),
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  const py = spawnSync("python", ["--version"], { cwd: ROOT, stdio: "ignore" });
  if (py.status === 0) {
    return "python";
  }
  return "python3";
}

function isDockerStackReady(compose) {
  const dbReady = spawnSync(
    compose.bin,
    [
      ...compose.prefix,
      "exec",
      "-T",
      "db",
      "sh",
      "-c",
      'pg_isready -U "${POSTGRES_USER:-spaos}" -d "${POSTGRES_DB:-spaos}"',
    ],
    { cwd: ROOT, stdio: "ignore" }
  );
  if (dbReady.status !== 0) {
    return false;
  }
  const backendReady = spawnSync(
    compose.bin,
    [...compose.prefix, "exec", "-T", "backend", "python", "-c", "import app"],
    { cwd: ROOT, stdio: "ignore" }
  );
  return backendReady.status === 0;
}

function ensureDockerReady(compose) {
  if (isDockerStackReady(compose)) {
    console.log("[Docker] Services `db` & `backend` đã sẵn sàng.");
    return;
  }
  console.log("[Docker] Đang khởi động `db` & `backend` qua Docker Compose...");
  const up = spawnSync(compose.bin, [...compose.prefix, "up", "-d", "db", "backend"], {
    cwd: ROOT,
    stdio: "inherit",
  });
  if (up.status !== 0) {
    process.exit(up.status ?? 1);
  }
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (isDockerStackReady(compose)) {
      console.log("[Docker] Services `db` & `backend` đã sẵn sàng.");
      return;
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 500);
  }
  console.error("[Docker] Quá thời gian chờ `db` & `backend` sẵn sàng (60s).");
  process.exit(1);
}

function runResetAndSeed(compose) {
  ensureDockerReady(compose);
  const res = spawnSync(
    compose.bin,
    [...compose.prefix, "exec", "-T", "backend", "python", "-"],
    {
      cwd: ROOT,
      input: ISOLATED_SEED_PYTHON,
      stdio: ["pipe", "inherit", "inherit"],
      encoding: "utf-8",
    }
  );
  if (res.status !== 0) {
    process.exit(res.status ?? 1);
  }
}

function runSeedDev(compose) {
  ensureDockerReady(compose);
  for (const mod of ["app.seed", "app.seed_demo"]) {
    const res = spawnSync(
      compose.bin,
      [...compose.prefix, "exec", "-T", "backend", "python", "-m", mod],
      { cwd: ROOT, stdio: "inherit" }
    );
    if (res.status !== 0) {
      process.exit(res.status ?? 1);
    }
  }
}

function formatRunUiQaArgs(rawArgs) {
  const runnerFlags = [];
  let i = 0;
  while (i < rawArgs.length) {
    const arg = rawArgs[i];
    if ((arg === "--mode" || arg === "--port") && i + 1 < rawArgs.length) {
      runnerFlags.push(arg, rawArgs[i + 1]);
      i += 2;
      continue;
    }
    if (arg.startsWith("--mode=") || arg.startsWith("--port=")) {
      runnerFlags.push(arg);
      i += 1;
      continue;
    }
    if (arg === "-h" || arg === "--help") {
      return [arg];
    }
    break;
  }
  const rest = rawArgs.slice(i);
  if (rest.length === 0) {
    return runnerFlags;
  }
  if (rest[0] === "--") {
    return [...runnerFlags, ...rest];
  }
  return [...runnerFlags, "--", ...rest];
}

function runPlaywrightE2E(compose, rawArgs) {
  ensureDockerReady(compose);
  const pyBin = resolveAutomationPython();
  const qaArgs = formatRunUiQaArgs(rawArgs);
  console.log(`[E2E] Python: ${pyBin}`);
  console.log(`[E2E] Chạy automation_test.run_ui_qa (tự tạo & seed DB E2E cô lập + Next.js QA server)...`);
  const res = spawnSync(pyBin, ["-B", "-m", "automation_test.run_ui_qa", ...qaArgs], {
    cwd: ROOT,
    stdio: "inherit",
  });
  if (res.status !== 0) {
    process.exit(res.status ?? 1);
  }
}

function runBackendIsolated(compose, rawArgs) {
  ensureDockerReady(compose);
  const res = spawnSync(
    compose.bin,
    [...compose.prefix, "exec", "-T", "backend", "python", "-m", "scripts.test_isolated", ...rawArgs],
    { cwd: ROOT, stdio: "inherit" }
  );
  if (res.status !== 0) {
    process.exit(res.status ?? 1);
  }
}

function runHarnessTests() {
  const pyBin = resolveAutomationPython();
  const res = spawnSync(
    pyBin,
    ["-B", "-m", "unittest", "discover", "-s", "automation_test/harness_tests", "-q"],
    { cwd: ROOT, stdio: "inherit" }
  );
  if (res.status !== 0) {
    process.exit(res.status ?? 1);
  }
}

const [, , action, ...extraArgs] = process.argv;

switch (action) {
  case "db-up": {
    ensureDockerReady(resolveCompose());
    break;
  }
  case "seed-dev": {
    runSeedDev(resolveCompose());
    break;
  }
  case "reset-and-seed": {
    runResetAndSeed(resolveCompose());
    break;
  }
  case "test-backend": {
    runBackendIsolated(resolveCompose(), extraArgs);
    break;
  }
  case "test-harness": {
    runHarnessTests();
    break;
  }
  case "e2e": {
    runPlaywrightE2E(resolveCompose(), extraArgs);
    break;
  }
  case "verify-all": {
    const compose = resolveCompose();
    console.log("=== [1/2] KIỂM ĐỊNH MIGRATION & SEED DATA (DB QA CÔ LẬP) ===");
    runResetAndSeed(compose);
    console.log("=== [2/2] CHẠY PLAYWRIGHT E2E TEST SUITE (MULTI-ROLE QA) ===");
    runPlaywrightE2E(compose, extraArgs);
    console.log("=== HOÀN TẤT VERIFY:ALL (SEED DATA + PLAYWRIGHT E2E PASS) ===");
    break;
  }
  default: {
    console.error(
      "Usage: node scripts/qa_orchestrator.mjs <db-up|seed-dev|reset-and-seed|test-backend|test-harness|e2e|verify-all> [args...]"
    );
    process.exit(1);
  }
}
