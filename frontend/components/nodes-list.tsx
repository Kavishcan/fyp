"use client";

import { Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, ApiError, type NodeStatus } from "@/lib/api";

function trustVariant(trust: number): "default" | "secondary" | "destructive" {
  if (trust >= 0.6) return "default";
  if (trust >= 0.3) return "secondary";
  return "destructive";
}

export function NodesList({ refreshKey, onChanged }: { refreshKey: number; onChanged?: () => void }) {
  const [nodes, setNodes] = useState<NodeStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .listNodes()
      .then((data) => {
        if (!cancelled) setNodes(data);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  async function confirmRemove() {
    if (!pendingRemove) return;
    const nodeId = pendingRemove;
    setRemovingId(nodeId);
    setPendingRemove(null);
    try {
      await api.removeNode(nodeId);
      toast.success(`Removed ${nodeId}`);
      setNodes((prev) => prev.filter((n) => n.node_id !== nodeId));
      onChanged?.();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to remove node");
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Registered sources</CardTitle>
        <CardDescription>
          Trust updates after every query. Collections, access and de-identification come
          from each node: restricted collections open only for roles in that node&rsquo;s
          allow-list, and identifiers are redacted before anything is indexed or served.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-muted-foreground text-sm">Loading...</p>
        ) : nodes.length === 0 ? (
          <p className="text-muted-foreground text-sm">No sources registered yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Node ID</TableHead>
                <TableHead>Transport</TableHead>
                <TableHead>Trust</TableHead>
                <TableHead>Observations</TableHead>
                <TableHead>Collections</TableHead>
                <TableHead>Access</TableHead>
                <TableHead>De-identified</TableHead>
                <TableHead>Documents</TableHead>
                <TableHead>Local model</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {nodes.map((n) => (
                <TableRow key={n.node_id}>
                  <TableCell className="font-mono text-sm">{n.node_id}</TableCell>
                  <TableCell>
                    <Badge variant={n.transport === "mcp" ? "default" : "secondary"}>
                      {n.transport === "mcp" ? "MCP" : "simulated"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={trustVariant(n.trust)}>{n.trust.toFixed(3)}</Badge>
                  </TableCell>
                  <TableCell>{n.trust_observations}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {n.collections.map((c) => (
                        <Badge
                          key={c}
                          variant={c === "public" ? "secondary" : "outline"}
                          className="text-[10px]"
                          title={
                            c === "public"
                              ? "readable by any authorised client"
                              : `readable by: ${Object.entries(n.access_policy ?? {})
                                  .filter(([, cs]) => cs.includes(c))
                                  .map(([r]) => r)
                                  .join(", ") || "no role"}`
                          }
                        >
                          {c}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    {n.gated === true ? (
                      <Badge variant="default" className="text-[10px]">credential + budget</Badge>
                    ) : n.gated === false ? (
                      <Badge variant="secondary" className="text-[10px]">open (public only)</Badge>
                    ) : (
                      <span className="text-muted-foreground text-xs">node-side</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {n.deidentified ? (
                      <span
                        className="text-xs"
                        title={Object.entries(n.deidentified)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join("\n")}
                      >
                        {Object.values(n.deidentified).reduce((a, b) => a + b, 0)} redacted
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-xs">{n.transport === "mcp" ? "node-side" : "none found"}</span>
                    )}
                  </TableCell>
                  <TableCell>{n.document_count_bucket}</TableCell>
                  <TableCell>
                    {n.local_model === "shared-routing-embedder" ? (
                      <span className="text-muted-foreground text-xs">shared</span>
                    ) : (
                      <Badge variant="outline" className="font-mono">
                        {n.local_model}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="size-7 text-muted-foreground hover:text-destructive"
                      disabled={removingId === n.node_id}
                      onClick={() => setPendingRemove(n.node_id)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={pendingRemove !== null} onOpenChange={(open) => !open && setPendingRemove(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove {pendingRemove}?</DialogTitle>
            <DialogDescription>
              It will stop receiving queries immediately. You can re-add it later via
              &ldquo;Add source&rdquo; or &ldquo;Activate servers&rdquo;.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingRemove(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmRemove}>
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
