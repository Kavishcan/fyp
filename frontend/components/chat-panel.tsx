"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { api, ApiError, type AuditResponse, type QueryResponse } from "@/lib/api";

interface ChatMessage {
  id: string;
  question: string;
  status: "pending" | "done" | "error";
  result?: QueryResponse;
  error?: string;
  audit?: AuditResponse;
  auditLoading?: boolean;
}

export function ChatPanel({ onQueried }: { onQueried: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [maxNodes, setMaxNodes] = useState(5);
  const [genuineK, setGenuineK] = useState(2);
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || sending) return;

    const id = crypto.randomUUID();
    setMessages((m) => [...m, { id, question, status: "pending" }]);
    setInput("");
    setSending(true);
    try {
      const result = await api.query({ question, max_nodes: maxNodes, genuine_k: genuineK });
      setMessages((m) => m.map((msg) => (msg.id === id ? { ...msg, status: "done", result } : msg)));
      onQueried();
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
    <Card className="flex flex-col h-full">
      <CardHeader>
        <CardTitle>Chat</CardTitle>
        <CardDescription>
          Each answer shows only what a caller would see — citations and which sources were
          contacted, never which were genuine versus decoys. Reveal that per message below.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col min-h-0 gap-3">
        <div ref={scrollRef} className="flex-1 overflow-y-auto flex flex-col gap-4 pr-1">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground">No messages yet — ask something below.</p>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className="flex flex-col gap-2">
              <div className="self-end max-w-[85%] rounded-lg bg-primary text-primary-foreground px-3 py-2 text-sm">
                {msg.question}
              </div>

              <div className="self-start max-w-[90%] rounded-lg border bg-card px-3 py-2 text-sm flex flex-col gap-2 w-full">
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
                            <span className="font-mono text-[10px] text-muted-foreground">
                              {c.node_id} · {c.score.toFixed(3)}
                            </span>
                            <p className="line-clamp-3">{c.document}</p>
                          </li>
                        ))}
                      </ul>
                    </details>

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
          ))}
        </div>

        <Separator />

        <form onSubmit={handleSend} className="flex flex-col gap-2">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question..."
              className="flex-1"
            />
            <Button type="submit" disabled={sending || !input.trim()}>
              {sending ? "..." : "Send"}
            </Button>
          </div>
          <div className="flex gap-4 items-center">
            <Label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              max nodes (m)
              <Input
                type="number"
                min={1}
                value={maxNodes}
                onChange={(e) => setMaxNodes(Number(e.target.value))}
                className="w-16 h-7 text-xs"
              />
            </Label>
            <Label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              genuine k
              <Input
                type="number"
                min={1}
                value={genuineK}
                onChange={(e) => setGenuineK(Number(e.target.value))}
                className="w-16 h-7 text-xs"
              />
            </Label>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
