
import React from 'react';
import type { Candidate } from '../types';

interface CandidateCardProps {
  candidate: Candidate;
  index: number;
}

const QuoteIcon: React.FC<{ className?: string }> = ({ className }) => (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M6.5 10c-1.104 0-2 .896-2 2s.896 2 2 2 2-.896 2-2-.896-2-2-2zm11 0c-1.104 0-2 .896-2 2s.896 2 2 2 2-.896 2-2-.896-2-2-2zM12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 18c-4.411 0-8-3.589-8-8s3.589-8 8-8 8 3.589 8 8-3.589 8-8 8z"></path>
    </svg>
);


const CandidateCard: React.FC<CandidateCardProps> = ({ candidate, index }) => {
  const animationDelay = `${index * 100}ms`;

  return (
    <div 
      className="bg-gray-800/50 rounded-xl shadow-lg overflow-hidden border border-gray-700 hover:border-brand-blue transition-all duration-300 transform hover:-translate-y-1 animate-slide-up"
      style={{ animationDelay }}
    >
      <div className="relative">
        <img 
          className="w-full h-56 object-cover object-center" 
          src={`https://picsum.photos/seed/${encodeURIComponent(candidate.name)}/600/400`} 
          alt={candidate.photoDescription}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-gray-900/60 to-transparent"></div>
        <div className="absolute bottom-0 left-0 p-4">
          <h2 className="text-3xl font-bold text-white">{candidate.name}</h2>
          <p className="text-sm text-gray-400 italic">{candidate.photoDescription}</p>
        </div>
      </div>
      <div className="p-6 space-y-6">
        <div>
          <h3 className="text-lg font-semibold text-brand-blue/90 border-b-2 border-brand-blue/30 pb-2 mb-2">Biography</h3>
          <p className="text-gray-300 leading-relaxed">{candidate.bio}</p>
        </div>
        
        <div>
          <h3 className="text-lg font-semibold text-brand-blue/90 border-b-2 border-brand-blue/30 pb-2 mb-2">Recent Headlines</h3>
          <ul className="space-y-2 list-disc list-inside text-gray-300">
            {candidate.headlines.map((headline, i) => (
              <li key={i}>{headline}</li>
            ))}
          </ul>
        </div>
        
        <div>
          <h3 className="text-lg font-semibold text-brand-blue/90 border-b-2 border-brand-blue/30 pb-2 mb-2">Notable Quotes</h3>
          <div className="space-y-4">
            {candidate.quotes.map((quote, i) => (
              <blockquote key={i} className="relative p-4 bg-gray-900/50 rounded-lg border-l-4 border-gray-600">
                 <p className="italic text-gray-300">"{quote}"</p>
              </blockquote>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CandidateCard;
