import { sql, ensureSchema, auth } from "./_lib.js";

// CSV of every decision, available to either reviewer once both have finished (blinding).
export default async function handler(req, res) {
  if (!auth(req, res)) return;
  await ensureSchema();
  const rows = await sql`SELECT paper_id, reviewer, decision, note, updated_at FROM decisions ORDER BY paper_id, reviewer`;
  const counts = {};
  for (const r of rows) counts[r.reviewer] = (counts[r.reviewer] || 0) + 1;
  if (Object.keys(counts).length < 2 || Object.values(counts).some(n => n < 50))
    return res.status(403).json({ error: "Export opens once both reviewers have decided all 50 papers." });
  const esc = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = ["paper_id,reviewer,decision,note,updated_at",
    ...rows.map(r => [r.paper_id, r.reviewer, r.decision, r.note, new Date(r.updated_at).toISOString()].map(esc).join(","))].join("\n");
  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Content-Disposition", 'attachment; filename="rl_verification.csv"');
  res.status(200).send(csv);
}
