
import React, { useState, useEffect, useCallback } from 'react';
import type { Candidate } from './types';
import { fetchCandidateNames, fetchCandidateDetails } from './services/geminiService';
import Header from './components/Header';
import CandidateCard from './components/CandidateCard';
import LoadingSpinner from './components/LoadingSpinner';
import Footer from './components/Footer';

const App: React.FC = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingMessage, setLoadingMessage] = useState<string>("Initializing research...");

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setLoadingMessage("Identifying top 10 Democratic hopefuls...");
      const names = await fetchCandidateNames();
      if (names.length === 0) {
        setError("Could not identify any candidates. Please try again later.");
        setIsLoading(false);
        return;
      }

      setLoadingMessage(`Found ${names.length} candidates. Compiling profiles...`);
      const candidateDetailsPromises = names.map(name => fetchCandidateDetails(name));
      const candidateDetails = await Promise.all(candidateDetailsPromises);
      
      setCandidates(candidateDetails);
    } catch (e) {
      console.error(e);
      setError("An error occurred while fetching candidate data. This could be due to API restrictions or a network issue.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="text-center">
          <LoadingSpinner />
          <p className="mt-4 text-lg text-gray-300 animate-pulse">{loadingMessage}</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="text-center text-red-400 bg-red-900/20 p-6 rounded-lg">
          <h2 className="text-2xl font-bold">Error</h2>
          <p className="mt-2">{error}</p>
          <button 
            onClick={loadData}
            className="mt-4 px-6 py-2 bg-brand-blue text-white font-semibold rounded-lg hover:bg-blue-500 transition-colors"
          >
            Retry
          </button>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
        {candidates.map((candidate, index) => (
          <CandidateCard key={candidate.name} candidate={candidate} index={index} />
        ))}
      </div>
    );
  };
  
  return (
    <div className="min-h-screen bg-gray-900 font-sans">
      <Header />
      <main className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {renderContent()}
      </main>
      <Footer />
    </div>
  );
};

export default App;
