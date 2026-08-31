"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";

export function RegisterNodeForm({ onRegistered }: { onRegistered: () => void }) {
  const [nodeId, setNodeId] = useState("");
  const [documents, setDocuments] = useState("");
  const [localModel, setLocalModel] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const docs = documents
      .split("\n")
      .map((d) => d.trim())
      .filter(Boolean);
    if (!nodeId.trim() || docs.length === 0) {
      toast.error("Node ID and at least one document are required");
      return;
    }
    setSubmitting(true);
    try {
      const result = await api.registerNode({
        node_id: nodeId.trim(),
        documents: docs,
        local_model: localModel.trim() || undefined,
      });
      toast.success(`Registered ${result.node_id}`, {
        description: `local model: ${result.local_model} · ${result.centroid_count} centroid(s), version ${result.profile_version}`,
      });
      setNodeId("");
      setDocuments("");
      setLocalModel("");
      onRegistered();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to register node");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Register a source</CardTitle>
        <CardDescription>
          Simulated mode — documents are submitted directly and a profile is computed
          server-side, since no separate MCP node process is running yet.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="node-id">Node ID</Label>
            <Input
              id="node-id"
              placeholder="hosp_oncology_1"
              value={nodeId}
              onChange={(e) => setNodeId(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="documents">Documents (one per line)</Label>
            <Textarea
              id="documents"
              rows={6}
              placeholder={"chemo protocol for tumour patients\ntumour staging guideline"}
              value={documents}
              onChange={(e) => setDocuments(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="local-model">Local embedding model (optional)</Label>
            <Input
              id="local-model"
              placeholder="leave blank to share the routing embedder"
              value={localModel}
              onChange={(e) => setLocalModel(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Any name — it&apos;s a placeholder, not a real model. A distinct name simulates a
              genuinely different, incomparable embedding space for this node&apos;s own local
              retrieval, independent of the shared routing embedder used for source selection.
            </p>
          </div>
          <Button type="submit" disabled={submitting} className="self-start">
            {submitting ? "Registering..." : "Register node"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
