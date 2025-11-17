
import React from 'react';

const Header: React.FC = () => {
  return (
    <header className="bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10 shadow-lg shadow-gray-900/50">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="text-center animate-fade-in">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-white">
            <span className="bg-gradient-to-r from-brand-blue via-blue-400 to-gray-200 bg-clip-text text-transparent">Project</span>
            <span className="mx-2 text-gray-400">/</span>
            <span className="bg-gradient-to-r from-gray-200 via-red-400 to-brand-red bg-clip-text text-transparent">2028</span>
          </h1>
          <p className="mt-2 text-lg text-gray-400">
            An AI-Powered Look at Potential Democratic Hopefuls
          </p>
        </div>
      </div>
    </header>
  );
};

export default Header;
