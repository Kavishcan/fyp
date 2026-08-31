"use client";

import { useState } from "react";
import { ArchitectureFlow } from "@/components/architecture-flow";
import { DashboardStats } from "@/components/dashboard-stats";
import { NodesList } from "@/components/nodes-list";

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="h-full w-full overflow-y-auto">
      <div className="flex flex-col gap-6 p-6 md:p-8 max-w-7xl mx-auto">
        <header className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground text-sm max-w-2xl">
            Live routing architecture and source management — the same backend state the chat
            page queries against.
          </p>
        </header>

        <DashboardStats refreshKey={refreshKey} />
        <ArchitectureFlow refreshKey={refreshKey} onChanged={bump} />
        <NodesList refreshKey={refreshKey} />
      </div>
    </div>
  );
}
