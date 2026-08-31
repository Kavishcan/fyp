"use client";

import Link from "next/link";
import { useState } from "react";
import { ArchitectureFlow } from "@/components/architecture-flow";
import { NodesList } from "@/components/nodes-list";
import { RegisterNodeForm } from "@/components/register-node-form";

export default function ServersPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const bump = () => setRefreshKey((k) => k + 1);

  return (
    <div className="min-h-screen w-full flex flex-col p-6 md:p-8 gap-4">
      <header className="flex flex-col gap-1">
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground w-fit">
          ← Back to chat
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">Servers</h1>
        <p className="text-muted-foreground text-sm max-w-2xl">
          Architecture and node management on its own page — the same live state as the main
          dashboard, no chat panel taking up space.
        </p>
      </header>

      <div className="flex flex-col gap-6 max-w-5xl w-full">
        <ArchitectureFlow refreshKey={refreshKey} onChanged={bump} />
        <RegisterNodeForm onRegistered={bump} />
        <NodesList refreshKey={refreshKey} />
      </div>
    </div>
  );
}
