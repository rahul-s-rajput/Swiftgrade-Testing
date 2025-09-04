import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Loader2, CheckCircle, Trash2, Eye, Calendar, Cpu, RotateCcw, AlertTriangle } from 'lucide-react';
import { useAssessments } from '../context/AssessmentContext';

export const Home: React.FC = () => {
  const { assessments, deleteAssessment, refreshSessions, retryAssessment, loading } = useAssessments();
  const [refreshing, setRefreshing] = useState(false);

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this assessment?')) {
      deleteAssessment(id);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    const start = Date.now();
    try {
      await refreshSessions();
      const elapsed = Date.now() - start;
      if (elapsed < 1000) {
        await new Promise(res => setTimeout(res, 1000 - elapsed));
      }
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-8 animate-pulse">
        <div className="h-10 w-64 bg-slate-200 rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[0,1,2].map(i => (
            <div key={i} className="bg-white/70 rounded-2xl p-6 shadow-lg border border-white/50">
              <div className="h-6 w-32 bg-slate-200 rounded mb-4" />
              <div className="h-8 w-20 bg-slate-200 rounded" />
            </div>
          ))}
        </div>
        <div className="bg-white/70 shadow-xl rounded-2xl border border-white/50 p-8 flex items-center justify-center">
          <div className="flex items-center text-slate-600">
            <Loader2 className="w-6 h-6 animate-spin mr-3" />
            <span className="font-medium">Loading assessments…</span>
          </div>
        </div>
      </div>
    );
  }

  if (assessments.length === 0) {
    return (
      <div className="text-center py-20">
        <div className="mx-auto w-32 h-32 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center mb-8 shadow-lg">
          <Plus className="w-16 h-16 text-blue-600" />
        </div>
        <h3 className="text-2xl font-bold text-slate-900 mb-4">No assessments yet</h3>
        <p className="text-slate-600 mb-8 max-w-md mx-auto leading-relaxed">
          Create your first assessment to start testing AI models on grading performance!
        </p>
        <Link
          to="/new-assessment"
          className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-1"
        >
          <Plus className="w-5 h-5 mr-2" />
          Create Your First Assessment
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">
            Assessment Dashboard
          </h2>
          <p className="text-slate-600 mt-2 leading-relaxed">
            Monitor your AI grading tests and analyze performance results
          </p>
        </div>
        <div className="flex items-center">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center px-4 py-3 bg-slate-100 text-slate-800 font-medium rounded-xl hover:bg-slate-200 transition-colors border border-slate-200 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Refresh Sessions"
          >
            {refreshing ? (
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
            ) : (
              <RotateCcw className="w-5 h-5 mr-2" />
            )}
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      
      {/* Assessments Table */}
      <div className="bg-white/70 backdrop-blur-sm shadow-xl rounded-2xl overflow-hidden border border-white/50">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-slate-50/80">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Assessment Details
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Configuration
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/60">
              {assessments.map((assessment, index) => (
                <tr key={assessment.id} className={`hover:bg-slate-50/50 transition-colors ${
                  index % 2 === 0 ? 'bg-white/40' : 'bg-slate-50/40'
                }`}>
                  <td className="px-6 py-6">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-lg flex items-center justify-center">
                          <span className="text-white font-bold text-sm">
                            {assessment.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      </div>
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-slate-900">{assessment.name}</h4>
                        <div className="flex items-center mt-1 text-sm text-slate-600">
                          <Calendar className="w-4 h-4 mr-1" />
                          {assessment.date}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-6">
                    <div className="space-y-2">
                      <div className="flex items-center text-sm">
                        <Cpu className="w-4 h-4 mr-2 text-slate-500" />
                        <span className="text-slate-700 font-medium">{assessment.selectedModels.length}</span>
                        <span className="text-slate-600 ml-1">model{assessment.selectedModels.length !== 1 ? 's' : ''}</span>
                      </div>
                      <div className="flex items-center text-sm">
                        <RotateCcw className="w-4 h-4 mr-2 text-slate-500" />
                        <span className="text-slate-700 font-medium">{assessment.iterations}</span>
                        <span className="text-slate-600 ml-1">iteration{assessment.iterations !== 1 ? 's' : ''}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-6">
                    <div className="flex items-center">
                      {assessment.status === 'running' && (
                        <div className="flex items-center px-3 py-1 bg-amber-100 text-amber-800 rounded-full">
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          <span className="text-sm font-medium">Processing</span>
                        </div>
                      )}
                      {assessment.status === 'complete' && (
                        <div className="flex items-center px-3 py-1 bg-green-100 text-green-800 rounded-full">
                          <CheckCircle className="w-4 h-4 mr-2" />
                          <span className="text-sm font-medium">Complete</span>
                        </div>
                      )}
                      {assessment.status === 'failed' && (
                        <div className="flex items-center px-3 py-1 bg-red-100 text-red-800 rounded-full">
                          <AlertTriangle className="w-4 h-4 mr-2" />
                          <span className="text-sm font-medium">Failed</span>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-6">
                    <div className="flex items-center space-x-3">
                      {assessment.status === 'complete' && (
                        <Link
                          to={`/review/${assessment.id}`}
                          className="p-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors"
                          title="View Results"
                        >
                          <Eye className="w-5 h-5" />
                        </Link>
                      )}
                      {assessment.status === 'failed' && (
                        <button
                          onClick={() => void retryAssessment(assessment.id)}
                          className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
                          title="Retry Grading"
                        >
                          <RotateCcw className="w-5 h-5" />
                        </button>
                      )}
                      <button
                        onClick={(e) => handleDelete(assessment.id, e)}
                        className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete Assessment"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};