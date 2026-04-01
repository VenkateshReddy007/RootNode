import React from 'react';
import { motion } from 'framer-motion';

/* ══════════════════════════════════════════
   LEVEL CONFIG
   ══════════════════════════════════════════ */
const levelConfig = {
  High: {
    bg: 'bg-red-500',
    glow: '0 0 14px rgba(239,68,68,0.7)',
    text: 'text-red-100',
    label: 'H',
  },
  Medium: {
    bg: 'bg-yellow-500',
    glow: '0 0 8px rgba(234,179,8,0.4)',
    text: 'text-yellow-100',
    label: 'M',
  },
  Low: {
    bg: 'bg-green-500',
    glow: '0 0 8px rgba(34,197,94,0.3)',
    text: 'text-green-100',
    label: 'L',
  },
};

const COLUMNS = ['Criticality', 'Data Size', 'Dependencies', 'Complexity', 'Overall'];

/* ══════════════════════════════════════════
   DERIVE PER-APP DIMENSION SCORES FROM PROPS
   Using strategy/risk as heuristics since we
   only have Overall Risk in mock data.
   ══════════════════════════════════════════ */
function deriveScore(app, dimension, risk, strategy) {
  const overall = risk?.[app] || 'Low';
  const strat = strategy?.[app] || 'Rehost';

  const complexityByStrategy = { Refactor: 'High', Replatform: 'Medium', Rehost: 'Low' };
  const criticalityByRisk    = { High: 'High',   Medium: 'Medium',  Low: 'Low' };
  const dataSizeByRisk       = { High: 'Medium',  Medium: 'Low',    Low: 'Low' };
  const depsByStrategy       = { Refactor: 'High', Replatform: 'Medium', Rehost: 'Low' };

  switch (dimension) {
    case 'Criticality':  return criticalityByRisk[overall]    || 'Low';
    case 'Data Size':    return dataSizeByRisk[overall]       || 'Low';
    case 'Dependencies': return depsByStrategy[strat]         || 'Low';
    case 'Complexity':   return complexityByStrategy[strat]   || 'Low';
    case 'Overall':      return overall;
    default:             return 'Low';
  }
}

/* ══════════════════════════════════════════
   HEATMAP CELL
   ══════════════════════════════════════════ */
const Cell = ({ level, isOverall, delay }) => {
  const cfg = levelConfig[level] || levelConfig.Low;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, delay, ease: 'easeOut' }}
      className={`
        flex items-center justify-center rounded-md font-bold text-xs tracking-wider select-none
        ${cfg.bg} ${cfg.text}
        ${isOverall ? 'w-[72px] h-[72px] text-sm' : 'w-[60px] h-[60px]'}
        ${isOverall && level === 'High' ? 'animate-pulse' : ''}
      `}
      style={{
        boxShadow: isOverall ? cfg.glow.replace('14px', '20px') : cfg.glow,
        flexShrink: 0,
      }}
      title={level}
    >
      {cfg.label}
    </motion.div>
  );
};

/* ══════════════════════════════════════════
   COMPONENT
   ══════════════════════════════════════════ */
const RiskHeatmap = ({ risk, strategy, timeline }) => {
  if (!risk) return null;

  const apps = Object.keys(risk);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl overflow-x-auto"
    >
      {/* Title */}
      <h2 className="text-white text-xl font-bold tracking-wide mb-6">
        🔥 Risk Heatmap
      </h2>

      <div className="min-w-max">
        {/* Column headers */}
        <div className="flex items-center gap-3 mb-3 pl-[140px]">
          {COLUMNS.map((col) => (
            <div
              key={col}
              className={`font-semibold text-xs uppercase tracking-wider text-center flex-shrink-0 ${
                col === 'Overall' ? 'w-[72px]' : 'w-[60px]'
              }`}
              style={{ color: '#FF9900' }}
            >
              {col}
            </div>
          ))}
        </div>

        {/* Rows */}
        <div className="flex flex-col gap-3">
          {apps.map((app, rowIdx) => (
            <div key={app} className="flex items-center gap-3">
              {/* App name */}
              <div className="w-[132px] flex-shrink-0 text-white font-bold text-sm truncate pr-2">
                {app}
              </div>

              {/* Cells */}
              {COLUMNS.map((col, colIdx) => {
                const level = deriveScore(app, col, risk, strategy);
                const delay = (rowIdx * COLUMNS.length + colIdx) * 0.04;
                const isOverall = col === 'Overall';

                return (
                  <Cell
                    key={col}
                    level={level}
                    isOverall={isOverall}
                    delay={delay}
                  />
                );
              })}
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-5 mt-6 pt-4 border-t border-brand-border">
          {Object.entries(levelConfig).map(([label, cfg]) => (
            <div key={label} className="flex items-center gap-2">
              <span
                className={`inline-block w-3 h-3 rounded-sm ${cfg.bg}`}
                style={{ boxShadow: cfg.glow }}
              />
              <span className="text-[#AAAAAA] text-xs font-medium">{label}</span>
            </div>
          ))}
          <span className="ml-auto text-[#555] text-xs">
            Hover cells for details · Overall column pulses on High risk
          </span>
        </div>
      </div>
    </motion.div>
  );
};

export default RiskHeatmap;
