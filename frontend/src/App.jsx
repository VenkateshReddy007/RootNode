import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SignedIn, SignedOut, SignIn, useUser } from '@clerk/clerk-react';

import LandingPage from './components/LandingPage';
import Navbar from './components/Navbar';
import InputPanel from './components/InputPanel';
import WavesView from './components/WavesView';
import GraphView from './components/GraphView';
import RiskTable from './components/RiskTable';
import GanttChart from './components/GanttChart';
import AIPanel from './components/AIPanel';

import { MOCK_DATA } from './data/mock';

function App() {
  const { isSignedIn, isLoaded } = useUser();
  // If user is already signed in, skip landing and go straight to the planner
  const [showLanding, setShowLanding] = useState(true);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAnalyze = (csvText) => {
    setIsLoading(true);
    setResult(null);

    // Simulate 2-second API delay — will be replaced with real API call
    setTimeout(() => {
      setResult(MOCK_DATA);
      setIsLoading(false);
    }, 2000);
  };

  /* ── Wait for Clerk to resolve auth — prevents flash of landing page ── */
  if (!isLoaded) {
    return <div className="min-h-screen bg-[#0A0A0A]" />;
  }

  /* ── Landing page — only show to unauthenticated visitors ── */
  if (showLanding && !isSignedIn) {
    return <LandingPage onEnterApp={() => setShowLanding(false)} />;
  }

  /* ── Main planner app ── */
  return (
    <>
      <SignedIn>
        <div className="min-h-screen bg-brand-dark text-white font-sans">
          {/* Navbar */}
          <Navbar />

          {/* Main Content */}
          <main className="px-8 py-6">
            {/* Input Panel — centered */}
            <div className="max-w-[700px] mx-auto">
              <InputPanel onAnalyze={handleAnalyze} isLoading={isLoading} />
            </div>

            {/* Results Section */}
            <AnimatePresence>
              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.6, ease: 'easeOut' }}
                  className="mt-10 flex flex-col gap-8 max-w-7xl mx-auto"
                >
                  {/* 1. Migration Waves — full width */}
                  <WavesView
                    waves={result.waves}
                    risk={result.risk}
                    strategy={result.strategy}
                  />

                  {/* 2. Dependency Graph — full width */}
                  <div className="h-[500px]">
                    <GraphView
                      waves={result.waves}
                      dependencies={result.dependencies}
                    />
                  </div>

                  {/* 3. Two-column grid: Risk Table + Gantt Chart */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <RiskTable
                      risk={result.risk}
                      strategy={result.strategy}
                      timeline={result.timeline}
                    />
                    <GanttChart
                      waves={result.waves}
                      timeline={result.timeline}
                    />
                  </div>

                  {/* 4. AI Panel — full width */}
                  <AIPanel explanation={result.explanation} />
                </motion.div>
              )}
            </AnimatePresence>
          </main>
        </div>
      </SignedIn>

      <SignedOut>
        <div className="min-h-screen bg-[#0F0F0F] flex items-center justify-center">
          <div className="shadow-[0_0_30px_rgba(255,153,0,0.15)] rounded-2xl">
            <SignIn 
              routing="hash" 
              appearance={{
                elements: {
                  card: 'bg-[#111111] border border-[#2A2A2A]',
                  headerTitle: 'text-white',
                  headerSubtitle: 'text-gray-400',
                  socialButtonsBlockButton: 'bg-[#1A1A1A] text-white border border-[#2A2A2A] hover:bg-[#222]',
                  socialButtonsBlockButtonText: 'text-white font-semibold',
                  dividerLine: 'bg-[#2A2A2A]',
                  dividerText: 'text-gray-500',
                  formFieldLabel: 'text-gray-300',
                  formFieldInput: 'bg-[#1A1A1A] border-[#2A2A2A] text-white focus:border-[#FF9900]',
                  formButtonPrimary: 'bg-[#FF9900] hover:bg-[#ffaa33] text-black font-bold',
                  footerActionText: 'text-gray-400',
                  footerActionLink: 'text-[#FF9900] hover:text-[#ffaa33]'
                }
              }}
            />
          </div>
        </div>
      </SignedOut>
    </>
  );
}

export default App;
