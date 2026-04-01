import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert } from 'lucide-react';

const riskMeta = {
  High: {
    pill: 'bg-red-900 text-red-300',
    barColor: 'bg-red-500',
    width: '100%',
  },
  Medium: {
    pill: 'bg-yellow-900 text-yellow-300',
    barColor: 'bg-yellow-500',
    width: '60%',
  },
  Low: {
    pill: 'bg-green-900 text-green-300',
    barColor: 'bg-green-500',
    width: '30%',
  },
};

const RiskTable = ({ risk, strategy, timeline }) => {
  if (!risk) return null;

  const apps = Object.keys(risk);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl"
    >
      {/* Title */}
      <div className="flex items-center gap-2.5 mb-5">
        <ShieldAlert className="w-5 h-5 text-brand-orange" />
        <h2 className="text-white text-xl font-bold tracking-wide">Risk Analysis</h2>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-brand-border">
        <table className="w-full text-sm text-left">
          {/* Header */}
          <thead>
            <tr className="bg-[#111] text-brand-orange uppercase text-xs tracking-wider">
              <th className="px-5 py-3 font-semibold">Application</th>
              <th className="px-5 py-3 font-semibold">Risk Level</th>
              <th className="px-5 py-3 font-semibold">Strategy</th>
              <th className="px-5 py-3 font-semibold">Timeline</th>
              <th className="px-5 py-3 font-semibold min-w-[180px]">Risk Score</th>
            </tr>
          </thead>

          {/* Body */}
          <tbody>
            {apps.map((app, idx) => {
              const level = risk[app] || 'Low';
              const meta = riskMeta[level] || riskMeta.Low;

              return (
                <tr
                  key={app}
                  className={`${
                    idx % 2 === 0 ? 'bg-brand-card' : 'bg-[#222]'
                  } border-t border-brand-border hover:bg-brand-orange/5 transition-colors duration-200`}
                >
                  {/* App name */}
                  <td className="px-5 py-3.5 text-white font-semibold">{app}</td>

                  {/* Risk pill */}
                  <td className="px-5 py-3.5">
                    <span
                      className={`text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full ${meta.pill}`}
                    >
                      {level}
                    </span>
                  </td>

                  {/* Strategy */}
                  <td className="px-5 py-3.5 text-gray-300">{strategy?.[app] || '—'}</td>

                  {/* Timeline */}
                  <td className="px-5 py-3.5 text-gray-400 font-mono text-xs">
                    {timeline?.[app] || '—'}
                  </td>

                  {/* Risk score bar */}
                  <td className="px-5 py-3.5">
                    <div className="w-full h-2.5 bg-[#1A1A1A] rounded-full overflow-hidden border border-brand-border">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: meta.width }}
                        transition={{
                          duration: 0.8,
                          delay: idx * 0.12,
                          ease: 'easeOut',
                        }}
                        className={`h-full rounded-full ${meta.barColor}`}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};

export default RiskTable;
