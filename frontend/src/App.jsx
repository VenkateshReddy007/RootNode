import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SignedIn, SignedOut, SignIn, useUser } from '@clerk/clerk-react';
import axios from 'axios';

import LandingPage from './components/LandingPage';
import Navbar from './components/Navbar';
import InputPanel from './components/InputPanel';
import WavesView from './components/WavesView';
import GraphView from './components/GraphView';
import RiskTable from './components/RiskTable';
import GanttChart from './components/GanttChart';
import AIPanel from './components/AIPanel';
import RiskHeatmap from './components/RiskHeatmap';

const API_URL =
  import.meta.env.VITE_API_URL ||
  'https://zztl0gdz8i.execute-api.ap-south-2.amazonaws.com';

/* ── CSV parser: header row → array of objects ── */
function parseCSV(csvText) {
  const lines = csvText.trim().split('\n').filter(Boolean);
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const vals = line.split(',').map((v) => v.trim());
    return headers.reduce((obj, h, i) => ({ ...obj, [h]: vals[i] ?? '' }), {});
  });
}

function App() {
  const { isSignedIn, isLoaded } = useUser();
  const [showLanding, setShowLanding] = useState(true);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState(null); // { message, type }

  const showToast = (message, type = 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleAnalyze = async (csvText) => {
    setIsLoading(true);
    setResult(null);

    const data = parseCSV(csvText);
    if (data.length === 0) {
      showToast('Analysis failed — check your CSV format');
      setIsLoading(false);
      return;
    }

    try {
      const response = await axios.post(`${API_URL}/analyze`, { data });
      setResult(response.data);
    } catch (err) {
      console.error('API error:', err);
      showToast(
        err?.response?.data?.message ||
        'Analysis failed — check your CSV format'
      );
    } finally {
      setIsLoading(false);
    }
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

          {/* Toast Notification */}
          <AnimatePresence>
            {toast && (
              <motion.div
                initial={{ opacity: 0, y: 50, x: '-50%' }}
                animate={{ opacity: 1, y: 0, x: '-50%' }}
                exit={{ opacity: 0, y: 20, x: '-50%' }}
                className="fixed bottom-10 left-1/2 z-[100] px-6 py-3 rounded-full shadow-2xl border flex items-center gap-3 backdrop-blur-md"
                style={{
                  backgroundColor: toast.type === 'error' ? 'rgba(239, 68, 68, 0.9)' : 'rgba(34, 197, 94, 0.9)',
                  borderColor: toast.type === 'error' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(34, 197, 94, 0.4)',
                }}
              >
                <span className="text-white font-bold text-sm tracking-wide">
                  {toast.type === 'error' ? '❌' : '✅'} {toast.message}
                </span>
              </motion.div>
            )}
          </AnimatePresence>

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
                      risk={result.risk}
                      strategy={result.strategy}
                      timeline={result.timeline}
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

                  {/* 4. Risk Heatmap — full width */}
                  <RiskHeatmap
                    risk={result.risk}
                    strategy={result.strategy}
                    timeline={result.timeline}
                  />

                  {/* 5. AI Panel — full width */}
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
