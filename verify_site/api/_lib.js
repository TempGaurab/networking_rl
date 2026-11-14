import { neon } from "@neondatabase/serverless";
import { timingSafeEqual } from "node:crypto";

export const REVIEWERS = { gaurab: "Gaurab Baral", nityashree: "Nityashree Vangala" };
export const CHOICES = ["yes", "no", "unsure"];
export const N_PAPERS = 50;

const url = process.env.DATABASE_URL || process.env.POSTGRES_URL;
export const sql = url ? neon(url) : null;

let ready = null;
export function ensureSchema() {
  ready ??= sql`CREATE TABLE IF NOT EXISTS decisions (
      paper_id   text NOT NULL,
      reviewer   text NOT NULL,
      decision   text NOT NULL CHECK (decision IN ('yes','no','unsure')),
      note       text NOT NULL DEFAULT '',
      updated_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (paper_id, reviewer))`;
  return ready;
}

function same(a, b) {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && timingSafeEqual(x, y);
}

/** Returns the reviewer key if the request carries that reviewer's access code, else sends 401. */
export function auth(req, res) {
  const who = String(req.headers["x-reviewer"] || "");
  const code = String(req.headers["x-access-code"] || "");
  const expected = process.env[`CODE_${who.toUpperCase()}`];
  if (!REVIEWERS[who] || !expected || !same(code, expected)) {
    res.status(401).json({ error: "Wrong reviewer or access code." });
    return null;
  }
  if (!sql) { res.status(500).json({ error: "DATABASE_URL is not set." }); return null; }
  return who;
}

/** Cohen's kappa on yes vs not-yes, over papers both reviewers decided. */
export function kappa(pairs) {
  const n = pairs.length;
  if (!n) return null;
  const agree = pairs.filter(([a, b]) => a === b).length / n;
  const p = (k, i) => pairs.filter(x => x[i] === k).length / n;
  const pe = CHOICES.reduce((s, k) => s + p(k, 0) * p(k, 1), 0);
  return { n, agreement: agree, kappa: pe === 1 ? 1 : (agree - pe) / (1 - pe) };
}
