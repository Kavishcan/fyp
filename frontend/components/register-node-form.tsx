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
      const result = await api.registerNode({ node_id: nodeId.trim(), documents: docs });
      toast.success(`Registered ${result.node_id}`, {
        description: `${result.centroid_count} centroid(s), version ${result.profile_version}`,
      });
      setNodeId("");
      setDocuments("");
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
          <Button type="submit" disabled={submitting} className="self-start">
            {submitting ? "Registering..." : "Register node"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
