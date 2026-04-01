import React, { useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Workflow } from 'lucide-react';

/* ─── Custom Node ─── */
const AppNode = ({ data }) => (
  <div className="relative bg-brand-dark border-2 border-brand-orange rounded-lg px-5 py-3 min-w-[130px] shadow-lg shadow-brand-orange/10">
    {/* Wave badge — top-right */}
    <span className="absolute -top-2.5 -right-2.5 bg-brand-orange text-black text-[10px] font-bold px-2 py-0.5 rounded-full leading-none shadow-md">
      W{data.wave}
    </span>

    <span className="text-white font-bold text-sm tracking-wide">{data.label}</span>

    {/* Handles */}
    <Handle
      type="target"
      position={Position.Left}
      className="!w-2 !h-2 !bg-brand-orange !border-none"
    />
    <Handle
      type="source"
      position={Position.Right}
      className="!w-2 !h-2 !bg-brand-orange !border-none"
    />
  </div>
);

const nodeTypes = { appNode: AppNode };

/* ─── Helpers ─── */
function buildGraph(waves, dependencies) {
  const nodes = [];
  const edges = [];

  // Map app → wave number
  const appWaveMap = {};
  waves.forEach((waveApps, idx) => {
    waveApps.forEach((app) => {
      appWaveMap[app] = idx + 1;
    });
  });

  // Create nodes positioned by wave (x) and index within wave (y)
  waves.forEach((waveApps, waveIdx) => {
    waveApps.forEach((app, posIdx) => {
      nodes.push({
        id: app,
        type: 'appNode',
        position: { x: waveIdx * 280, y: posIdx * 130 },
        data: { label: app, wave: waveIdx + 1 },
      });
    });
  });

  // Create edges from dependencies
  Object.entries(dependencies).forEach(([app, deps]) => {
    deps.forEach((dep) => {
      edges.push({
        id: `${dep}->${app}`,
        source: dep,
        target: app,
        animated: true,
        style: { stroke: '#FF9900', strokeWidth: 2 },
        markerEnd: {
          type: 'arrowclosed',
          color: '#FF9900',
          width: 18,
          height: 18,
        },
      });
    });
  });

  return { nodes, edges };
}

/* ─── Component ─── */
const GraphView = ({ waves, dependencies }) => {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraph(waves || [], dependencies || {}),
    [waves, dependencies]
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onInit = useCallback((reactFlowInstance) => {
    setTimeout(() => reactFlowInstance.fitView({ padding: 0.25 }), 100);
  }, []);

  if (!waves || waves.length === 0) return null;

  return (
    <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl">
      {/* Title */}
      <div className="flex items-center gap-2.5 mb-4">
        <Workflow className="w-5 h-5 text-brand-orange" />
        <h2 className="text-white text-xl font-bold tracking-wide">
          Dependency Graph (DAG)
        </h2>
      </div>

      {/* React Flow canvas */}
      <div className="w-full h-[420px] rounded-lg overflow-hidden border border-brand-border">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onInit={onInit}
          nodeTypes={nodeTypes}
          fitView
          proOptions={{ hideAttribution: true }}
          style={{ background: '#0F0F0F' }}
        >
          <Background color="#1A1A1A" gap={20} size={1} />
          <MiniMap
            nodeColor={() => '#FF9900'}
            maskColor="rgba(0,0,0,0.7)"
            style={{ background: '#111111' }}
            className="rounded-lg border border-brand-border"
          />
        </ReactFlow>
      </div>
    </div>
  );
};

export default GraphView;
