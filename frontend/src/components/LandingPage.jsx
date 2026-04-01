import React, { useEffect, useState, useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
  Upload,
  GitBranch,
  BarChart3,
  AlertTriangle,
  RefreshCw,
  Bot,
  ArrowRight,
  Hexagon,
} from 'lucide-react';

/* ════════════════════════════════════════════════════
   ANIMATED GRID BACKGROUND (fixed behind everything)
   ════════════════════════════════════════════════════ */
const GridBackground = () => (
  <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
    <div
      className="absolute w-[200%] h-[200%] -top-1/2 -left-1/2"
      style={{
        backgroundImage: `
          linear-gradient(to right, rgba(255,153,0,0.06) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(255,153,0,0.06) 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px',
        animation: 'gridDrift 20s linear infinite',
      }}
    />
    <style>{`
      @keyframes gridDrift {
        0%   { transform: translate(0, 0); }
        100% { transform: translate(60px, 60px); }
      }
    `}</style>
  </div>
);

/* ════════════════════════════════════════════════════
   COUNT-UP HOOK
   ════════════════════════════════════════════════════ */
const useCountUp = (end, duration = 1.6, startWhen = true) => {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!startWhen) return;
    let start = 0;
    const increment = end / (duration * 60);
    const timer = setInterval(() => {
      start += increment;
      if (start >= end) { setCount(end); clearInterval(timer); }
      else setCount(Math.floor(start));
    }, 1000 / 60);
    return () => clearInterval(timer);
  }, [end, duration, startWhen]);
  return count;
};

/* ════════════════════════════════════════════════════
   STAT PILL
   ════════════════════════════════════════════════════ */
const StatPill = ({ value, suffix, label, delay }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });
  const count = useCountUp(value, 1.6, isInView);
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay }}
      className="flex items-center gap-3 bg-[#111] border border-[#1E1E1E] rounded-full px-6 py-3"
    >
      <span className="text-[#FF9900] font-black text-2xl tabular-nums">
        {suffix === 's' && count}{suffix === 's' && 's'}
        {suffix === '%' && count}{suffix === '%' && '%'}
        {suffix === 'M' && '$'}{suffix === 'M' && count}{suffix === 'M' && 'M'}
      </span>
      <span className="text-[#AAAAAA] text-sm font-medium">{label}</span>
    </motion.div>
  );
};

/* ════════════════════════════════════════════════════
   NAVBAR (fixed)
   ════════════════════════════════════════════════════ */
const LandingNav = ({ onEnterApp }) => (
  <motion.nav
    initial={{ y: -60, opacity: 0 }}
    animate={{ y: 0, opacity: 1 }}
    transition={{ duration: 0.6, ease: 'easeOut' }}
    className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4"
    style={{ background: 'rgba(10,10,10,0.8)', backdropFilter: 'blur(12px)' }}
  >
    <div className="flex items-center gap-2">
      <Hexagon className="w-6 h-6 text-[#FF9900]" />
      <span className="text-[#FF9900] font-bold text-xl tracking-tight">RootNode</span>
    </div>
    <button
      onClick={onEnterApp}
      className="flex items-center gap-2 border border-[#FF9900] text-[#FF9900] px-5 py-2 rounded-full text-sm font-semibold hover:bg-[#FF9900]/10 transition-all duration-200 cursor-pointer"
    >
      Launch App <ArrowRight className="w-4 h-4" />
    </button>
  </motion.nav>
);

/* ════════════════════════════════════════════════════
   SECTION 1 — HERO
   ════════════════════════════════════════════════════ */
const HeroSection = ({ onEnterApp }) => {
  const wordVariants = {
    hidden: { opacity: 0, y: 40 },
    visible: (i) => ({
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, delay: i * 0.1, ease: 'easeOut' },
    }),
  };

  return (
    <section className="relative z-[1] h-screen flex flex-col items-center justify-center text-center px-6 snap-start">


      {/* Headline */}
      <h1 className="text-5xl sm:text-6xl lg:text-7xl font-black leading-tight mb-6">
        {['Cloud', 'Migration,'].map((word, i) => (
          <motion.span
            key={word}
            custom={i}
            initial="hidden"
            animate="visible"
            variants={wordVariants}
            className="inline-block mr-4 text-white"
          >
            {word}
          </motion.span>
        ))}
        <br />
        {['Replanned', 'by', 'AI.'].map((word, i) => (
          <motion.span
            key={word}
            custom={i + 2}
            initial="hidden"
            animate="visible"
            variants={wordVariants}
            className="inline-block mr-4 text-[#FF9900] italic"
          >
            {word}
          </motion.span>
        ))}
      </h1>

      {/* Subtext */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="text-[#AAAAAA] text-lg max-w-xl mx-auto mb-10 leading-relaxed"
      >
        Upload your application portfolio. Get dependency graphs, wave plans,
        risk scores, and AI reasoning — in 8 seconds.
      </motion.p>

      {/* CTA Button */}
      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.6, type: 'spring', stiffness: 200 }}
        whileHover={{ scale: 1.05, boxShadow: '0 0 40px rgba(255,153,0,0.45)' }}
        whileTap={{ scale: 0.97 }}
        onClick={onEnterApp}
        className="bg-[#FF9900] text-black font-bold text-lg px-10 py-4 rounded-full shadow-[0_0_30px_rgba(255,153,0,0.25)] cursor-pointer mb-12 transition-shadow duration-300"
      >
        Start Planning →
      </motion.button>

      {/* Stats */}
      <div className="flex flex-wrap justify-center gap-4">
        <StatPill value={8} suffix="s" label="Plan Generation" delay={0.8} />
        <StatPill value={70} suffix="%" label="Faster Migration" delay={0.9} />
        <StatPill value={2} suffix="M" label="Saved" delay={1.0} />
      </div>
    </section>
  );
};

/* ════════════════════════════════════════════════════
   MARQUEE STRIP — between Hero and Problem
   ════════════════════════════════════════════════════ */
const MARQUEE_CARDS = [
  { emoji: '🔗', title: 'Dependency Graph',    sub: 'Auto-built DAG' },
  { emoji: '🌊', title: 'Wave Planning',        sub: 'Topological sort' },
  { emoji: '⚠️', title: 'Risk Scoring',         sub: '4-factor analysis' },
  { emoji: '🤖', title: 'AI Explanation',       sub: 'Amazon Bedrock' },
  { emoji: '🔄', title: 'Strategy Assignment',  sub: 'Rehost · Replatform · Refactor' },
  { emoji: '📅', title: 'Timeline Estimation',  sub: 'Per app & per wave' },
];

const MarqueeCard = ({ emoji, title, sub }) => (
  <div
    style={{
      display: 'flex',
      flexDirection: 'row',
      alignItems: 'center',
      gap: '12px',
      background: '#111111',
      border: '1px solid rgba(255,153,0,0.4)',
      borderRadius: '1rem',
      padding: '16px 24px',
      whiteSpace: 'nowrap',
      minWidth: '220px',
      flexShrink: 0,
      userSelect: 'none',
    }}
  >
    <span style={{ fontSize: '1.5rem', lineHeight: 1 }}>{emoji}</span>
    <div>
      <div style={{ color: '#ffffff', fontWeight: 600, fontSize: '0.875rem' }}>{title}</div>
      <div style={{ color: '#FF9900', fontWeight: 500, fontSize: '0.75rem', marginTop: 2 }}>{sub}</div>
    </div>
  </div>
);

const MarqueeSection = () => (
  <section
    className="relative z-[1] snap-start"
    style={{ padding: '32px 0', overflow: 'hidden' }}
  >
    {/* @keyframes injected once */}
    <style>{`
      @keyframes marquee {
        from { transform: translateX(0); }
        to   { transform: translateX(-50%); }
      }
      .marquee-track {
        animation: marquee 30s linear infinite;
      }
      .marquee-track:hover {
        animation-play-state: paused;
      }
    `}</style>

    {/* Label */}
    <p style={{
      textAlign: 'center',
      color: '#FF9900',
      fontWeight: 700,
      fontSize: '0.7rem',
      letterSpacing: '0.2em',
      textTransform: 'uppercase',
      marginBottom: '16px',
    }}>
      WHAT ROOTNODE DOES
    </p>

    {/* Fade-edge mask wrapper */}
    <div
      style={{
        overflow: 'hidden',
        maskImage: 'linear-gradient(to right, transparent, black 10%, black 90%, transparent)',
        WebkitMaskImage: 'linear-gradient(to right, transparent, black 10%, black 90%, transparent)',
      }}
    >
      {/* Scrolling track — card list duplicated for seamless loop */}
      <div
        className="marquee-track"
        style={{ display: 'flex', width: 'fit-content', gap: '16px' }}
      >
        {/* Original set */}
        {MARQUEE_CARDS.map((c) => <MarqueeCard key={`a-${c.title}`} {...c} />)}
        {/* Clone set — creates the seamless illusion */}
        {MARQUEE_CARDS.map((c) => <MarqueeCard key={`b-${c.title}`} {...c} />)}
      </div>
    </div>
  </section>
);

/* ════════════════════════════════════════════════════
   SECTION 2 — PROBLEM
   ════════════════════════════════════════════════════ */
const problems = [
  { emoji: '🕸️', title: 'Dependency Chaos', desc: 'Manual tracking of 500+ app dependencies across teams, spreadsheets, and Confluence pages that are never up to date.' },
  { emoji: '⏱️', title: 'Weeks of Work', desc: 'Consultants charge $2M+ for spreadsheet-based migration plans that take 6–12 weeks to produce.' },
  { emoji: '🔍', title: 'Zero Explainability', desc: 'No existing tool tells you WHY it ranked risks or ordered waves. You get an answer — never the reasoning.' },
];

const ProblemSection = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, amount: 0.3 });

  return (
    <section ref={ref} className="relative z-[1] h-screen flex items-center px-8 lg:px-16 snap-start">
      {/* Left label */}
      <div className="hidden lg:flex w-[35%] h-full items-center justify-center">
        <motion.span
          initial={{ opacity: 0, x: -40 }}
          animate={isInView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-[#FF9900] font-black text-6xl xl:text-7xl tracking-tight"
          style={{ writingMode: 'vertical-lr', textOrientation: 'mixed' }}
        >
          THE PROBLEM
        </motion.span>
      </div>

      {/* Right cards */}
      <div className="flex-1 flex flex-col gap-6 max-w-2xl">
        <h2 className="text-[#FF9900] font-black text-3xl mb-2 lg:hidden">THE PROBLEM</h2>
        {problems.map((p, i) => (
          <motion.div
            key={p.title}
            initial={{ opacity: 0, x: 80 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.5, delay: i * 0.15, ease: 'easeOut' }}
            className="bg-[#111] border-l-4 border-[#FF9900] rounded-lg p-6 hover:bg-[#161616] transition-colors duration-200"
          >
            <h3 className="text-white text-xl font-bold mb-2">
              <span className="mr-2">{p.emoji}</span>{p.title}
            </h3>
            <p className="text-[#AAAAAA] text-sm leading-relaxed">{p.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
};

/* ════════════════════════════════════════════════════
   SECTION 3 — HOW IT WORKS
   ════════════════════════════════════════════════════ */
const steps = [
  { num: '01', icon: Upload, title: 'Upload Portfolio', desc: 'Paste or upload your CSV application inventory with dependencies and metadata.' },
  { num: '02', icon: GitBranch, title: 'Build Dependency DAG', desc: 'We parse relationships and construct a directed acyclic graph automatically.' },
  { num: '03', icon: BarChart3, title: 'Generate Waves', desc: 'Topological sort groups apps into sequenced migration waves.' },
  { num: '04', icon: AlertTriangle, title: 'Score Risk', desc: 'Each app gets a risk score based on criticality, complexity, and data size.' },
  { num: '05', icon: RefreshCw, title: 'Assign Strategy', desc: 'AI picks the optimal 7R strategy — Rehost, Replatform, or Refactor.' },
  { num: '06', icon: Bot, title: 'AI Explanation', desc: 'Amazon Bedrock explains every decision in plain English with full reasoning.' },
];

const HowItWorksSection = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, amount: 0.2 });

  return (
    <section ref={ref} className="relative z-[1] h-screen flex flex-col items-center justify-center px-8 snap-start">
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.5 }}
        className="text-white text-4xl lg:text-5xl font-black text-center mb-14"
      >
        Six Steps. <span className="text-[#FF9900]">Eight Seconds.</span>
      </motion.h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 max-w-5xl w-full">
        {steps.map((s, i) => {
          const Icon = s.icon;
          return (
            <motion.div
              key={s.num}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.4, delay: i * 0.1, ease: 'easeOut' }}
              className="group relative bg-[#111] border border-[#1E1E1E] rounded-xl p-6 hover:border-[#FF9900]/60 hover:-translate-y-1 transition-all duration-200 cursor-default overflow-hidden"
            >
              {/* Large faded number */}
              <span className="absolute top-3 right-4 text-[#FF9900]/10 text-6xl font-black select-none pointer-events-none">
                {s.num}
              </span>
              <div className="relative z-[1]">
                <Icon className="w-6 h-6 text-[#FF9900] mb-3" />
                <h3 className="text-white font-bold text-base mb-1.5">{s.title}</h3>
                <p className="text-[#AAAAAA] text-sm leading-relaxed">{s.desc}</p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
};

/* ════════════════════════════════════════════════════
   SECTION 4 — ARCHITECTURE
   ════════════════════════════════════════════════════ */
const archSteps = [
  { emoji: '⚛️', label: 'React UI', sub: 'CSV Upload' },
  { emoji: '🌐', label: 'API Gateway', sub: 'REST endpoint' },
  { emoji: '⚡', label: 'Lambda', sub: 'Core pipeline' },
  { emoji: '🧠', label: 'Bedrock', sub: 'Claude Sonnet', highlight: true },
  { emoji: '🪣', label: 'S3', sub: 'Plan storage' },
];

const AnimatedArrow = () => (
  <div className="hidden md:flex items-center mx-1">
    <svg width="50" height="20" viewBox="0 0 50 20" className="overflow-visible">
      <line
        x1="0" y1="10" x2="40" y2="10"
        stroke="#FF9900"
        strokeWidth="2"
        strokeDasharray="6 4"
        className="animate-[dashFlow_1s_linear_infinite]"
      />
      <polygon points="38,5 48,10 38,15" fill="#FF9900" />
    </svg>
    <style>{`
      @keyframes dashFlow {
        0%   { stroke-dashoffset: 0; }
        100% { stroke-dashoffset: -20; }
      }
    `}</style>
  </div>
);

const ArchitectureSection = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, amount: 0.3 });

  return (
    <section ref={ref} className="relative z-[1] h-screen flex flex-col items-center justify-center px-8 snap-start">
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.5 }}
        className="text-white text-4xl lg:text-5xl font-black text-center mb-16"
      >
        Built on <span className="text-[#FF9900]">AWS.</span>
      </motion.h2>

      <div className="flex flex-wrap items-center justify-center gap-2">
        {archSteps.map((s, i) => (
          <React.Fragment key={s.label}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.4, delay: i * 0.12 }}
              className={`flex flex-col items-center gap-3 px-6 py-5 rounded-xl border transition-all duration-300 min-w-[130px] ${
                s.highlight
                  ? 'bg-[#111] border-[#FF9900]/60 shadow-[0_0_30px_rgba(255,153,0,0.2)]'
                  : 'bg-[#111] border-[#1E1E1E] hover:border-[#FF9900]/30'
              }`}
            >
              <span className="text-3xl">{s.emoji}</span>
              <span className="text-white font-bold text-sm">{s.label}</span>
              <span className="text-[#AAAAAA] text-xs">{s.sub}</span>
            </motion.div>
            {i < archSteps.length - 1 && <AnimatedArrow />}
          </React.Fragment>
        ))}
      </div>
    </section>
  );
};

/* ════════════════════════════════════════════════════
   SECTION 5 — FINAL CTA
   ════════════════════════════════════════════════════ */
const CTASection = ({ onEnterApp }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, amount: 0.4 });

  return (
    <section ref={ref} className="relative z-[1] h-screen flex flex-col items-center justify-center text-center px-6 snap-start overflow-hidden">
      {/* Radial glow */}
      <div className="absolute w-[600px] h-[600px] rounded-full bg-[#FF9900]/8 blur-[120px] pointer-events-none" />

      <motion.h2
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
        className="text-white text-4xl lg:text-5xl font-black mb-4 relative"
      >
        Ready to migrate <span className="text-[#FF9900]">smarter?</span>
      </motion.h2>

      <motion.p
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="text-[#AAAAAA] text-lg max-w-lg mb-10 relative"
      >
        Join teams replacing $2M consulting bills with 8-second AI plans.
      </motion.p>

      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={isInView ? { opacity: 1, scale: 1 } : {}}
        transition={{ duration: 0.5, delay: 0.4, type: 'spring', stiffness: 200 }}
        whileHover={{ scale: 1.05, boxShadow: '0 0 50px rgba(255,153,0,0.5)' }}
        whileTap={{ scale: 0.97 }}
        onClick={onEnterApp}
        className="relative bg-[#FF9900] text-black font-bold text-lg px-10 py-4 rounded-full shadow-[0_0_30px_rgba(255,153,0,0.3)] cursor-pointer mb-6 transition-shadow duration-300"
      >
        Get Started Free →
      </motion.button>

      <motion.span
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ delay: 0.6 }}
        className="text-[#555] text-xs relative"
      >
        No credit card. No AWS account needed to try.
      </motion.span>
    </section>
  );
};

/* ════════════════════════════════════════════════════
   LANDING PAGE (main export)
   ════════════════════════════════════════════════════ */
const LandingPage = ({ onEnterApp }) => {
  return (
    <div
      className="h-screen overflow-y-auto bg-[#0A0A0A]"
      style={{ scrollSnapType: 'y mandatory' }}
    >
      <GridBackground />
      <LandingNav onEnterApp={onEnterApp} />

      <HeroSection onEnterApp={onEnterApp} />
      <MarqueeSection />
      <ProblemSection />
      <HowItWorksSection />
      <ArchitectureSection />
      <CTASection onEnterApp={onEnterApp} />
    </div>
  );
};

export default LandingPage;
