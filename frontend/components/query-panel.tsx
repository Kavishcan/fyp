"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { api, ApiError, type AuditResponse, type QueryResponse } from "@/lib/api";

export function QueryPanel({ onQueried }: { onQueried: () => void }) {
  const [question, setQuestion] = useState("");
  const [maxNodes, setMaxNodes] = useState(5);
  const [genuineK, setGenuineK] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [audit, setAudit] = useState<AuditResponse | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setSubmitting(true);
    setResult(null);
    setAudit(null);
    try {
      const res = await api.query({
        question: question.trim(),
        max_nodes: maxNodes,
        genuine_k: genuineK,
      });
      setResult(res);
      onQueried();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Query failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function loadAudit() {
    if (!result) return;
    setAuditLoading(true);
    try {
      setAudit(await api.audit(result.query_id));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Audit lookup failed");
    } finally {
      setAuditLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Query</CardTitle>
        <CardDescription>
          The response below shows only what a caller would see: citations and which
          sources were contacted — not which were genuine versus decoys. Use &ldquo;Reveal
          audit trail&rdquo; to see that breakdown, the way an operator or auditor would.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="question">Question</Label>
            <Input
              id="question"
              placeholder="what is the tumour chemo protocol"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>
          <div className="flex gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="max-nodes">Max nodes (m)</Label>
              <Input
                id="max-nodes"
                type="number"
                min={1}
                className="w-28"
                value={maxNodes}
                onChange={(e) => setMaxNodes(Number(e.target.value))}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="genuine-k">Genuine k</Label>
              <Input
                id="genuine-k"
                type="number"
                min={1}
                className="w-28"
                value={genuineK}
                onChange={(e) => setGenuineK(Number(e.target.value))}
              />
            </div>
          </div>
          <Button type="submit" disabled={submitting} className="self-start">
            {submitting ? "Routing..." : "Run query"}
          </Button>
        </form>

        {result && (
          <>
            <Separator />
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">Answer:</span>
                {result.answer ? (
                  <span>{result.answer}</span>
                ) : (
                  <Badge variant="outline">{result.generation_status}</Badge>
                )}
              </div>

              <div className="flex flex-wrap gap-2 items-center text-sm">
                <span className="text-muted-foreground">Nodes contacted:</span>
                {result.nodes_contacted.map((n) => (
                  <Badge key={n} variant="secondary" className="font-mono">
                    {n}
                  </Badge>
                ))}
              </div>

              <div className="flex flex-col gap-2">
                <span className="text-muted-foreground text-sm">Citations:</span>
                <ul className="flex flex-col gap-1">
                  {result.citations.map((c, i) => (
                    <li key={i} className="text-sm border rounded-md p-2">
                      <span className="font-mono text-xs text-muted-foreground">
                        {c.node_id} · score {c.score.toFixed(3)}
                      </span>
                      <p>{c.document}</p>
                    </li>
                  ))}
                </ul>
              </div>

              <Button variant="outline" size="sm" className="self-start" onClick={loadAudit} disabled={auditLoading}>
                {auditLoading ? "Loading..." : "Reveal audit trail"}
              </Button>

              {audit && (
                <div className="text-sm border rounded-md p-3 flex flex-col gap-2 bg-muted/30">
                  <div>
                    <span className="text-muted-foreground">Topic key: </span>
                    <span className="font-mono">{audit.topic_key}</span>
                  </div>
                  <div className="flex flex-wrap gap-1 items-center">
                    <span className="text-muted-foreground mr-1">Genuine:</span>
                    {audit.genuine_source_ids.map((n) => (
                      <Badge key={n} className="font-mono">
                        {n}
                      </Badge>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-1 items-center">
                    <span className="text-muted-foreground mr-1">Decoys:</span>
                    {audit.decoy_source_ids.map((n) => (
                      <Badge key={n} variant="outline" className="font-mono">
                        {n}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
