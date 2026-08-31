"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  type Edge,
  Handle,
  MarkerType,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, type NodeStatus } from "@/lib/api";

// --- custom node types -----------------------------------------------------

function StageNode({ data }: NodeProps<Node<{ title: string; subtitle?: string }>>) {
  return (
    <div className="rounded-md border bg-card px-3 py-2 shadow-sm w-[190px]">
      <Handle type="target" position={Position.Left} />
      <div className="text-sm font-medium leading-tight">{data.title}</div>
      {data.subtitle && <div className="text-xs text-muted-foreground mt-1">{data.subtitle}</div>}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

function SourceNode({ data }: NodeProps<Node<{ nodeId: string; trust: number; localModel: string }>>) {
  const trustVariant = data.trust >= 0.6 ? "default" : data.trust >= 0.3 ? "secondary" : "destructive";
  return (
    <div className="rounded-md border bg-card px-3 py-2 shadow-sm w-[190px]">
      <Handle type="target" position={Position.Left} />
      <div className="text-sm font-mono truncate">{data.nodeId}</div>
      <div className="flex gap-1 mt-1 flex-wrap">
        <Badge variant={trustVariant} className="text-[10px]">
          trust {data.trust.toFixed(2)}
        </Badge>
        {data.localModel !== "shared-routing-embedder" && (
          <Badge variant="outline" className="text-[10px] font-mono">
            {data.localModel}
          </Badge>
        )}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

function AddSourceNode({ data }: NodeProps<Node<{ onClick: () => void }>>) {
  return (
    <button
      onClick={data.onClick}
      className="rounded-md border border-dashed px-3 py-2 w-[190px] flex items-center gap-2 text-sm text-muted-foreground hover:border-foreground hover:text-foreground transition-colors bg-background"
    >
      <Plus className="size-4" />
      Add source
    </button>
  );
}

const nodeTypes = { stage: StageNode, source: SourceNode, addSource: AddSourceNode };

// --- layout ------------------------------------------------------------

const STAGE_X = { query: 0, embed: 200, router: 420, decoys: 640, sources: 900, merge: 1160, llm: 1380, trust: 1380 };
const ROW_HEIGHT = 64;

function buildGraph(sources: NodeStatus[], onAddClick: () => void): { nodes: Node[]; edges: Edge[] } {
  const sourceRowsHeight = Math.max(sources.length, 1) * ROW_HEIGHT;
  const centerY = sourceRowsHeight / 2;

  const stageNodes: Node[] = [
    { id: "query", type: "stage", position: { x: STAGE_X.query, y: centerY }, data: { title: "Query" } },
    {
      id: "embed",
      type: "stage",
      position: { x: STAGE_X.embed, y: centerY },
      data: { title: "Embed + perturb", subtitle: "shared routing embedder" },
    },
    {
      id: "router",
      type: "stage",
      position: { x: STAGE_X.router, y: centerY },
      data: { title: "Router", subtitle: "score + rerank" },
    },
    {
      id: "decoys",
      type: "stage",
      position: { x: STAGE_X.decoys, y: centerY },
      data: { title: "Anonymity set", subtitle: "genuine + decoys" },
    },
    {
      id: "merge",
      type: "stage",
      position: { x: STAGE_X.merge, y: centerY },
      data: { title: "Merge passages" },
    },
    {
      id: "llm",
      type: "stage",
      position: { x: STAGE_X.llm, y: centerY - 50 },
      data: { title: "LLM", subtitle: "generation" },
    },
    {
      id: "trust",
      type: "stage",
      position: { x: STAGE_X.trust, y: centerY + 50 },
      data: { title: "Trust update", subtitle: "feeds back into rerank" },
    },
  ];

  const sourceNodes: Node[] = sources.map((s, i) => ({
    id: `source-${s.node_id}`,
    type: "source",
    position: { x: STAGE_X.sources, y: i * ROW_HEIGHT },
    data: { nodeId: s.node_id, trust: s.trust, localModel: s.local_model },
  }));

  const addNode: Node = {
    id: "add-source",
    type: "addSource",
    position: { x: STAGE_X.sources, y: sources.length * ROW_HEIGHT },
    data: { onClick: onAddClick },
  };

  const baseEdgeStyle = { markerEnd: { type: MarkerType.ArrowClosed } };

  const edges: Edge[] = [
    { id: "e-query-embed", source: "query", target: "embed", ...baseEdgeStyle },
    { id: "e-embed-router", source: "embed", target: "router", ...baseEdgeStyle },
    { id: "e-router-decoys", source: "router", target: "decoys", ...baseEdgeStyle },
    ...sources.flatMap((s) => [
      { id: `e-decoys-${s.node_id}`, source: "decoys", target: `source-${s.node_id}`, ...baseEdgeStyle },
      { id: `e-${s.node_id}-merge`, source: `source-${s.node_id}`, target: "merge", ...baseEdgeStyle },
    ]),
    { id: "e-merge-llm", source: "merge", target: "llm", ...baseEdgeStyle },
    { id: "e-merge-trust", source: "merge", target: "trust", ...baseEdgeStyle },
    {
      id: "e-trust-router",
      source: "trust",
      target: "router",
      animated: true,
      style: { strokeDasharray: "4 4" },
      label: "feedback",
      ...baseEdgeStyle,
    },
  ];

  return { nodes: [...stageNodes, ...sourceNodes, addNode], edges };
}

// --- add-source dialog -------------------------------------------------

function AddSourceDialog({
  open,
  onOpenChange,
  onRegistered,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRegistered: () => void;
}) {
  const [nodeId, setNodeId] = useState("");
  const [documents, setDocuments] = useState("");
  const [localModel, setLocalModel] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
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
      toast.success(`Registered ${result.node_id}`, { description: `local model: ${result.local_model}` });
      setNodeId("");
      setDocuments("");
      setLocalModel("");
      onOpenChange(false);
      onRegistered();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Failed to register node");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add a source</DialogTitle>
          <DialogDescription>
            Simulated mode — documents are submitted directly and a profile is computed server-side.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="flow-node-id">Node ID</Label>
            <Input id="flow-node-id" value={nodeId} onChange={(e) => setNodeId(e.target.value)} placeholder="hosp_oncology_1" />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="flow-documents">Documents (one per line)</Label>
            <Textarea
              id="flow-documents"
              rows={5}
              value={documents}
              onChange={(e) => setDocuments(e.target.value)}
              placeholder={"chemo protocol for tumour patients\ntumour staging guideline"}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="flow-local-model">Local embedding model (optional)</Label>
            <Input
              id="flow-local-model"
              value={localModel}
              onChange={(e) => setLocalModel(e.target.value)}
              placeholder="leave blank to share the routing embedder"
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Registering..." : "Register node"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// --- main component ------------------------------------------------------

export function ArchitectureFlow({ refreshKey, onChanged }: { refreshKey: number; onChanged: () => void }) {
  const [sources, setSources] = useState<NodeStatus[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    let cancelled = false;
    api.listNodes().then((data) => {
      if (!cancelled) setSources(data);
    });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const openDialog = useCallback(() => setDialogOpen(true), []);

  const graph = useMemo(() => buildGraph(sources, openDialog), [sources, openDialog]);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges);
  }, [graph, setNodes, setEdges]);

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h2 className="text-lg font-medium">Architecture</h2>
        <p className="text-sm text-muted-foreground">
          The live pipeline. Sources on the right are pulled from the running backend — add one with the
          dashed node, or from the Register panel below; either way it shows up here immediately.
        </p>
      </div>
      <div className="h-[480px] rounded-md border bg-muted/20">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={16} />
        </ReactFlow>
      </div>
      <AddSourceDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onRegistered={() => {
          onChanged();
        }}
      />
    </div>
  );
}
