import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BarChart3, MessageCircle, Trophy, Target, Brain, Info } from 'lucide-react';
import { useAssessments } from '../context/AssessmentContext';
import { getRubricResults } from '../utils/api';  // NEW: Import rubric results API

export const Review: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getAssessment, loadAssessmentResults } = useAssessments();
  const [activeTab, setActiveTab] = useState<'results' | 'questions'>('results');
  const [questionTab, setQuestionTab] = useState<'both' | 'rubric' | 'feedback'>('both');  // NEW: Sub-tabs for questions
  const [selectedQuestion, setSelectedQuestion] = useState<string>('');
  const [isLoadingResults, setIsLoadingResults] = useState<boolean>(false);
  const [rubricResults, setRubricResults] = useState<any>(null);  // NEW: Store rubric results
  const [hoveredAttempt, setHoveredAttempt] = useState<string | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<'above' | 'below'>('below');
  const tooltipRef = useRef<HTMLDivElement>(null);
  const iconRef = useRef<HTMLDivElement>(null);

  const assessment = id ? getAssessment(id) : null;

  // Debug: Log assessment modelPairs when component loads
  useEffect(() => {
    if (assessment) {
      console.log('[Review] Assessment loaded:', {
        id: assessment.id,
        hasModelPairs: !!assessment.modelPairs,
        modelPairsCount: assessment.modelPairs?.length,
        modelPairs: assessment.modelPairs
      });
    }
  }, [assessment?.id]);

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

  // Helper to get reasoning label from ReasoningConfig
  const getReasoningLabel = (reasoning?: { level?: string; effort?: string; tokens?: number; exclude?: boolean }): string => {
    if (!reasoning) return '';
    // Handle 'exclude' flag (means no reasoning)
    if (reasoning.exclude === true) return '';
    // Handle both 'level' and 'effort' field names
    const levelValue = reasoning.level || reasoning.effort;
    if (!levelValue || levelValue === 'none') return '';
    if (levelValue === 'custom') {
      return reasoning.tokens ? `Reasoning: Custom (${reasoning.tokens} tokens)` : 'Reasoning: Custom';
    }
    return `Reasoning: ${capitalize(levelValue)}`;
  };

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

  // Format rubric model with reasoning info
  const formatRubricModelLabel = (rubricModelId?: string, instanceId?: string): string => {
    if (!rubricModelId) return '';
    
    // Find the matching model pair using instanceId (unique) or fallback to model names
    const pair = assessment?.modelPairs?.find(
      p => instanceId ? p.instanceId === instanceId : (p.rubricModel === rubricModelId)
    );
    
    // Format rubric model with reasoning
    const rubricReason = getReasoningLabel(pair?.rubricReasoning);
    return rubricReason ? `${rubricModelId} — ${rubricReason}` : rubricModelId;
  };

  // Format model pair label with reasoning info
  const formatModelPairLabel = (rubricModelId?: string, assessmentModelId?: string, instanceId?: string): string => {
    if (!rubricModelId || !assessmentModelId) return '';
    
    console.log('[formatModelPairLabel] Looking for:', {
      instanceId,
      rubricModelId,
      assessmentModelId,
      availablePairs: assessment?.modelPairs?.map(p => ({
        instanceId: p.instanceId,
        rubricModel: p.rubricModel,
        assessmentModel: p.assessmentModel,
        rubricReasoning: p.rubricReasoning,
        assessmentReasoning: p.assessmentReasoning
      }))
    });
    
    // Find the matching model pair using instanceId (unique) or fallback to model names
    const pair = assessment?.modelPairs?.find(
      p => instanceId ? p.instanceId === instanceId : (p.rubricModel === rubricModelId && p.assessmentModel === assessmentModelId)
    );
    
    console.log('[formatModelPairLabel] Found pair:', pair);
    
    // Format rubric model with reasoning
    const rubricReason = getReasoningLabel(pair?.rubricReasoning);
    const rubricLabel = rubricReason ? `${rubricModelId} — ${rubricReason}` : rubricModelId;
    
    // Format assessment model with reasoning
    const assessmentReason = getReasoningLabel(pair?.assessmentReasoning);
    const assessmentLabel = assessmentReason ? `${assessmentModelId} — ${assessmentReason}` : assessmentModelId;
    
    return `${rubricLabel} → ${assessmentLabel}`;
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

  const questionIds = React.useMemo(() => {
    const ids = (assessment?.results?.questions || []).map(q => q.text);
    console.log('Question IDs from results:', ids);
    return ids;
  }, [assessment?.results]);

  // Ensure selected question is valid after results load
  useEffect(() => {
    console.log('Selected question effect - questionIds:', questionIds, 'selectedQuestion:', selectedQuestion);
    if (questionIds.length > 0 && (!selectedQuestion || !questionIds.includes(selectedQuestion))) {
      console.log('Setting selected question to:', questionIds[0]);
      setSelectedQuestion(questionIds[0] || '');
    }
  }, [questionIds]);

  // NEW: Fetch rubric results when assessment is complete and has results
  useEffect(() => {
    if (assessment && assessment.status === 'complete' && assessment.results && id) {
      // Only fetch if we haven't already or if assessment uses model pairs
      const hasModelPairs = assessment.results.modelResults.some(mr => mr.rubricModel || mr.assessmentModel);
      if (hasModelPairs && !rubricResults) {
        console.log('[Review] Fetching rubric results for session:', id);
        getRubricResults(id)
          .then(data => {
            console.log('[Review] Rubric results loaded:', data);
            setRubricResults(data);
          })
          .catch(err => {
            console.error('[Review] Failed to load rubric results:', err);
            // Non-fatal error, continue without rubric data
          });
      }
    }
  }, [assessment?.status, assessment?.results, id]);

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

  // Helper: Extract grading criteria for a specific question from full rubric response
  const extractQuestionCriteria = (rubricResponse: string, questionId: string): any | null => {
    try {
      // Try to parse as JSON
      const parsed = JSON.parse(rubricResponse);
      
      // Look for grading_criteria array
      if (parsed.grading_criteria && Array.isArray(parsed.grading_criteria)) {
        // Find the question by question_number or question_id
        const questionCriteria = parsed.grading_criteria.find(
          (q: any) => q.question_number === questionId || q.question_id === questionId
        );
        
        return questionCriteria || null;
      }
      
      // If not found or not in expected format, return null
      return null;
    } catch (e) {
      // If parsing fails, return null
      return null;
    }
  };

  // Component to render question criteria nicely
  const QuestionCriteriaDisplay: React.FC<{ criteria: any }> = ({ criteria }) => {
    if (!criteria) return null;
    
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-purple-300">
          <span className="font-bold text-purple-900">
            Question {criteria.question_number || criteria.question_id}
          </span>
          <span className="text-sm font-semibold text-purple-700 bg-purple-100 px-2 py-1 rounded">
            Max: {criteria.max_mark} marks
          </span>
        </div>
        
        {criteria.components && Array.isArray(criteria.components) && (
          <div className="space-y-3">
            {criteria.components.map((component: any, idx: number) => (
              <div key={idx} className="bg-white/50 rounded-lg p-3 border border-purple-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-slate-800">
                    {component.header || `Component ${idx + 1}`}
                  </span>
                  {component.marks !== null && component.marks !== undefined && (
                    <span className="text-xs font-medium text-purple-700 bg-purple-50 px-2 py-1 rounded">
                      {component.marks} marks
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {component.criteria || 'No criteria specified'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
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
              <span className="text-slate-600">
                {assessment.modelPairs && assessment.modelPairs.length > 0 ? 'Model Pairs:' : 'Models:'}
              </span>
              <span className="font-semibold text-slate-900 ml-1">
                {assessment.modelPairs && assessment.modelPairs.length > 0 
                  ? assessment.modelPairs.length 
                  : assessment.selectedModels.length}
              </span>
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
                            {modelResult.rubricModel && modelResult.assessmentModel
                              ? formatModelPairLabel(modelResult.rubricModel, modelResult.assessmentModel, modelResult.model)
                              : formatModelLabel(modelResult.model)} (Average)
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
                      {modelResult.attempts.map((attempt, attemptIndex) => {
                        const attemptKey = `${modelIndex}-${attemptIndex}`;
                        return (
                        <tr 
                          key={attemptKey} 
                          className={`hover:bg-slate-50/50 transition-colors relative ${
                            attemptIndex % 2 === 0 ? 'bg-white/60' : 'bg-slate-50/60'
                          }`}
                        >
                          <td className="px-6 py-3 text-sm text-slate-600 pl-12">
                            <div className="flex items-center gap-2">
                              <div className="flex flex-col">
                                <span>Attempt {attempt.attemptNumber}</span>
                                {attempt.failureReasons && attempt.failureReasons.length > 0 && (
                                  <span className="mt-1 inline-block text-xs text-red-700 bg-red-100 rounded px-2 py-0.5">
                                    Failed: {attempt.failureReasons[0]}
                                  </span>
                                )}
                              </div>
                              {attempt.tokenUsage && (
                                <div 
                                  ref={iconRef}
                                  className="relative inline-flex items-center"
                                  onMouseEnter={(e) => {
                                    setHoveredAttempt(attemptKey);
                                    // Check if tooltip would go off-screen
                                    const rect = e.currentTarget.getBoundingClientRect();
                                    const spaceBelow = window.innerHeight - rect.bottom;
                                    const tooltipHeight = 250; // Approximate height of tooltip
                                    
                                    if (spaceBelow < tooltipHeight) {
                                      setTooltipPosition('above');
                                    } else {
                                      setTooltipPosition('below');
                                    }
                                  }}
                                  onMouseLeave={() => {
                                    setHoveredAttempt(null);
                                    setTooltipPosition('below');
                                  }}
                                >
                                  <Info className="w-4 h-4 text-slate-400 hover:text-slate-600 cursor-help" />
                                  {hoveredAttempt === attemptKey && (
                                    <div 
                                      ref={tooltipRef}
                                      className={`absolute left-6 z-50 bg-slate-900 text-white p-3 rounded-lg shadow-xl min-w-[200px] text-xs ${
                                        tooltipPosition === 'above' 
                                          ? 'bottom-6' 
                                          : 'top-0'
                                      }`}
                                      style={{
                                        maxHeight: '80vh',
                                        overflowY: 'auto'
                                      }}
                                    >
                                      <div className="font-semibold mb-2 border-b border-slate-700 pb-1">Token Usage</div>
                                      <div className="space-y-1">
                                        {attempt.tokenUsage.input_tokens && (
                                          <div className="flex justify-between">
                                            <span className="text-slate-300">Input:</span>
                                            <span className="font-mono">{attempt.tokenUsage.input_tokens.toLocaleString()}</span>
                                          </div>
                                        )}
                                        {attempt.tokenUsage.output_tokens && (
                                          <div className="flex justify-between">
                                            <span className="text-slate-300">Output:</span>
                                            <span className="font-mono">{attempt.tokenUsage.output_tokens.toLocaleString()}</span>
                                          </div>
                                        )}
                                        {attempt.tokenUsage.reasoning_tokens !== undefined && (
                                          <div className="flex justify-between">
                                            <span className="text-slate-300">Reasoning:</span>
                                            <span className="font-mono">{attempt.tokenUsage.reasoning_tokens.toLocaleString()}</span>
                                          </div>
                                        )}
                                        {attempt.tokenUsage.total_tokens && (
                                          <div className="flex justify-between pt-1 border-t border-slate-700 mt-1 font-semibold">
                                            <span>Total:</span>
                                            <span className="font-mono">{attempt.tokenUsage.total_tokens.toLocaleString()}</span>
                                          </div>
                                        )}
                                      </div>
                                      {/* Arrow pointer - adjusts based on position */}
                                      <div 
                                        className={`absolute w-0 h-0 border-solid ${
                                          tooltipPosition === 'above'
                                            ? 'top-full left-2 border-t-[6px] border-t-slate-900 border-x-[6px] border-x-transparent'
                                            : 'bottom-full left-2 border-b-[6px] border-b-slate-900 border-x-[6px] border-x-transparent'
                                        }`}
                                      />
                                    </div>
                                  )}
                                </div>
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
                        );
                      })}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'questions' && (
            <div className="space-y-6">
              {/* NEW: Sub-tab Navigation */}
              <div className="border-b border-slate-200">
                <nav className="flex space-x-8">
                  <button
                    onClick={() => setQuestionTab('both')}
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      questionTab === 'both'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    Both (Rubric + Feedback)
                  </button>
                  <button
                    onClick={() => setQuestionTab('rubric')}
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      questionTab === 'rubric'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    Grading Rubric Only
                  </button>
                  <button
                    onClick={() => setQuestionTab('feedback')}
                    className={`py-2 px-1 border-b-2 font-medium text-sm ${
                      questionTab === 'feedback'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    Feedback Only
                  </button>
                </nav>
              </div>

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
                    <div className="text-sm font-medium text-slate-700 min-w-[180px] text-center bg-white/80 px-3 py-1 rounded-lg">
                      Question {selectedQuestion} ({Math.max(1, questionIds.indexOf(selectedQuestion) + 1)} of {questionIds.length})
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
                  {results.questions.map((q, idx) => {
                    const qid = q.text;
                    const isActive = qid === selectedQuestion;
                    // Use the actual question ID from q.text, not a fallback
                    const displayText = q.text;
                    return (
                      <button
                        key={qid || `q-${idx}`}
                        type="button"
                        onClick={() => setSelectedQuestion(qid)}
                        className={`px-4 py-2 rounded-lg border text-sm font-medium transition-all transform hover:scale-105 ${
                          isActive
                            ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-transparent shadow-lg'
                            : 'bg-white/80 text-slate-700 border-slate-300 hover:bg-slate-50 hover:border-slate-400'
                        }`}
                        aria-current={isActive ? 'true' : undefined}
                        aria-label={`Select question ${displayText}`}
                      >
                        {displayText}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Question Feedback with Human Grades */}
              {selectedQuestion && results.humanGrades && (
                <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 mb-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-slate-700 mb-1">Human Graded Mark</h3>
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold text-green-700">
                          {results.humanGrades[selectedQuestion] !== undefined 
                            ? results.humanGrades[selectedQuestion] 
                            : 'N/A'}
                        </span>
                        {results.questions.find(q => q.text === selectedQuestion) && (
                          <span className="text-sm text-slate-600">
                            / {(() => {
                              // Find max mark from first model's first attempt's feedback
                              const firstModel = results.modelResults[0];
                              const firstAttempt = firstModel?.attempts[0];
                              const feedback = firstAttempt?.questionFeedback?.find(qf => qf.questionId === selectedQuestion);
                              if (feedback?.mark) {
                                const parts = feedback.mark.split('/');
                                return parts[1] || '?';
                              }
                              return '?';
                            })()}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-sm text-slate-600">
                      Question: {selectedQuestion}
                    </div>
                  </div>
                </div>
              )}

              {/* Question Feedback from Models */}
              <div className="space-y-6">
                {isLoadingResults && (
                  <div className="animate-pulse space-y-4">
                    <div className="h-6 bg-slate-200 rounded w-1/4"></div>
                    <div className="h-20 bg-slate-200 rounded"></div>
                    <div className="h-20 bg-slate-200 rounded"></div>
                  </div>
                )}
                
                {/* NEW: Conditional rendering based on sub-tab */}
                {questionTab === 'both' && (
                  // BOTH: Show rubric + feedback
                  results.modelResults.map((modelResult) => {
                    // Get rubric data for this model
                    const modelRubricData = rubricResults?.rubric_results?.[modelResult.model];
                    
                    return (
                      <div key={modelResult.model} className="bg-white/80 backdrop-blur-sm border border-white/60 rounded-xl p-6 shadow-lg">
                        <div className="flex items-center mb-4">
                          <div className="w-4 h-4 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full mr-3"></div>
                          <h4 className="text-lg font-bold text-slate-900">
                            {modelResult.rubricModel && modelResult.assessmentModel
                              ? formatModelPairLabel(modelResult.rubricModel, modelResult.assessmentModel, modelResult.model)
                              : formatModelLabel(modelResult.model)}
                          </h4>
                        </div>
                        <div className="grid gap-4">
                          {modelResult.attempts.map((attempt) => {
                            const questionFeedback = attempt.questionFeedback?.find(
                              qf => qf.questionId === selectedQuestion
                            );
                            
                            // Get rubric response for this attempt
                            const rubricResponse = modelRubricData?.[attempt.attemptNumber.toString()]?.rubric_response;
                            
                            const filteredCriteria = rubricResponse ? extractQuestionCriteria(rubricResponse, selectedQuestion) : null;
                            
                            return (
                              <div key={attempt.attemptNumber} className="space-y-3">
                                {/* Rubric Section */}
                                {filteredCriteria && (
                                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                                    <div className="flex justify-between items-center mb-3">
                                      <span className="text-xs font-semibold text-purple-800 uppercase tracking-wide">
                                        Grading Criteria (Attempt {attempt.attemptNumber})
                                      </span>
                                    </div>
                                    <QuestionCriteriaDisplay criteria={filteredCriteria} />
                                  </div>
                                )}
                                
                                {/* Feedback Section */}
                                {questionFeedback ? (
                                  <div className="bg-gradient-to-r from-slate-50 to-blue-50/50 rounded-lg p-4 border border-slate-200/60">
                                    <div className="flex justify-between items-center mb-3">
                                      <span className="text-sm font-semibold text-slate-700 bg-white/70 px-3 py-1 rounded-full">
                                        Assessment Feedback (Attempt {attempt.attemptNumber})
                                      </span>
                                      <span className="text-sm font-bold text-blue-700 bg-blue-100 px-3 py-1 rounded-full">
                                        {questionFeedback.mark}
                                      </span>
                                    </div>
                                    <div className="space-y-2">
                                      {questionFeedback.feedback ? (
                                        <p className="text-sm text-slate-700 leading-relaxed">
                                          {questionFeedback.feedback}
                                        </p>
                                      ) : (
                                        <p className="text-sm text-slate-500 italic">
                                          No feedback provided
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                ) : (
                                  attempt.failureReasons && attempt.failureReasons.length > 0 ? (
                                    <div className="bg-red-50 rounded-lg p-4 border border-red-200/70">
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
                                  ) : (
                                    <div className="bg-slate-50 rounded-lg p-4 border border-slate-200/60">
                                      <div className="flex justify-between items-center mb-2">
                                        <span className="text-sm font-semibold text-slate-600 bg-white/70 px-3 py-1 rounded-full">
                                          Attempt {attempt.attemptNumber}
                                        </span>
                                      </div>
                                      <p className="text-sm text-slate-500 italic">
                                        No answer recorded for this question
                                      </p>
                                    </div>
                                  )
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })
                )}
                
                {questionTab === 'rubric' && (
                  // RUBRIC ONLY: Show only rubric responses
                  results.modelResults.map((modelResult) => {
                    const modelRubricData = rubricResults?.rubric_results?.[modelResult.model];
                    
                    if (!modelRubricData) {
                      return (
                        <div key={modelResult.model} className="bg-white/80 backdrop-blur-sm border border-white/60 rounded-xl p-6 shadow-lg">
                          <div className="flex items-center mb-4">
                            <div className="w-4 h-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full mr-3"></div>
                            <h4 className="text-lg font-bold text-slate-900">
                              {modelResult.rubricModel 
                                ? formatRubricModelLabel(modelResult.rubricModel, modelResult.model)
                                : formatModelLabel(modelResult.model)}
                            </h4>
                          </div>
                          <p className="text-sm text-slate-500 italic">No rubric analysis available for this model</p>
                        </div>
                      );
                    }
                    
                    return (
                      <div key={modelResult.model} className="bg-white/80 backdrop-blur-sm border border-white/60 rounded-xl p-6 shadow-lg">
                        <div className="flex items-center mb-4">
                          <div className="w-4 h-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full mr-3"></div>
                          <h4 className="text-lg font-bold text-slate-900">
                            {modelResult.rubricModel 
                              ? formatRubricModelLabel(modelResult.rubricModel, modelResult.model)
                              : formatModelLabel(modelResult.model)}
                          </h4>
                        </div>
                        <div className="grid gap-4">
                          {Object.entries(modelRubricData).map(([tryIndex, rubricData]) => {
                            const rubricResponse = (rubricData as any).rubric_response;
                            const filteredCriteria = rubricResponse ? extractQuestionCriteria(rubricResponse, selectedQuestion) : null;
                            
                            return (
                              <div key={tryIndex} className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                                <div className="flex justify-between items-center mb-3">
                                  <span className="text-sm font-semibold text-purple-800 bg-white/70 px-3 py-1 rounded-full">
                                    Grading Criteria (Attempt {tryIndex})
                                  </span>
                                </div>
                                {filteredCriteria ? (
                                  <QuestionCriteriaDisplay criteria={filteredCriteria} />
                                ) : (
                                  <p className="text-sm text-slate-500 italic">
                                    No grading criteria available for this question
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })
                )}
                
                {questionTab === 'feedback' && (
                  // FEEDBACK ONLY: Show only assessment feedback
                  results.modelResults.map((modelResult) => (
                  <div key={modelResult.model} className="bg-white/80 backdrop-blur-sm border border-white/60 rounded-xl p-6 shadow-lg">
                    <div className="flex items-center mb-4">
                      <div className="w-4 h-4 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full mr-3"></div>
                      <h4 className="text-lg font-bold text-slate-900">
                        {modelResult.rubricModel && modelResult.assessmentModel
                          ? formatModelPairLabel(modelResult.rubricModel, modelResult.assessmentModel, modelResult.model)
                          : formatModelLabel(modelResult.model)}
                      </h4>
                    </div>
                    <div className="grid gap-4">
                      {modelResult.attempts.map((attempt) => {
                        console.log('Attempt feedback for attempt', attempt.attemptNumber, ':', attempt.questionFeedback?.map(qf => qf.questionId));
                        console.log('Looking for selectedQuestion:', selectedQuestion);
                        const questionFeedback = attempt.questionFeedback?.find(
                          qf => qf.questionId === selectedQuestion
                        );
                        console.log('Found feedback:', questionFeedback);
                        
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
                            <div className="space-y-2">
                              {questionFeedback.feedback ? (
                                <p className="text-sm text-slate-700 leading-relaxed">
                                  {questionFeedback.feedback}
                                </p>
                              ) : (
                                <p className="text-sm text-slate-500 italic">
                                  No feedback provided
                                </p>
                              )}
                            </div>
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
                          ) : (
                            <div key={attempt.attemptNumber} className="bg-slate-50 rounded-lg p-4 border border-slate-200/60">
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-sm font-semibold text-slate-600 bg-white/70 px-3 py-1 rounded-full">
                                  Attempt {attempt.attemptNumber}
                                </span>
                              </div>
                              <p className="text-sm text-slate-500 italic">
                                No answer recorded for this question
                              </p>
                            </div>
                          )
                        )
                      })}
                    </div>
                  </div>
                )))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};