import { sql, ensureSchema, auth, REVIEWERS, CHOICES, N_PAPERS, kappa } from "./_lib.js";

// GET: your own decisions, how far each reviewer has got, and (only once both have
// decided all papers) both sets side by side with agreement statistics.
// POST {paper_id, decision, note}: save or change your decision on one paper.
export default async function handler(req, res) {
  const who = auth(req, res);
  if (!who) return;
  await ensureSchema();

  if (req.method === "POST") {
    const { paper_id, decision, note = "" } = req.body || {};
    if (!/^[A-Z]{1,3}\d{1,4}$/.test(String(paper_id)) || !CHOICES.includes(decision))
      return res.status(400).json({ error: "Bad paper_id or decision." });
    await sql`INSERT INTO decisions (paper_id, reviewer, decision, note)
              VALUES (${paper_id}, ${who}, ${decision}, ${String(note).slice(0, 2000)})
              ON CONFLICT (paper_id, reviewer)
              DO UPDATE SET decision = EXCLUDED.decision, note = EXCLUDED.note, updated_at = now()`;
    return res.status(200).json({ ok: true });
  }
  if (req.method !== "GET") return res.status(405).end();

  const rows = await sql`SELECT paper_id, reviewer, decision, note, updated_at FROM decisions`;
  const progress = Object.fromEntries(Object.keys(REVIEWERS).map(r => [r, rows.filter(x => x.reviewer === r).length]));
  const mine = Object.fromEntries(rows.filter(r => r.reviewer === who).map(r => [r.paper_id, r]));
  const revealed = Object.values(progress).every(n => n >= N_PAPERS);
  let results = null;
  if (revealed) {
    const by = {};
    for (const r of rows) (by[r.paper_id] ??= {})[r.reviewer] = r;
    const [a, b] = Object.keys(REVIEWERS);
    const both = Object.entries(by).filter(([, v]) => v[a] && v[b]);
    results = {
      stats: kappa(both.map(([, v]) => [v[a].decision, v[b].decision])),
      papers: Object.fromEntries(both.map(([id, v]) => [id, { [a]: v[a], [b]: v[b] }])),
    };
  }
  res.status(200).json({ reviewer: who, progress, total: N_PAPERS, mine, revealed, results });
}
