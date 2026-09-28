"use client";

import { Building2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ArchitectureFlow } from "@/components/architecture-flow";
import { DashboardStats } from "@/components/dashboard-stats";
import { NodesList } from "@/components/nodes-list";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = () => setRefreshKey((k) => k + 1);
  const [loadingDemo, setLoadingDemo] = useState(false);

  async function loadDemo() {
    setLoadingDemo(true);
    try {
      const r = await api.loadDemoFederation();
      toast.success(`Loaded ${r.nodes.length} demo hospitals and ${r.identities.length} identities`);
      bump();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not load the demo federation");
    } finally {
      setLoadingDemo(false);
    }
  }

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="flex flex-col gap-6 p-6 md:p-8 max-w-7xl mx-auto">
        <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground text-sm max-w-2xl">
              Live routing architecture and source management — the same backend state the chat
              page queries against.
            </p>
          </div>
          <Button variant="outline" onClick={loadDemo} disabled={loadingDemo} className="self-start md:self-auto">
            <Building2 className="size-4" />
            {loadingDemo ? "Loading..." : "Load demo hospital federation"}
          </Button>
        </header>

        <DashboardStats refreshKey={refreshKey} />
        <ArchitectureFlow refreshKey={refreshKey} onChanged={bump} />
        <NodesList refreshKey={refreshKey} onChanged={bump} />
      </div>
    </div>
  );
}
