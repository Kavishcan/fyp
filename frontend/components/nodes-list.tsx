"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, type NodeStatus } from "@/lib/api";

function trustVariant(trust: number): "default" | "secondary" | "destructive" {
  if (trust >= 0.6) return "default";
  if (trust >= 0.3) return "secondary";
  return "destructive";
}

export function NodesList({ refreshKey }: { refreshKey: number }) {
  const [nodes, setNodes] = useState<NodeStatus[]>([]);
  const [loading, setLoading] = useState(true);

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
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
