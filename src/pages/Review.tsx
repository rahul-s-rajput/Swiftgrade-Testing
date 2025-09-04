import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BarChart3, MessageCircle, Trophy, Target, Brain } from 'lucide-react';
import { useAssessments } from '../context/AssessmentContext';

export const Review: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getAssessment, loadAssessmentResults } = useAssessments();
  const [activeTab, setActiveTab] = useState<'results' | 'questions'>('results');
  const [selectedQuestion, setSelectedQuestion] = useState<string>('');
  const [isLoadingResults, setIsLoadingResults] = useState<boolean>(false);

  const assessment = id ? getAssessment(id) : null;

  // Helper: parse model instance IDs of the form `${name}_${index}_${level}`
  // Returns base model id, optional index, and reasoning level if present
  const parseModelInstance = (modelId: string): { base: string; index?: number; level?: 'none' | 'low' | 'medium' | 'high' | 'custom' } => {
    const m = modelId.match(/^(.*)_([0-9]+)_(none|low|medium|high|custom)$/i);
    if (m) {
      return { base: m[1], index: parseInt(m[2], 10), level: m[3].toLowerCase() as any };
    }
    return { base: modelId };
  };

  const capitalize = (s: string) => s ? s.charAt(0).toUpperCase() + s.slice(1) : s;

  // Build a human-readable label for a model, including reasoning info when available
  const formatModelLabel = (modelId: string): string => {
    const parsed = parseModelInstance(modelId);
    if (!parsed.level || parsed.index == null) return parsed.base;
    const rc = assessment?.reasoningBySelection?.[parsed.index];
    let reasonPart = '';
    if (parsed.level !== 'none') {
      if (parsed.level === 'custom') {
        const tokens = rc?.tokens;
        reasonPart = `Reasoning: Custom${tokens ? ` (${tokens} tokens)` : ''}`;
      } else {
        reasonPart = `Reasoning: ${capitalize(parsed.level)}`;
      }
    }
    return reasonPart ? `${parsed.base} — ${reasonPart}` : parsed.base;
  };

  // If session is complete but results missing, trigger a load with local skeleton
  useEffect(() => {
    if (assessment && assessment.status === 'complete' && !assessment.results && id) {
      setIsLoadingResults(true);
      (async () => {
        try { await loadAssessmentResults(id); } finally { setIsLoadingResults(false); }
      })();
    }
  }, [assessment, id, loadAssessmentResults]);

  // If results exist but are missing totalMaxMarks, fetch fresh stats/results with skeleton
  useEffect(() => {
    if (assessment && assessment.status === 'complete' && assessment.results && id) {
      if (!assessment.results.totalMaxMarks || assessment.results.totalMaxMarks <= 0) {
        setIsLoadingResults(true);
        (async () => {
          try { await loadAssessmentResults(id); } finally { setIsLoadingResults(false); }
        })();
      }
    }
  }, [assessment, id, loadAssessmentResults]);

  // Compute values derived from results in hooks that always run, even if results are not yet present.
  // This avoids calling hooks conditionally later.
  const totalQuestions = assessment?.results?.questions.length || 0;
  const totalMaxMarksRaw = assessment?.results?.totalMaxMarks || 0;
  const derivedTotalMaxFromFeedback = React.useMemo(() => {
    try {
      const firstModel = assessment?.results?.modelResults?.[0];
      const firstAttempt = firstModel?.attempts?.[0];
      const sum = (firstAttempt?.questionFeedback || [])
        .map(qf => {
          const parts = String(qf.mark || '').split('/');
          const maxStr = parts[1];
          const n = Number(maxStr);
          return Number.isFinite(n) ? n : 0;
        })
        .reduce((a, b) => a + b, 0);
      return sum > 0 ? sum : 0;
    } catch {
      return 0;
    }
  }, [assessment?.results]);
  const effectiveTotalMaxMarks = totalMaxMarksRaw > 0 ? totalMaxMarksRaw : derivedTotalMaxFromFeedback;

  const questionIds = React.useMemo(() => (
    (assessment?.results?.questions || []).map(q => q.text)
  ), [assessment?.results]);

  // Ensure selected question is valid after results load
  useEffect(() => {
    if (questionIds.length && !questionIds.includes(selectedQuestion)) {
      setSelectedQuestion(questionIds[0]);
    }
  }, [questionIds, selectedQuestion]);

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

  if (assessment.status !== 'complete') {
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

  if (!assessment.results) {
    return (
      <div className="text-center py-20">
        <div className="mx-auto w-32 h-32 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center mb-8 shadow-lg">
          <Brain className="w-16 h-16 text-blue-600" />
        </div>
        <h3 className="text-2xl font-bold text-slate-900 mb-4">Loading results...</h3>
        <p className="text-slate-600 mb-8 max-w-md mx-auto leading-relaxed">
          We are preparing your results. This typically takes a few seconds after grading completes.
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

  const fmtRatio = (numerator: number, denominator: number) => {
    const den = Number(denominator) || 0;
    if (den <= 0) return 'none';
    const numRaw = Number(numerator) || 0;
    const num = Math.round(numRaw);
    const pct = (numRaw / den) * 100;
    return `${num}/${den} (${pct.toFixed(2)}%)`;
  };

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
                    <th className="px-6 py-4 text-left text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Errors
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {isLoadingResults && (
                    <tr className="animate-pulse">
                      <td className="px-6 py-4" colSpan={9}>
                        <div className="space-y-3">
                          <div className="h-4 bg-slate-200 rounded w-1/3"></div>
                          <div className="h-3 bg-slate-200 rounded w-full"></div>
                          <div className="h-3 bg-slate-200 rounded w-5/6"></div>
                          <div className="h-3 bg-slate-200 rounded w-2/3"></div>
                        </div>
                      </td>
                    </tr>
                  )}
                  {results.modelResults.map((modelResult, modelIndex) => (
                    <React.Fragment key={modelResult.model}>
                      {/* Average row */}
                      <tr className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/60">
                        <td className="px-6 py-4 font-bold text-slate-900">
                          <div className="flex items-center">
                            <div className="w-3 h-3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full mr-3"></div>
                            {formatModelLabel(modelResult.model)} (Average)
                          </div>
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {fmtRatio(modelResult.averages.discrepancies100, totalQuestions)}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {/* Empty on purpose for average row */}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {fmtRatio(modelResult.averages.zpfDiscrepancies, totalQuestions)}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {/* Empty on purpose for average row */}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {fmtRatio(modelResult.averages.rangeDiscrepancies, totalQuestions)}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {/* Empty on purpose for average row */}
                        </td>
                        <td className="px-6 py-4 font-semibold text-green-700">
                          {fmtRatio(modelResult.averages.totalScore, effectiveTotalMaxMarks)}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-900">{/* empty for average */}</td>
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
                            <div className="flex flex-col">
                              <span>Attempt {attempt.attemptNumber}</span>
                              {attempt.failureReasons && attempt.failureReasons.length > 0 && (
                                <span className="mt-1 inline-block text-xs text-red-700 bg-red-100 rounded px-2 py-0.5">
                                  Failed: {attempt.failureReasons[0]}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {fmtRatio(attempt.discrepancies100, totalQuestions)}
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {(attempt.lt100Questions || []).map(qid => {
                              const q = results.questions.find(q => q.text === qid);
                              return q?.text || qid;
                            }).join(', ') || 'none'}
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {fmtRatio(attempt.zpfDiscrepancies, totalQuestions)}
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {(attempt.zpfQuestions || []).map(qid => {
                              const q = results.questions.find(q => q.text === qid);
                              return q?.text || qid;
                            }).join(', ') || 'none'}
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {fmtRatio(attempt.rangeDiscrepancies, totalQuestions)}
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {(attempt.rangeQuestions || []).map(qid => {
                              const q = results.questions.find(q => q.text === qid);
                              return q?.text || qid;
                            }).join(', ') || 'none'}
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {fmtRatio(attempt.totalScore, effectiveTotalMaxMarks)}
                          </td>
                          <td className="px-6 py-3 text-sm text-slate-900">
                            {attempt.failureReasons && attempt.failureReasons.length > 0 ? (
                              <div className="text-red-700">
                                {attempt.failureReasons.slice(0, 2).join('; ')}{attempt.failureReasons.length > 2 ? '…' : ''}
                              </div>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
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
              {/* Question Navigator */}
              <div className="bg-gradient-to-r from-slate-50 to-blue-50 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-semibold text-slate-700">Select Question for Analysis</h3>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      aria-label="Previous question"
                      onClick={() => {
                        const idx = questionIds.indexOf(selectedQuestion);
                        const prevIdx = Math.max(0, idx - 1);
                        const nextVal = questionIds[prevIdx] ?? selectedQuestion;
                        setSelectedQuestion(nextVal);
                      }}
                      className="inline-flex items-center px-3 py-2 rounded-lg border border-slate-300 text-slate-700 bg-white/80 hover:bg-slate-50 disabled:opacity-50"
                      disabled={questionIds.indexOf(selectedQuestion) <= 0}
                    >
                      <ArrowLeft className="w-4 h-4" />
                    </button>
                    <div className="text-xs text-slate-600 min-w-[150px] text-center">
                      {results.questions.find(q => q.text === selectedQuestion)?.text || `Question ${Math.max(1, questionIds.indexOf(selectedQuestion) + 1)}`} ({Math.max(1, questionIds.indexOf(selectedQuestion) + 1)} of {questionIds.length})
                    </div>
                    <button
                      type="button"
                      aria-label="Next question"
                      onClick={() => {
                        const idx = questionIds.indexOf(selectedQuestion);
                        const nextIdx = Math.min(questionIds.length - 1, idx + 1);
                        const nextVal = questionIds[nextIdx] ?? selectedQuestion;
                        setSelectedQuestion(nextVal);
                      }}
                      className="inline-flex items-center px-3 py-2 rounded-lg border border-slate-300 text-slate-700 bg-white/80 hover:bg-slate-50 disabled:opacity-50"
                      disabled={questionIds.indexOf(selectedQuestion) >= questionIds.length - 1}
                    >
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {questionIds.map((qid, idx) => {
                    const isActive = qid === selectedQuestion;
                    const q = results.questions.find(q => q.text === qid);
                    return (
                      <button
                        key={qid}
                        type="button"
                        onClick={() => setSelectedQuestion(qid)}
                        className={`px-3 py-2 rounded-lg border text-sm transition-all ${
                          isActive
                            ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                            : 'bg-white/80 text-slate-700 border-slate-300 hover:bg-slate-50'
                        }`}
                        aria-current={isActive ? 'true' : undefined}
                        aria-label={`Select question ${q?.text || qid}`}
                      >
                        {q?.text || `Q${idx + 1}`}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Question Feedback */}
              <div className="space-y-6">
                {isLoadingResults && (
                  <div className="animate-pulse space-y-4">
                    <div className="h-6 bg-slate-200 rounded w-1/4"></div>
                    <div className="h-20 bg-slate-200 rounded"></div>
                    <div className="h-20 bg-slate-200 rounded"></div>
                  </div>
                )}
                {results.modelResults.map((modelResult) => (
                  <div key={modelResult.model} className="bg-white/80 backdrop-blur-sm border border-white/60 rounded-xl p-6 shadow-lg">
                    <div className="flex items-center mb-4">
                      <div className="w-4 h-4 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full mr-3"></div>
                      <h4 className="text-lg font-bold text-slate-900">{formatModelLabel(modelResult.model)}</h4>
                    </div>
                    <div className="grid gap-4">
                      {modelResult.attempts.map((attempt) => {
                        const questionFeedback = attempt.questionFeedback.find(
                          qf => qf.questionId === selectedQuestion
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
                        ) : (
                          attempt.failureReasons && attempt.failureReasons.length > 0 ? (
                            <div key={attempt.attemptNumber} className="bg-red-50 rounded-lg p-4 border border-red-200/70">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-sm font-semibold text-red-800 bg-white/70 px-3 py-1 rounded-full">
                                  Attempt {attempt.attemptNumber} failed
                                </span>
                              </div>
                              <ul className="list-disc pl-5 text-sm text-red-800 space-y-1">
                                {attempt.failureReasons.slice(0, 3).map((r, idx) => (
                                  <li key={idx}>{r}</li>
                                ))}
                              </ul>
                            </div>
                          ) : null
                        );
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