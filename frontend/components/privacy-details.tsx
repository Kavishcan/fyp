"use client";

import { ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { PrivacySummary } from "@/lib/api";

function fmtBytes(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

function fmtMs(n: number | null | undefined): string {
  return n == null ? "—" : `${n < 10 ? n.toFixed(1) : Math.round(n)} ms`;
}

/** Per-answer view of what left the device: payload type, identity, and per
 * contacted node the bytes, time, envelopes and readable collections. */
export function PrivacyDetails({ privacy }: { privacy: PrivacySummary }) {
  const nodes = Object.entries(privacy.per_node);
  const isBlind = privacy.routing_mode === "blind";
  const isPsi = privacy.routing_mode === "psi" || isBlind;
  return (
    <details className="text-xs">
      <summary className="cursor-pointer text-muted-foreground select-none inline-flex items-center gap-1">
        <ShieldCheck className="size-3.5" /> what left your device
      </summary>
      <div className="mt-2 flex flex-col gap-2 rounded-lg border bg-muted/30 p-2.5">
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <span>
            <span className="text-muted-foreground">each node received: </span>
            <span className={isPsi ? "text-primary font-medium" : "font-medium"}>{privacy.node_receives}</span>
          </span>
          {privacy.decoy_policy && (
            <span>
              <span className="text-muted-foreground">cover: </span>
              {privacy.decoy_policy === "cells"
                ? "fixed anonymity cell"
                : privacy.decoy_policy === "blind_unlock"
                  ? "every node, same number of points (real or dummy)"
                  : "topic-stable decoys"}
            </span>
          )}
          <span>
            <span className="text-muted-foreground">acting as: </span>
            {privacy.identity ? `${privacy.identity.client_id} (${privacy.identity.roles.join(", ") || "no role"})` : "no credential"}
          </span>
          <span>
            <span className="text-muted-foreground">evidence kept: </span>
            {privacy.evidence_kept}
            {privacy.evidence_top_k != null && ` (top ${privacy.evidence_top_k} after cross-node rerank)`}
          </span>
        </div>
        <div className="text-muted-foreground">
          embed {fmtMs(privacy.stage_ms.embed)} · route {fmtMs(privacy.stage_ms.routing)} · contact nodes{" "}
          {fmtMs(privacy.stage_ms.retrieval)}
        </div>
        {nodes.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead className="text-muted-foreground">
                <tr className="text-left">
                  <th className="font-normal pr-3">node</th>
                  <th className="font-normal pr-3">sent</th>
                  <th className="font-normal pr-3">received</th>
                  <th className="font-normal pr-3">time</th>
                  {isPsi && <th className="font-normal pr-3">{isBlind ? "points (real)" : "envelopes opened"}</th>}
                  {isPsi && <th className="font-normal pr-3">passages disclosed</th>}
                  {isPsi && <th className="font-normal">readable collections</th>}
                </tr>
              </thead>
              <tbody>
                {nodes.map(([id, n]) => (
                  <tr key={id} className="border-t border-border/60">
                    <td className="font-mono pr-3 py-1">{id}</td>
                    <td className="pr-3">{fmtBytes(n.request_bytes)}</td>
                    <td className="pr-3">{fmtBytes(n.response_bytes)}</td>
                    <td className="pr-3">{fmtMs(n.contact_ms)}</td>
                    {isPsi && (
                      <td className="pr-3">
                        {n.error ? (
                          <Badge variant="destructive" className="text-[10px]">{n.error}</Badge>
                        ) : (
                          isBlind
                            ? `${n.probes_sent ?? "—"} (${n.real_probes ?? 0} real)`
                            : `${n.envelopes_opened ?? "—"} of ${n.envelopes_delivered ?? "—"}`
                        )}
                      </td>
                    )}
                    {isPsi && <td className="pr-3">{n.passages_disclosed ?? "—"}</td>}
                    {isPsi && (
                      <td className="flex flex-wrap gap-1 py-1">
                        {(n.collections_readable ?? []).map((c) => (
                          <Badge key={c} variant={c === "public" ? "secondary" : "outline"} className="text-[10px]">
                            {c}
                          </Badge>
                        ))}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </details>
  );
}
