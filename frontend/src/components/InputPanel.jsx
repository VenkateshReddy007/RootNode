import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const InputPanel = ({ onAnalyze, isLoading }) => {
  const [csvText, setCsvText] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const placeholderText = `Application,DependsOn,Criticality,DataSize,Priority,Complexity
AppA,AppB,Yes,500,High,High
AppB,AppC,No,200,Medium,Low
AppC,,No,100,Low,Medium`;

  return (
    <div className="relative w-full max-w-3xl mx-auto mt-8">
      {/* Aceternity UI style animated glow on focus */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: isFocused ? 1 : 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="absolute -inset-0.5 bg-gradient-to-r from-brand-orange/40 to-brand-orange/10 blur-xl rounded-2xl z-0 pointer-events-none"
      />
      
      {/* Main Card Context */}
      <div className="relative z-10 bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl flex flex-col gap-5">
        <h2 className="text-white text-xl font-bold tracking-wide">
          Upload Application Portfolio
        </h2>
        
        <textarea
          value={csvText}
          onChange={(e) => setCsvText(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholderText}
          className="w-full h-56 bg-brand-dark text-gray-200 placeholder-gray-500 border border-brand-border rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-brand-orange focus:border-transparent resize-y font-mono text-sm leading-relaxed transition-all shadow-inner"
        />
        
        <button
          onClick={() => onAnalyze(csvText)}
          disabled={isLoading || !csvText.trim()}
          className="w-full bg-brand-orange hover:bg-[#FFAA33] disabled:opacity-60 disabled:cursor-not-allowed text-black font-bold py-3.5 rounded-lg flex items-center justify-center transition-all duration-200 active:scale-[0.98]"
        >
          {isLoading ? (
            <>
              <Loader2 className="animate-spin mr-2 w-5 h-5 text-black" />
              Processing Data...
            </>
          ) : (
            'Analyze Migration'
          )}
        </button>
      </div>
    </div>
  );
};

export default InputPanel;
