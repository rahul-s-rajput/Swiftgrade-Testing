import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { GraduationCap, Plus } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const isReview = location.pathname.includes('/review');
  const isNewAssessment = location.pathname.includes('/new-assessment');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm shadow-sm border-b border-slate-200/60 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <Link to="/" className="flex items-center space-x-3 group transition-all duration-200 hover:scale-105">
              <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl shadow-lg group-hover:shadow-xl transition-all duration-200">
                <GraduationCap className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
                  SwiftGrade
                </h1>
                <p className="text-sm text-slate-500 font-medium">OpenRouter Testing</p>
              </div>
            </Link>
            
            <div className="flex items-center gap-3">
              {/* New Assessment */}
              <Link
                to="/new-assessment"
                className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-1"
              >
                <Plus className="w-4 h-4 mr-2" />
                New Assessment
              </Link>

              {/* Home Button */}
              <Link
                to="/"
                className="inline-flex items-center px-3 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                Home
              </Link>

              {/* Settings */}
              <Link
                to="/settings"
                className="inline-flex items-center px-3 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                Settings
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className={(isReview || isNewAssessment) ? "w-full px-4 sm:px-6 lg:px-8 py-8" : "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
        {children}
      </main>
    </div>
  );
};