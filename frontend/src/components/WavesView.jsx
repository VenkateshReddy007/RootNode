import React from 'react';
import { motion } from 'framer-motion';
import { Layers, ArrowDown } from 'lucide-react';

const riskColorMap = {
  High: 'bg-red-500/20 text-red-400 border-red-500/40',
  Medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40',
  Low: 'bg-green-500/20 text-green-400 border-green-500/40',
};

const AppCard = ({ app, risk, strategy, index }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4, delay: index * 0.1, ease: 'easeOut' }}
    className="bg-brand-card border border-brand-border rounded-lg p-4 flex flex-col gap-3 min-w-[180px] hover:border-brand-orange/40 transition-colors duration-300"
  >
    <span className="text-white font-bold text-base tracking-wide">{app}</span>

    <div className="flex flex-wrap items-center gap-2">
      {/* Risk badge */}
      <span
        className={`text-[11px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full border ${riskColorMap[risk] || riskColorMap.Low}`}
      >
        {risk}
      </span>

      {/* Strategy badge */}
      <span className="text-[11px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full border border-brand-orange/50 text-brand-orange bg-brand-orange/10">
        {strategy}
      </span>
    </div>
  </motion.div>
);

const WaveSection = ({ waveIndex, apps, risk, strategy, totalWaves }) => (
  <div className="flex flex-col items-center w-full">
    <div className="w-full">
      {/* Wave header */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-brand-orange font-black text-4xl leading-none tabular-nums">
          {waveIndex + 1}
        </span>
        <span className="text-white font-semibold text-lg tracking-wide">
          Wave {waveIndex + 1}
        </span>
        <span className="text-gray-500 text-sm ml-1">
          — {apps.length} app{apps.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* App cards */}
      <div className="flex flex-wrap gap-4">
        {apps.map((app, i) => (
          <AppCard
            key={app}
            app={app}
            risk={risk[app]}
            strategy={strategy[app]}
            index={waveIndex * 3 + i}
          />
        ))}
      </div>
    </div>

    {/* Downward arrow between waves */}
    {waveIndex < totalWaves - 1 && (
      <motion.div
        initial={{ opacity: 0, scale: 0.6 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: (waveIndex + 1) * 0.25 }}
        className="flex flex-col items-center my-5"
      >
        <div className="w-px h-6 bg-gradient-to-b from-brand-orange/60 to-brand-orange/20" />
        <ArrowDown className="w-5 h-5 text-brand-orange/70" />
      </motion.div>
    )}
  </div>
);

const WavesView = ({ waves, risk, strategy }) => {
  if (!waves || waves.length === 0) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl"
    >
      {/* Section title */}
      <div className="flex items-center gap-2.5 mb-6">
        <Layers className="w-5 h-5 text-brand-orange" />
        <h2 className="text-white text-xl font-bold tracking-wide">Migration Waves</h2>
      </div>

      {/* Waves */}
      <div className="flex flex-col items-center">
        {waves.map((apps, idx) => (
          <WaveSection
            key={idx}
            waveIndex={idx}
            apps={apps}
            risk={risk}
            strategy={strategy}
            totalWaves={waves.length}
          />
        ))}
      </div>
    </motion.div>
  );
};

export default WavesView;
