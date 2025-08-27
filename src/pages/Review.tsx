import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, BarChart3, MessageCircle, Trophy, Target, Brain } from 'lucide-react';
import { useAssessments } from '../context/AssessmentContext';

export const Review: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getAssessment } = useAssessments();
  const [activeTab, setActiveTab] = useState<'results' | 'questions'>('results');
  const [selectedQuestion, setSelectedQuestion] = useState<number>(1);

  const assessment = id ? getAssessment(id) : null;

  if (!assessment) {
    return (
      <div className="text-center py-20">
        <div className="mx-auto w-32 h-32 bg-gradient-to-br from-red-100 to-pink-100 rounded-full flex items-center justify-center mb-8 shadow-lg">
          <Target className="w-16 h-16 text-red-600" />
        </div>
        <h3 className="text-2xl font-bold text-slate-900 mb-4">Assessment not found</h3>
        <p className="text-slate-600 mb-8 max-w-md mx-auto leading-relaxed">
          The assessment you're looking for doesn't exist or has been removed.
        </p>
        <Link
          to="/"
          className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  if (assessment.status !== 'complete' || !assessment.results) {
    return (
      <div className="text-center py-20">
        <div className="mx-auto w-32 h-32 bg-gradient-to-br from-amber-100 to-orange-100 rounded-full flex items-center justify-center mb-8 shadow-lg">
          <Brain className="w-16 h-16 text-amber-600" />
        </div>
        <h3 className="text-2xl font-bold text-slate-900 mb-4">Assessment in Progress</h3>
        <p className="text-slate-600 mb-8 max-w-md mx-auto leading-relaxed">
          Your assessment is still being processed by our AI models. Please check back in a few moments.
        </p>
        <Link
          to="/"
          className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Dashboard
        </Link>
      </div>
    );
  }

  const { results } = assessment;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-slate-600 hover:text-slate-900 mb-6 transition-all duration-200 hover:scale-105"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Dashboard
        </button>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-500 rounded-2xl flex items-center justify-center shadow-lg">
              <Trophy className="w-8 h-8 text-white" />
            </div>
            <div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">
                {assessment.name}
              </h2>
              <p className="text-slate-600 mt-1">Assessment completed on {assessment.date}</p>
            </div>
          </div>
          <div className="flex items-center space-x-4 text-sm">
            <div className="bg-white/80 backdrop-blur-sm px-4 py-2 rounded-lg shadow-md">
              <span className="text-slate-600">Models:</span>
              <span className="font-semibold text-slate-900 ml-1">{assessment.selectedModels.length}</span>
            </div>
            <div className="bg-white/80 backdrop-blur-sm px-4 py-2 rounded-lg shadow-md">
              <span className="text-slate-600">Iterations:</span>
              <span className="font-semibold text-slate-900 ml-1">{assessment.iterations}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50 overflow-hidden">
        <div className="border-b border-slate-200/60">
          <nav className="flex">
            <button
              onClick={() => setActiveTab('results')}
              className={`flex items-center px-6 py-4 text-sm font-semibold transition-all duration-200 ${
                activeTab === 'results'
                  ? 'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border-b-2 border-blue-500'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50/50'
              }`}
            >
              <BarChart3 className="w-5 h-5 mr-2" />
              Performance Results
            </button>
            <button
              onClick={() => setActiveTab('questions')}
              className={`flex items-center px-6 py-4 text-sm font-semibold transition-all duration-200 ${
                activeTab === 'questions'
                  ? 'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border-b-2 border-blue-500'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50/50'
              }`}
            >
              <MessageCircle className="w-5 h-5 mr-2" />
              Question Analysis
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'results' && (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      AI Model
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      &lt;100% Discrepancies
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      &lt;100% Question Discrepancies
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Z P F Discrepancies
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Z P F Question Discrepancies
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Range Discrepancies
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Range Question Discrepancies
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      AI Total Score
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {results.modelResults.map((modelResult, modelIndex) => (
                    <React.Fragment key={modelResult.model}>
                      {/* Average row */}
                      <tr className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/60">
                        <td className="px-6 py-4 font-bold text-slate-900">
                          <div className="flex items-center">
                            <div className="w-3 h-3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full mr-3"></div>
                            {modelResult.model} (Average)
                          </div>
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {modelResult.averages.discrepancies100}%
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {modelResult.averages.questionDiscrepancies100}%
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {modelResult.averages.zpfDiscrepancies}%
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {modelResult.averages.zpfQuestionDiscrepancies}%
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {modelResult.averages.rangeDiscrepancies}%
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {modelResult.averages.rangeQuestionDiscrepancies}%
                        </td>
                        <td className="px-6 py-4 font-semibold text-green-700">
                          {modelResult.averages.totalScore}%
                        </td>
                      </tr>
                      {/* Individual attempt rows */}
                      {modelResult.attempts.map((attempt, attemptIndex) => (
                        <tr 
                          key={`${modelIndex}-${attemptIndex}`} 
                          className={`hover:bg-slate-50/50 transition-colors ${
                            attemptIndex % 2 === 0 ? 'bg-white/60' : 'bg-slate-50/60'
                          }`}
                        >
                          <td className="px-6 py-3 text-sm text-slate-600 pl-12">
                            Attempt {attempt.attemptNumber}
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {attempt.discrepancies100}%
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {attempt.questionDiscrepancies100}%
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {attempt.zpfDiscrepancies}%
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {attempt.zpfQuestionDiscrepancies}%
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {attempt.rangeDiscrepancies}%
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {attempt.rangeQuestionDiscrepancies}%
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {attempt.totalScore}%
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'questions' && (
            <div className="space-y-6">
              {/* Question Selector */}
              <div className="bg-gradient-to-r from-slate-50 to-blue-50 rounded-xl p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-3">
                  Select Question for Analysis
                </label>
                <select
                  value={selectedQuestion}
                  onChange={(e) => setSelectedQuestion(parseInt(e.target.value))}
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl bg-white/80 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {results.questions.map((question) => (
                    <option key={question.number} value={question.number}>
                      Q{question.number}: {question.text}
                    </option>
                  ))}
                </select>
              </div>

              {/* Question Feedback */}
              <div className="space-y-6">
                {results.modelResults.map((modelResult) => (
                  <div key={modelResult.model} className="bg-white/80 backdrop-blur-sm border border-white/60 rounded-xl p-6 shadow-lg">
                    <div className="flex items-center mb-4">
                      <div className="w-4 h-4 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full mr-3"></div>
                      <h4 className="text-lg font-bold text-slate-900">{modelResult.model}</h4>
                    </div>
                    <div className="grid gap-4">
                      {modelResult.attempts.map((attempt) => {
                        const questionFeedback = attempt.questionFeedback.find(
                          qf => qf.questionNumber === selectedQuestion
                        );
                        return questionFeedback ? (
                          <div key={attempt.attemptNumber} className="bg-gradient-to-r from-slate-50 to-blue-50/50 rounded-lg p-4 border border-slate-200/60">
                            <div className="flex justify-between items-center mb-3">
                              <span className="text-sm font-semibold text-slate-700 bg-white/70 px-3 py-1 rounded-full">
                                Attempt {attempt.attemptNumber}
                              </span>
                              <span className="text-sm font-bold text-blue-700 bg-blue-100 px-3 py-1 rounded-full">
                                {questionFeedback.mark}
                              </span>
                            </div>
                            <p className="text-sm text-slate-700 leading-relaxed">
                              {questionFeedback.feedback}
                            </p>
                          </div>
                        ) : null;
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};