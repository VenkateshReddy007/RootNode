import React from 'react';
import { Cloud } from 'lucide-react';

const Navbar = () => {
  return (
    <nav className="bg-brand-dark text-white font-sans px-6 py-4 flex items-center justify-between border-b border-brand-orange/30">
      <div className="flex items-center gap-3">
        <Cloud className="text-brand-orange w-7 h-7" />
        <span className="font-bold text-xl tracking-wide">RootNode Migration Planner</span>
      </div>
      
      <div className="flex items-center">
        <span className="px-4 py-1.5 text-xs font-bold text-brand-orange bg-brand-orange/10 border border-brand-orange/50 rounded-full shadow-[0_0_12px_rgba(255,153,0,0.4)] tracking-wider uppercase">
          AI Powered
        </span>
      </div>
    </nav>
  );
};

export default Navbar;
