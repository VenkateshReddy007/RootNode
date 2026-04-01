import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

const TypewriterText = ({ text }) => {
  const paragraphs = text.split('\n');

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        visible: { transition: { staggerChildren: 0.015 } },
      }}
      className="flex flex-col gap-4"
    >
      {paragraphs.map((line, pIndex) => (
        <p key={pIndex} className="text-white leading-relaxed text-[15px]">
          {line.split('').map((char, cIndex) => (
            <motion.span
              key={`${pIndex}-${cIndex}`}
              variants={{
                hidden: { opacity: 0 },
                visible: { opacity: 1 },
              }}
            >
              {char}
            </motion.span>
          ))}
        </p>
      ))}
    </motion.div>
  );
};

const LoadingSkeleton = () => (
  <div className="flex flex-col gap-3 animate-pulse mt-2">
    <div className="h-4 bg-brand-border rounded-md w-11/12" />
    <div className="h-4 bg-brand-border rounded-md w-full" />
    <div className="h-4 bg-brand-border rounded-md w-5/6" />
    <div className="h-4 bg-brand-border rounded-md w-3/4" />
  </div>
);

const AIPanel = ({ explanation }) => {
  return (
    <div className="relative rounded-2xl overflow-hidden p-[1px] shadow-[0_0_20px_rgba(255,153,0,0.2)]">
      {/* Animated Rotating Gradient Border */}
      <div className="absolute -inset-[150%] animate-[spin_3s_linear_infinite] bg-[conic-gradient(from_90deg_at_50%_50%,#FF9900_0%,transparent_20%,transparent_100%)] pointer-events-none" />

      {/* Inner Content Card */}
      <div className="relative z-10 w-full bg-brand-card rounded-[15px] p-6 shadow-2xl flex flex-col gap-4 min-h-[160px]">
        
        {/* Header */}
        <div>
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-5 h-5 text-brand-orange" />
            <h2 className="text-white text-xl font-bold tracking-wide">
              AI Migration Analysis
            </h2>
          </div>
          <p className="text-brand-orange text-xs font-semibold mt-1 tracking-wider uppercase ml-7">
            Powered by Amazon Bedrock
          </p>
        </div>

        {/* Dynamic Explanation Content vs Loading State */}
        <div className="mt-1 ml-7">
          {!explanation ? (
            <LoadingSkeleton />
          ) : (
            <TypewriterText text={explanation} />
          )}
        </div>
      </div>
    </div>
  );
};

export default AIPanel;
