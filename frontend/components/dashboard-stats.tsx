"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { api, type NodeStatus } from "@/lib/api";

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-semibold mt-1">{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

export function DashboardStats({ refreshKey }: { refreshKey: number }) {
  const [nodes, setNodes] = useState<NodeStatus[]>([]);

  useEffect(() => {
    let cancelled = false;
    api.listNodes().then((data) => {
      if (!cancelled) setNodes(data);
    });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const mcpCount = nodes.filter((n) => n.transport === "mcp").length;
  const simulatedCount = nodes.length - mcpCount;
  const avgTrust = nodes.length ? nodes.reduce((sum, n) => sum + n.trust, 0) / nodes.length : 0;
  const uniqueModels = new Set(nodes.map((n) => n.local_model)).size;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard label="Total sources" value={nodes.length} />
      <StatCard label="MCP servers" value={mcpCount} sub={`${simulatedCount} simulated`} />
      <StatCard label="Avg trust" value={avgTrust.toFixed(2)} />
      <StatCard label="Distinct local models" value={uniqueModels} />
    </div>
  );
}
