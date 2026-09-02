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
          Trust is dynamic — it updates after every query, so it may differ from the
          static value a source published at registration.
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
                <TableHead>Document count</TableHead>
                <TableHead>Profile version</TableHead>
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
                  <TableCell>{n.document_count_bucket}</TableCell>
                  <TableCell>{n.profile_version}</TableCell>
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
