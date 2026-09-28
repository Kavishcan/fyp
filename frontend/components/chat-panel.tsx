"use client";

import { Send, Settings2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { PrivacyDetails } from "@/components/privacy-details";
import { api, ApiError, type AuditResponse, type IdentityState, type QueryResponse } from "@/lib/api";

type RoutingMode = "legacy" | "smart" | "v2" | "psi";
type DecoyPolicy = "topic_stable" | "cells";

/** What a contacted node receives in each mode — the fact the mode selector exists to make visible. */
const MODE_HELP: Record<RoutingMode, string> = {
  psi: "Proposed. Local routing; nodes receive blinded cluster ids over OPRF/PSI — never the question or a vector.",
  v2: "Local routing; nodes receive an invertible routing-space vector.",
  smart: "Adaptive budgeted selection, no decoys; nodes receive the question text.",
  legacy: "Control. Cosine shortlist, rerank, decoys; nodes receive the question text.",
};

interface ChatMessage {
  id: string;
  question: string;
  status: "pending" | "done" | "error";
  result?: QueryResponse;
  error?: string;
  audit?: AuditResponse;
  auditLoading?: boolean;
}

export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [maxNodes, setMaxNodes] = useState(4);
  const [genuineK, setGenuineK] = useState(1);
  // The studio defaults to the proposed configuration (docs/41): psi dispatch,
  // anonymity cells, cross-node rerank. The API's own default stays legacy;
  // every mode is selectable here so the control can be shown side by side.
  const [routingMode, setRoutingMode] = useState<RoutingMode>("psi");
  const [decoyPolicy, setDecoyPolicy] = useState<DecoyPolicy>("cells");
  const [trustWeight, setTrustWeight] = useState(0.5);
  const [evidenceTopK, setEvidenceTopK] = useState(2);
  const [identity, setIdentity] = useState<IdentityState>({ active: null, available: [] });
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    api.getIdentity().then(setIdentity).catch(() => undefined);
  }, []);

  async function changeIdentity(clientId: string) {
    try {
      setIdentity(await api.setIdentity(clientId === "" ? null : clientId));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not switch identity");
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || sending) return;

    const id = crypto.randomUUID();
    setMessages((m) => [...m, { id, question, status: "pending" }]);
    setInput("");
    setSending(true);
    try {
      const privacyModes = routingMode === "v2" || routingMode === "psi";
      const result = await api.query({
        question,
        max_nodes: maxNodes,
        genuine_k: genuineK,
        routing_mode: routingMode,
        ...(privacyModes
          ? { decoy_policy: decoyPolicy, cell_size: 4, evidence_top_k: evidenceTopK, trust_weight: trustWeight }
          : {}),
      });
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, status: "done", result } : msg)));
    } catch (err) {
      const error = err instanceof ApiError ? err.message : "Query failed";
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, status: "error", error } : msg)));
    } finally {
      setSending(false);
    }
  }

  async function revealAudit(id: string, queryId: string) {
    setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, auditLoading: true } : msg)));
    try {
      const audit = await api.audit(queryId);
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, audit, auditLoading: false } : msg)));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Audit lookup failed");
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, auditLoading: false } : msg)));
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto flex flex-col gap-8 px-4 md:px-6 py-8 min-h-full">
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center text-center gap-2 py-24">
              <h2 className="text-lg font-medium">Ask FedSafeRouter something</h2>
              <p className="text-sm text-muted-foreground max-w-sm">
                Default is the proposed configuration: private (PSI) dispatch with anonymity cells.
                Each answer shows what a caller would see — citations and which sources were
                contacted, never which were genuine. Switch to legacy in settings to compare.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className="flex flex-col gap-4">
              <div className="flex gap-3 justify-end">
                <div className="max-w-[75%] rounded-2xl bg-primary text-primary-foreground px-4 py-2.5 text-sm">
                  {msg.question}
                </div>
                <Avatar className="size-8 shrink-0">
                  <AvatarFallback className="text-xs">You</AvatarFallback>
                </Avatar>
              </div>

              <div className="flex gap-3">
                <Avatar className="size-8 shrink-0">
                  <AvatarFallback className="text-xs bg-accent text-accent-foreground">FR</AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0 flex flex-col gap-2 text-sm rounded-2xl border bg-card px-4 py-3">
                  {msg.status === "pending" && <span className="text-muted-foreground">Routing...</span>}
                  {msg.status === "error" && <span className="text-destructive">{msg.error}</span>}
                  {msg.status === "done" && msg.result && (
                    <>
                      {msg.result.answer ? (
                        <p>{msg.result.answer}</p>
                      ) : (
                        <Badge variant="outline" className="self-start">
                          {msg.result.generation_status}
                        </Badge>
                      )}

                      <div className="flex flex-wrap gap-1 items-center text-xs">
                        <Badge variant="outline" className="font-mono text-[10px]">
                          {msg.result.routing_details?.mode ?? "legacy"}
                        </Badge>
                        <span className="text-muted-foreground">contacted:</span>
                        {msg.result.nodes_contacted.map((n) => (
                          <Badge key={n} variant="secondary" className="font-mono text-[10px]">
                            {n}
                          </Badge>
                        ))}
                      </div>

                      <details className="text-xs">
                        <summary className="cursor-pointer text-muted-foreground select-none">
                          citations ({msg.result.citations.length})
                        </summary>
                        <ul className="mt-2 flex flex-col gap-1">
                          {msg.result.citations.map((c, i) => (
                            <li key={i} className="border rounded p-1.5">
                              <span className="font-mono text-[10px] text-muted-foreground flex items-center gap-1.5">
                                {c.node_id} · {c.score.toFixed(3)}
                                {c.collection && (
                                  <Badge
                                    variant={c.collection === "public" ? "secondary" : "outline"}
                                    className="text-[9px] px-1 py-0"
                                  >
                                    {c.collection}
                                  </Badge>
                                )}
                              </span>
                              <p className="line-clamp-3">{c.document}</p>
                            </li>
                          ))}
                        </ul>
                      </details>

                      {msg.result.privacy && <PrivacyDetails privacy={msg.result.privacy} />}

                      <Button
                        size="sm"
                        variant="outline"
                        className="self-start"
                        onClick={() => revealAudit(msg.id, msg.result!.query_id)}
                        disabled={msg.auditLoading}
                      >
                        {msg.auditLoading ? "Loading..." : "Reveal audit trail"}
                      </Button>

                      {msg.audit && (
                        <div className="text-xs border rounded p-2 bg-muted/30 flex flex-col gap-1.5">
                          <div>
                            <span className="text-muted-foreground">topic key: </span>
                            <span className="font-mono">{msg.audit.topic_key}</span>
                          </div>
                          <div className="flex flex-wrap gap-1 items-center">
                            <span className="text-muted-foreground mr-1">genuine:</span>
                            {msg.audit.genuine_source_ids.map((n) => (
                              <Badge key={n} className="font-mono text-[10px]">
                                {n}
                              </Badge>
                            ))}
                          </div>
                          <div className="flex flex-wrap gap-1 items-center">
                            <span className="text-muted-foreground mr-1">decoys:</span>
                            {msg.audit.decoy_source_ids.map((n) => (
                              <Badge key={n} variant="outline" className="font-mono text-[10px]">
                                {n}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t bg-background shrink-0">
        <form onSubmit={handleSend} className="max-w-3xl mx-auto flex gap-2 items-center px-4 md:px-6 py-4">
          <Popover>
            <PopoverTrigger className={buttonVariants({ variant: "outline", size: "icon", className: "shrink-0" })}>
              <Settings2 className="size-4" />
            </PopoverTrigger>
            <PopoverContent className="w-72 flex flex-col gap-3" align="start">
              <Label className="flex flex-col items-start gap-1.5 text-xs">
                Routing mode
                <select
                  value={routingMode}
                  onChange={(e) => setRoutingMode(e.target.value as RoutingMode)}
                  className="h-8 w-full rounded-md border bg-background px-2 text-sm"
                >
                  <option value="psi">psi — private dispatch (proposed)</option>
                  <option value="v2">v2 — vector dispatch</option>
                  <option value="smart">smart</option>
                  <option value="legacy">legacy (control)</option>
                </select>
                <span className="text-[11px] leading-snug text-muted-foreground font-normal">
                  {MODE_HELP[routingMode]}
                </span>
              </Label>
              <Label className="flex flex-col items-start gap-1.5 text-xs">
                Acting as
                <select
                  value={identity.active?.client_id ?? ""}
                  onChange={(e) => changeIdentity(e.target.value)}
                  className="h-8 w-full rounded-md border bg-background px-2 text-sm"
                >
                  <option value="">no credential</option>
                  {identity.available.map((i) => (
                    <option key={i.client_id} value={i.client_id}>
                      {i.client_id} ({i.roles.join(", ") || "no role"})
                    </option>
                  ))}
                </select>
                <span className="text-[11px] leading-snug text-muted-foreground font-normal">
                  {identity.available.length === 0
                    ? "Load the demo hospital federation on the Dashboard to get identities."
                    : "Nodes read your roles from their own allow-lists; claiming a role gains nothing."}
                </span>
              </Label>
              {(routingMode === "v2" || routingMode === "psi") && (
                <div className="grid grid-cols-2 gap-2">
                  <Label className="flex flex-col items-start gap-1.5 text-xs">
                    Trust weight
                    <Input
                      type="number"
                      min={0}
                      max={5}
                      step={0.5}
                      value={trustWeight}
                      onChange={(e) => setTrustWeight(Number(e.target.value))}
                      className="h-8 text-sm"
                    />
                  </Label>
                  <Label className="flex flex-col items-start gap-1.5 text-xs">
                    Evidence kept
                    <Input
                      type="number"
                      min={1}
                      value={evidenceTopK}
                      onChange={(e) => setEvidenceTopK(Number(e.target.value))}
                      className="h-8 text-sm"
                    />
                  </Label>
                </div>
              )}
              {(routingMode === "v2" || routingMode === "psi") && (
                <Label className="flex flex-col items-start gap-1.5 text-xs">
                  Decoy policy
                  <select
                    value={decoyPolicy}
                    onChange={(e) => setDecoyPolicy(e.target.value as DecoyPolicy)}
                    className="h-8 w-full rounded-md border bg-background px-2 text-sm"
                  >
                    <option value="cells">anonymity cells — hides topic and source</option>
                    <option value="topic_stable">topic-stable decoys — hides source only</option>
                  </select>
                </Label>
              )}
              <Label className="flex flex-col items-start gap-1.5 text-xs">
                Max nodes (m)
                <Input
                  type="number"
                  min={1}
                  value={maxNodes}
                  onChange={(e) => setMaxNodes(Number(e.target.value))}
                  className="h-8 text-sm"
                />
              </Label>
              <Label className="flex flex-col items-start gap-1.5 text-xs">
                Genuine k
                <Input
                  type="number"
                  min={1}
                  value={genuineK}
                  onChange={(e) => setGenuineK(Number(e.target.value))}
                  className="h-8 text-sm"
                />
              </Label>
            </PopoverContent>
          </Popover>
          <Badge variant="outline" className="shrink-0 hidden md:inline-flex font-mono text-[10px]">
            {routingMode}
            {identity.active ? ` · ${identity.active.roles.join(",") || "no role"}` : ""}
          </Badge>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 rounded-full h-11 px-4"
          />
          <Button type="submit" size="icon" className="rounded-full size-11 shrink-0" disabled={sending || !input.trim()}>
            <Send className="size-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
