"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, ApiError, type AvailableMCPNode } from "@/lib/api";

export function ActivateServersDialog({
  open,
  onOpenChange,
  onActivated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onActivated: () => void;
}) {
  const [nodes, setNodes] = useState<AvailableMCPNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [activating, setActivating] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api
      .listAvailableNodes()
      .then(setNodes)
      .finally(() => setLoading(false));
  }, [open]);

  async function handleActivate(nodeId: string) {
    setActivating(nodeId);
    try {
      const result = await api.activateNode(nodeId);
      toast.success(`Activated ${result.node_id}`, { description: `local model: ${result.local_model}` });
      setNodes((prev) => prev.filter((n) => n.node_id !== nodeId));
      onActivated();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to activate node");
    } finally {
      setActivating(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] flex flex-col sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Activate more MCP servers</DialogTitle>
          <DialogDescription>
            Real datasets prepared by <code className="font-mono">data/prepare_beir_nodes.py</code>{" "}
            (BEIR corpora and MMLU), not auto-started at boot. Activating one spawns a genuine,
            separate MCP server process holding its own real documents.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto flex flex-col gap-2 -mx-1 px-1">
          {loading && <p className="text-sm text-muted-foreground">Loading...</p>}
          {!loading && nodes.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No more prepared servers available — everything prepared is already running, or run{" "}
              <code className="font-mono">data/prepare_beir_nodes.py</code> to prepare more.
            </p>
          )}
          {nodes.map((n) => (
            <div key={n.node_id} className="flex items-center justify-between border rounded-md px-3 py-2">
              <div className="flex flex-col gap-1">
                <span className="font-mono text-sm">{n.node_id}</span>
                <div className="flex gap-1 flex-wrap">
                  <Badge variant="outline" className="text-[10px]">
                    {n.document_count} docs
                  </Badge>
                  {n.local_model !== "shared-routing-embedder" && (
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {n.local_model}
                    </Badge>
                  )}
                </div>
              </div>
              <Button size="sm" onClick={() => handleActivate(n.node_id)} disabled={activating === n.node_id}>
                {activating === n.node_id ? "Activating..." : "Activate"}
              </Button>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
