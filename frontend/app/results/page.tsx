"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, ApiError, type ScorecardRow } from "@/lib/api";

// Column order and plain-language labels for the scorecard (eval/scorecard.py).
const COLUMNS: { key: string; label: string; hint: string; better: "lower" | "higher" }[] = [
  { key: "topic_attack_feb4rag", label: "Topic leak", hint: "observer names the query's topic from contacted sources (FeB4RAG, chance 0.077)", better: "lower" },
  { key: "source_attack_feb4rag", label: "Source leak", hint: "observer names the genuine source", better: "lower" },
  { key: "topic_attack_healthcare", label: "Topic leak (same-domain)", hint: "8-client healthcare federation (majority floor ≈ 0.31)", better: "lower" },
  { key: "sensitive_values_exposed", label: "Query values exposed", hint: "fraction of planted sensitive values a contacted node can read", better: "lower" },
  { key: "planted_passage_cited", label: "Planted evidence cited", hint: "malicious passage reaches the prompt", better: "lower" },
  { key: "graded_gain_feb4rag", label: "Routing gain", hint: "graded relevance captured at the contact cap", better: "higher" },
  { key: "answer_accuracy_mirage", label: "Answer accuracy", hint: "MIRAGE MCQ, local Qwen3.5-9B (±8 points at n=150)", better: "higher" },
  { key: "contact_ms_persistent", label: "ms / contact", hint: "real MCP, persistent session", better: "lower" },
  { key: "request_bytes_per_query", label: "request bytes", hint: "application payload per query", better: "lower" },
];

function fmt(v: string | number | null | undefined, key: string): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  if (key === "request_bytes_per_query") return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (key === "contact_ms_persistent") return n.toFixed(1);
  return n.toFixed(3);
}

export default function ResultsPage() {
  const [rows, setRows] = useState<ScorecardRow[]>([]);
  const [sources, setSources] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .scorecard()
      .then((r) => {
        setRows(r.rows);
        setSources(r.sources);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load the scorecard"));
  }, []);

  const main = rows.filter((r) => !String(r.configuration).startsWith("+ trust ranking term"));
  const trust = rows.find((r) => String(r.configuration).startsWith("+ trust ranking term"));

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="flex flex-col gap-6 p-6 md:p-8 max-w-7xl mx-auto">
        <header className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight">Results</h1>
          <p className="text-muted-foreground text-sm max-w-3xl">
            Each row adds one mechanism to the one above. Numbers are copied from the measured
            result files — nothing is recomputed here — and a dash means that configuration was
            not measured on that axis. Definitions and caveats are in docs/36–45.
          </p>
        </header>

        {error && <p className="text-destructive text-sm">{error}</p>}

        <Card>
          <CardHeader>
            <CardTitle>Privacy, quality and cost by configuration</CardTitle>
            <CardDescription>
              Leak columns: lower is better. Gain and accuracy: higher is better.
            </CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[220px]">Configuration</TableHead>
                  {COLUMNS.map((c) => (
                    <TableHead key={c.key} title={c.hint} className="text-right whitespace-nowrap">
                      {c.label}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {main.map((r) => (
                  <TableRow key={String(r.configuration)}>
                    <TableCell className="text-sm">{String(r.configuration)}</TableCell>
                    {COLUMNS.map((c) => (
                      <TableCell key={c.key} className="text-right font-mono text-xs">
                        {fmt(r[c.key], c.key)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {trust && (
          <Card>
            <CardHeader>
              <CardTitle>Malicious source — trust as a ranking term</CardTitle>
              <CardDescription>A forged profile, with and without the trust term (docs/42).</CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              {[
                ["attacker selected, no trust", "a3_attacker_selected_no_trust"],
                ["honest recall, no trust", "a3_honest_recall_no_trust"],
                ["attacker selected, w = 0.5", "a3_attacker_selected_trust_w0.5"],
                ["honest recall, w = 0.5", "a3_honest_recall_trust_w0.5"],
              ].map(([label, key]) => (
                <div key={key}>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="text-xl font-semibold">{fmt(trust[key], key)}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {Object.keys(sources).length > 0 && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer select-none">Result files used</summary>
            <ul className="mt-2 flex flex-col gap-1 font-mono">
              {Object.entries(sources).map(([k, v]) => (
                <li key={k}>
                  {k}: {v}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}
