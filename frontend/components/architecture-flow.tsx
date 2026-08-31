"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  type Edge,
  Handle,
  MarkerType,
  type Node,
  type NodeProps,
  Panel,
  Position,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import { Plus, Server } from "lucide-react";
import { toast } from "sonner";
import { ActivateServersDialog } from "@/components/activate-servers-dialog";
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

// --- custom node types, top/bottom handles for a vertical layout -----------

function StageNode({ data }: NodeProps<Node<{ title: string; subtitle?: string }>>) {
  return (
    <div className="rounded-md border bg-card px-3 py-2 shadow-sm w-[190px]">
      <Handle type="target" position={Position.Top} />
      <div className="text-sm font-medium leading-tight">{data.title}</div>
      {data.subtitle && <div className="text-xs text-muted-foreground mt-1">{data.subtitle}</div>}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

function SourceNode({
  data,
}: NodeProps<Node<{ nodeId: string; trust: number; localModel: string; transport: string }>>) {
  const trustVariant = data.trust >= 0.6 ? "default" : data.trust >= 0.3 ? "secondary" : "destructive";
  return (
    <div className="rounded-md border bg-card px-3 py-2 shadow-sm w-[190px]">
      <Handle type="target" position={Position.Top} />
      <div className="text-sm font-mono truncate">{data.nodeId}</div>
      <div className="flex gap-1 mt-1 flex-wrap">
        {data.transport === "mcp" && (
          <Badge variant="default" className="text-[10px]">
            MCP
          </Badge>
        )}
        <Badge variant={trustVariant} className="text-[10px]">
          trust {data.trust.toFixed(2)}
        </Badge>
        {data.localModel !== "shared-routing-embedder" && (
          <Badge variant="outline" className="text-[10px] font-mono">
            {data.localModel}
          </Badge>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

const nodeTypes = { stage: StageNode, source: SourceNode };

// --- layout: vertical, sources fan out horizontally at their own row -------

const NODE_WIDTH = 190;
const SOURCE_SPACING = 220;
const ROW_HEIGHT = 110;

function buildGraph(sources: NodeStatus[]): { nodes: Node[]; edges: Edge[] } {
  const sourceCount = Math.max(sources.length, 1);
  const rowWidth = (sourceCount - 1) * SOURCE_SPACING;
  const centerX = rowWidth / 2;

  const stageNodes: Node[] = [
    { id: "query", type: "stage", position: { x: centerX, y: 0 }, data: { title: "Query" } },
    {
      id: "embed",
      type: "stage",
      position: { x: centerX, y: ROW_HEIGHT },
      data: { title: "Embed + perturb", subtitle: "shared routing embedder" },
    },
    {
      id: "router",
      type: "stage",
      position: { x: centerX, y: ROW_HEIGHT * 2 },
      data: { title: "Router", subtitle: "score + rerank" },
    },
    {
      id: "decoys",
      type: "stage",
      position: { x: centerX, y: ROW_HEIGHT * 3 },
      data: { title: "Anonymity set", subtitle: "genuine + decoys" },
    },
    {
      id: "merge",
      type: "stage",
      position: { x: centerX, y: ROW_HEIGHT * 5 },
      data: { title: "Merge passages" },
    },
    {
      id: "llm",
      type: "stage",
      position: { x: centerX - 110, y: ROW_HEIGHT * 6 },
      data: { title: "LLM", subtitle: "generation" },
    },
    {
      id: "trust",
      type: "stage",
      position: { x: centerX + 110, y: ROW_HEIGHT * 6 },
      data: { title: "Trust update", subtitle: "feeds back into rerank" },
    },
  ];

  const sourceNodes: Node[] = sources.map((s, i) => ({
    id: `source-${s.node_id}`,
    type: "source",
    position: { x: i * SOURCE_SPACING, y: ROW_HEIGHT * 4 },
    data: { nodeId: s.node_id, trust: s.trust, localModel: s.local_model, transport: s.transport },
  }));

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

  return { nodes: [...stageNodes, ...sourceNodes], edges };
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
  const [serversDialogOpen, setServersDialogOpen] = useState(false);
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

  const graph = useMemo(() => buildGraph(sources), [sources]);

  useEffect(() => {
    setNodes(graph.nodes);
    setEdges(graph.edges);
  }, [graph, setNodes, setEdges]);

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h2 className="text-lg font-medium">Architecture</h2>
        <p className="text-sm text-muted-foreground">
          The live pipeline, top to bottom. Add a simulated source or activate a real MCP server
          from the buttons in the corner — either way it shows up here immediately.
        </p>
      </div>
      <div className="h-[600px] rounded-md border bg-muted/20">
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
          <Panel position="top-right" className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setServersDialogOpen(true)} className="gap-1.5 shadow-sm">
              <Server className="size-4" />
              Activate servers
            </Button>
            <Button size="sm" onClick={openDialog} className="gap-1.5 shadow-sm">
              <Plus className="size-4" />
              Add source
            </Button>
          </Panel>
        </ReactFlow>
      </div>
      <AddSourceDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onRegistered={() => {
          onChanged();
        }}
      />
      <ActivateServersDialog
        open={serversDialogOpen}
        onOpenChange={setServersDialogOpen}
        onActivated={onChanged}
      />
    </div>
  );
}
