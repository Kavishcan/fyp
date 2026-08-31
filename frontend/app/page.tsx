"use client";

import { useState } from "react";
import { ArchitectureFlow } from "@/components/architecture-flow";
import { NodesList } from "@/components/nodes-list";
import { QueryPanel } from "@/components/query-panel";
import { RegisterNodeForm } from "@/components/register-node-form";

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="flex-1 flex flex-col gap-6 max-w-6xl w-full mx-auto p-6 md:p-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">FedSafeRouter</h1>
        <p className="text-muted-foreground text-sm max-w-2xl">
          Privacy-aware, trust-aware source routing for federated RAG. Genuine sources are
          dispatched alongside decoys so the selection pattern itself doesn&apos;t reveal
          which sources actually hold the answer.
        </p>
      </header>

      <ArchitectureFlow refreshKey={refreshKey} onChanged={bump} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <div className="flex flex-col gap-6">
          <RegisterNodeForm onRegistered={bump} />
          <NodesList refreshKey={refreshKey} />
        </div>
        <QueryPanel onQueried={bump} />
      </div>
    </div>
  );
}
