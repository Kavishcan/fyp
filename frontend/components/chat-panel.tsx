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

export function ChatPanel() {
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
                Each answer shows only what a caller would see — citations and which sources were
                contacted, never which were genuine versus decoys. Reveal that per message below.
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
            <PopoverContent className="w-56 flex flex-col gap-3" align="start">
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
