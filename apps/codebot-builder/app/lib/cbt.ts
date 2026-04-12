import fs from "fs";
import path from "path";

type Store = {
  users: Record<string, { balance: number; updatedAt: string }>;
  ledger: Array<{
    id: string;
    userId: string;
    delta: number;
    reason: string;
    meta?: any;
    createdAt: string;
  }>;
};

const STORE_PATH = (process.env.CODEBOT_TOKENS_PATH || "").trim()
  ? process.env.CODEBOT_TOKENS_PATH!.trim()
  : path.join(process.cwd(), "codebot-tokens.json");

function nowIso() {
  return new Date().toISOString();
}

function readStore(): Store {
  try {
    const raw = fs.readFileSync(STORE_PATH, "utf8");
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") throw new Error("bad_store");
    if (!parsed.users) parsed.users = {};
    if (!parsed.ledger) parsed.ledger = [];
    return parsed as Store;
  } catch {
    return { users: {}, ledger: [] };
  }
}

function writeStoreAtomic(store: Store) {
  const dir = path.dirname(STORE_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const tmp = `${STORE_PATH}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(store, null, 2), "utf8");
  fs.renameSync(tmp, STORE_PATH);
}

function randId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function getUserIdFromRequest(req: Request): string {
  const h = req.headers.get("x-codebot-user");
  const user = (h || "anon").trim();
  return user || "anon";
}

export function getBalance(userId: string): number {
  const s = readStore();
  return s.users[userId]?.balance ?? 0;
}

export function canAfford(userId: string, cost: number): boolean {
  if (cost <= 0) return true;
  return getBalance(userId) >= cost;
}

export function addTokens(userId: string, amount: number, reason: string, meta?: Record<string, any>): void {
  if (!Number.isInteger(amount)) throw new Error("amount must be integer");
  const s = readStore();

  if (!s.users[userId]) s.users[userId] = { balance: 0, updatedAt: nowIso() };

  s.users[userId].balance += amount;
  s.users[userId].updatedAt = nowIso();

  s.ledger.push({ id: randId(), userId, delta: amount, reason, meta, createdAt: nowIso() });

  if (s.ledger.length > 5000) s.ledger.splice(0, s.ledger.length - 5000);
  writeStoreAtomic(s);
}

export function spendTokens(userId: string, cost: number, reason: string, meta?: Record<string, any>): void {
  if (!Number.isInteger(cost)) throw new Error("cost must be integer");
  if (cost < 0) throw new Error("cost must be >= 0");

  const s = readStore();
  if (!s.users[userId]) s.users[userId] = { balance: 0, updatedAt: nowIso() };

  const bal = s.users[userId].balance;
  if (bal < cost) throw new Error("INSUFFICIENT_CBT");

  s.users[userId].balance = bal - cost;
  s.users[userId].updatedAt = nowIso();

  s.ledger.push({ id: randId(), userId, delta: -cost, reason, meta, createdAt: nowIso() });

  if (s.ledger.length > 5000) s.ledger.splice(0, s.ledger.length - 5000);
  writeStoreAtomic(s);
}
