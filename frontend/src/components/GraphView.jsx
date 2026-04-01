import React, { useMemo, useCallback, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { motion, AnimatePresence } from 'framer-motion';
import { Workflow } from 'lucide-react';

/* ══════════════════════════════════════════
   RISK COLORS
   ══════════════════════════════════════════ */
const riskColor = {
  High:   { bg: 'rgba(239,68,68,0.15)',   text: '#f87171', border: 'rgba(239,68,68,0.4)'   },
  Medium: { bg: 'rgba(234,179,8,0.15)',   text: '#facc15', border: 'rgba(234,179,8,0.4)'   },
  Low:    { bg: 'rgba(34,197,94,0.15)',   text: '#4ade80', border: 'rgba(34,197,94,0.4)'   },
};

const waveColors = ['#FF9900', '#a78bfa', '#34d399'];

/* ══════════════════════════════════════════
   TOOLTIP
   ══════════════════════════════════════════ */
const Tooltip = ({ strategy, timeline, risk, visible }) => (
  <AnimatePresence>
    {visible && (
      <motion.div
        initial={{ opacity: 0, y: 6, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 6, scale: 0.95 }}
        transition={{ duration: 0.15 }}
        className="absolute -top-[88px] left-1/2 -translate-x-1/2 z-50 pointer-events-none"
        style={{ width: 160 }}
      >
        <div
          className="rounded-lg px-3 py-2 text-xs text-left shadow-xl"
          style={{
            background: 'rgba(17,17,17,0.95)',
            border: '1px solid #2A2A2A',
            backdropFilter: 'blur(12px)',
          }}
        >
          <div className="text-[#AAAAAA] mb-1">Strategy</div>
          <div className="text-white font-semibold mb-1.5">{strategy || '—'}</div>
          <div className="text-[#AAAAAA] mb-1">Timeline</div>
          <div className="text-[#FF9900] font-semibold">{timeline || '—'}</div>
        </div>
        {/* Arrow */}
        <div
          className="mx-auto w-2.5 h-2.5 -mt-0.5"
          style={{
            background: 'rgba(17,17,17,0.95)',
            border: '0 0 1px 1px solid #2A2A2A',
            transform: 'rotate(45deg)',
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: '1px solid #2A2A2A',
            borderBottom: '1px solid #2A2A2A',
          }}
        />
      </motion.div>
    )}
  </AnimatePresence>
);

/* ══════════════════════════════════════════
   CUSTOM NODE
   ══════════════════════════════════════════ */
const AppNode = ({ data }) => {
  const [hovered, setHovered] = useState(false);
  const risk = data.risk || 'Low';
  const rc = riskColor[risk] || riskColor.Low;
  const waveColor = waveColors[(data.wave - 1) % waveColors.length];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.7 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, delay: data.animDelay || 0, ease: 'easeOut' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        transform: hovered ? 'scale(1.08)' : 'scale(1)',
        transition: 'transform 0.18s ease',
        position: 'relative',
        minWidth: 148,
        background: 'rgba(20, 20, 20, 0.82)',
        backdropFilter: 'blur(12px)',
        border: `1.5px solid ${waveColor}`,
        borderRadius: 12,
        padding: '12px 16px 10px',
        boxShadow: hovered
          ? `0 0 22px ${waveColor}55, 0 4px 24px rgba(0,0,0,0.5)`
          : `0 0 10px ${waveColor}22, 0 2px 12px rgba(0,0,0,0.4)`,
        cursor: 'default',
      }}
    >
      {/* Tooltip */}
      <Tooltip
        strategy={data.strategy}
        timeline={data.timeline}
        risk={risk}
        visible={hovered}
      />

      {/* Wave badge — top right */}
      <span
        className="absolute -top-2.5 -right-2.5 text-black text-[10px] font-black px-2 py-0.5 rounded-full leading-none shadow"
        style={{ background: waveColor }}
      >
        W{data.wave}
      </span>

      {/* App name */}
      <span className="block text-white font-bold text-sm tracking-wide mb-2">
        {data.label}
      </span>

      {/* Risk pill — bottom */}
      <span
        className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border"
        style={{
          background: rc.bg,
          color: rc.text,
          borderColor: rc.border,
        }}
      >
        {risk}
      </span>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: waveColor, border: 'none', width: 8, height: 8 }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: waveColor, border: 'none', width: 8, height: 8 }}
      />
    </motion.div>
  );
};

const nodeTypes = { appNode: AppNode };

/* ══════════════════════════════════════════
   LEGEND
   ══════════════════════════════════════════ */
const Legend = ({ waves }) => (
  <div
    className="absolute top-3 right-3 z-10 flex flex-col gap-1.5 rounded-lg px-3 py-2.5"
    style={{
      background: 'rgba(17,17,17,0.85)',
      border: '1px solid #2A2A2A',
      backdropFilter: 'blur(8px)',
    }}
  >
    {waves.map((_, i) => (
      <div key={i} className="flex items-center gap-2 text-xs text-[#AAAAAA]">
        <span
          className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ background: waveColors[i % waveColors.length] }}
        />
        Wave {i + 1}
      </div>
    ))}
  </div>
);

/* ══════════════════════════════════════════
   GRAPH BUILDER
   ══════════════════════════════════════════ */
function buildGraph(waves, dependencies, risk, strategy, timeline) {
  const nodes = [];
  const edges = [];
  let animDelay = 0;

  waves.forEach((waveApps, waveIdx) => {
    const totalInWave = waveApps.length;
    waveApps.forEach((app, posIdx) => {
      // Center vertically within wave
      const yStep = 130;
      const yOffset = ((totalInWave - 1) * yStep) / 2;

      nodes.push({
        id: app,
        type: 'appNode',
        position: { x: waveIdx * 300, y: posIdx * yStep - yOffset + 100 },
        data: {
          label: app,
          wave: waveIdx + 1,
          risk: risk?.[app],
          strategy: strategy?.[app],
          timeline: timeline?.[app],
          animDelay: animDelay,
        },
      });
      animDelay += 0.08;
    });
  });

  Object.entries(dependencies).forEach(([app, deps]) => {
    deps.forEach((dep) => {
      edges.push({
        id: `${dep}->${app}`,
        source: dep,
        target: app,
        animated: true,
        style: { stroke: '#FF9900', strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#FF9900',
          width: 16,
          height: 16,
        },
      });
    });
  });

  return { nodes, edges };
}

/* ══════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════ */
const GraphView = ({ waves, dependencies, risk, strategy, timeline }) => {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraph(
      waves || [],
      dependencies || {},
      risk || {},
      strategy || {},
      timeline || {}
    ),
    [waves, dependencies, risk, strategy, timeline]
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onInit = useCallback((rf) => {
    setTimeout(() => rf.fitView({ padding: 0.3 }), 120);
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

      {/* Canvas */}
      <div className="relative w-full h-[460px] rounded-lg overflow-hidden border border-brand-border">
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
          minZoom={0.3}
          maxZoom={2}
        >
          {/* Dark dot background */}
          <Background
            variant={BackgroundVariant.Dots}
            color="#2A2A2A"
            gap={24}
            size={1.5}
          />

          {/* Controls — dark themed */}
          <Controls
            showInteractive={false}
            style={{
              background: 'rgba(17,17,17,0.9)',
              border: '1px solid #2A2A2A',
              borderRadius: 8,
              backdropFilter: 'blur(8px)',
            }}
          />
        </ReactFlow>

        {/* Legend overlay */}
        <Legend waves={waves} />
      </div>
    </div>
  );
};

export default GraphView;
