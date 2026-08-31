"use client";

import Link from "next/link";
import { useState } from "react";
import { ArchitectureFlow } from "@/components/architecture-flow";
import { ChatPanel } from "@/components/chat-panel";
import { NodesList } from "@/components/nodes-list";
import { RegisterNodeForm } from "@/components/register-node-form";

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="h-screen w-full flex flex-col overflow-hidden p-6 md:p-8 gap-4">
      <header className="flex items-start justify-between gap-4 shrink-0">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">FedSafeRouter</h1>
          <p className="text-muted-foreground text-sm max-w-2xl">
            Privacy-aware, trust-aware source routing for federated RAG. Genuine sources are
            dispatched alongside decoys so the selection pattern itself doesn&apos;t reveal
            which sources actually hold the answer.
          </p>
        </div>
        <Link href="/servers" className="text-sm text-muted-foreground hover:text-foreground whitespace-nowrap pt-1">
          Manage servers →
        </Link>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        <div className="h-full min-h-0">
          <ChatPanel onQueried={bump} />
        </div>

        <div className="h-full min-h-0 overflow-y-auto flex flex-col gap-6 pr-1">
          <ArchitectureFlow refreshKey={refreshKey} onChanged={bump} />
          <RegisterNodeForm onRegistered={bump} />
          <NodesList refreshKey={refreshKey} />
        </div>
      </div>
    </div>
  );
}
