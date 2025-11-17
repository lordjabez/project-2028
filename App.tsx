import React, { useState, useEffect } from 'react';
import type { Candidate } from './types';
import { candidates as staticCandidates } from './data/candidates';
import Header from './components/Header';
import CandidateCard from './components/CandidateCard';
import Footer from './components/Footer';

const App: React.FC = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);

  useEffect(() => {
    // Shuffle candidates for random order on each load
    const shuffledCandidates = [...staticCandidates];
    for (let i = shuffledCandidates.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffledCandidates[i], shuffledCandidates[j]] = [shuffledCandidates[j], shuffledCandidates[i]];
    }
    setCandidates(shuffledCandidates);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 font-sans">
      <Header />
      <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
          {candidates.map((candidate, index) => (
            <CandidateCard key={candidate.name} candidate={candidate} index={index} />
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default App;