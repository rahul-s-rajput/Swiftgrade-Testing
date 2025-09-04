import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { Assessment, AssessmentResults, ReasoningConfig } from '../types';
import {
  createSession,
  getSignedUrl,
  uploadToSignedUrl,
  registerImage,
  postQuestionsConfig,
  gradeSingleWithRetry,
  getResults,
  getResultErrors,
  getStats,
  getQuestions,
  getSessions,
  deleteSession,
  type ResultsRes,
  type ResultsErrorsRes,
  type StatsRes,
  type QuestionConfigQuestion,
  type QuestionsRes,
  type ResultItem,
} from '../utils/api';

interface AssessmentContextType {
  assessments: Assessment[];
  addAssessment: (assessment: Omit<Assessment, 'id' | 'date'>) => Promise<void>;
  deleteAssessment: (id: string) => void;
  getAssessment: (id: string) => Assessment | undefined;
  updateAssessmentStatus: (id: string, status: 'running' | 'complete' | 'failed', results?: AssessmentResults) => void;
  retryAssessment: (id: string) => Promise<void>;
  refreshSessions: () => Promise<void>;
  loadAssessmentResults: (id: string) => Promise<void>;
  loading: boolean;
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

export const useAssessments = () => {
  const context = useContext(AssessmentContext);
  if (!context) {
    throw new Error('useAssessments must be used within an AssessmentProvider');
  }
  return context;
};

// Token counts for effort level mapping
const EFFORT_TO_TOKENS = {
  low: 4096,    // Increased from 1024 to handle multiple questions
  medium: 8192,
  high: 32768
} as const;

// Convert frontend reasoning config to OpenRouter format
function convertReasoningToOpenRouterFormat(
  models: string[],
  reasoningBySelection?: ReasoningConfig[]
): any | undefined {
  if (!reasoningBySelection || reasoningBySelection.length === 0) return undefined;
  
  // Build per-model reasoning configuration
  // This allows different reasoning settings for each model
  const perModelReasoning: Record<string, any> = {};
  let hasAnyReasoning = false;
  
  models.forEach((model, index) => {
    const reasoning = reasoningBySelection[index];
    if (!reasoning || reasoning.level === 'none') return;
    
    const modelId = model.toLowerCase();
    
    // Determine if model supports effort-based or token-based reasoning
    const supportsEffort = 
      modelId.includes('anthropic/') ||
      modelId.includes('mistral/magistral') ||
      modelId.includes('google/gemini-2.5') ||
      modelId.includes('google/gemini-2.0') ||
      modelId.includes('z-ai/glm');
      
    const supportsMaxTokens = 
      modelId.includes('openai/') ||
      modelId.includes('deepseek/') ||
      (modelId.includes('qwen/') && modelId.includes('thinking'));
    
    // Map to OpenRouter format based on model and reasoning type
    if (reasoning.level === 'custom' && reasoning.tokens) {
      // Custom token-based reasoning
      if (supportsMaxTokens) {
        perModelReasoning[model] = { max_tokens: reasoning.tokens };
        hasAnyReasoning = true;
      } else if (supportsEffort) {
        // Fallback to high effort if model doesn't support max_tokens
        perModelReasoning[model] = { effort: 'high' };
        hasAnyReasoning = true;
      }
    } else if (reasoning.level !== 'custom') {
      // Effort-based reasoning (low/medium/high)
      if (supportsEffort) {
        perModelReasoning[model] = { effort: reasoning.level };
        hasAnyReasoning = true;
      } else if (supportsMaxTokens) {
        // Map effort levels to token counts for models that only support max_tokens
        perModelReasoning[model] = { 
          max_tokens: EFFORT_TO_TOKENS[reasoning.level as keyof typeof EFFORT_TO_TOKENS] || 8192 
        };
        hasAnyReasoning = true;
      }
    }
  });
  
  if (!hasAnyReasoning) return undefined;
  
  // For now, return the first model's reasoning config
  // In future, could enhance backend to support per-model reasoning
  const firstModel = models[0];
  return perModelReasoning[firstModel] || undefined;
}

export const AssessmentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Load existing sessions from backend on mount
  useEffect(() => {
    let cancelled = false;
    const fetchWithRetry = async (tries = 3) => {
      let lastErr: any;
      for (let i = 0; i < tries; i++) {
        try {
          const sessions = await getSessions();
          const mapped: Assessment[] = (sessions || []).map(s => ({
            id: s.id,
            name: (s.name && s.name.trim()) ? s.name : `Assessment ${String(s.id).slice(0, 8)}`,
            date: (String(s.created_at || '').split('T')[0]) || new Date().toISOString().split('T')[0],
            status: (s.status === 'graded') ? 'complete' : (s.status === 'failed' ? 'failed' : 'running'),
            studentImages: [],
            answerKeyImages: [],
            questions: '[]',
            humanGrades: '{}',
            selectedModels: (s.selected_models || []),
            iterations: (typeof s.default_tries === 'number' && s.default_tries > 0 ? s.default_tries : 1),
          }));
          if (!cancelled) {
            setAssessments(prev => mapped.map(m => {
              const existing = prev.find(p => p.id === m.id);
              return existing ? { ...m, results: existing.results } : m;
            }));
            setLoading(false);
          }
          return;
        } catch (e) {
          lastErr = e;
          await new Promise(res => setTimeout(res, 600 * (i + 1)));
        }
      }
      console.error('Failed to load sessions:', lastErr);
      if (!cancelled) setLoading(false);
    };
    setLoading(true);
    void fetchWithRetry(3);
    return () => { cancelled = true; };
  }, []);

  // Expose a manual refresh that reuses the same logic
  const refreshSessions = useCallback(async () => {
    try {
      const sessions = await getSessions();
      const mapped: Assessment[] = (sessions || []).map(s => ({
        id: s.id,
        name: (s.name && s.name.trim()) ? s.name : `Assessment ${String(s.id).slice(0, 8)}`,
        date: (String(s.created_at || '').split('T')[0]) || new Date().toISOString().split('T')[0],
        status: (s.status === 'graded') ? 'complete' : (s.status === 'failed' ? 'failed' : 'running'),
        studentImages: [],
        answerKeyImages: [],
        questions: '[]',
        humanGrades: '{}',
        selectedModels: (s.selected_models || []),
        iterations: (typeof s.default_tries === 'number' && s.default_tries > 0 ? s.default_tries : 1),
      }));
      // Preserve existing results and client-only fields when possible
      setAssessments(prev => mapped.map(m => {
        const existing = prev.find(p => p.id === m.id);
        return existing ? { ...m, results: existing.results } : m;
      }));
    } catch (e) {
      console.error('Failed to refresh sessions:', e);
    }
  }, []);

  // Load results+stats+questions for an existing session and cache into state
  const loadAssessmentResults = useCallback(async (sessionId: string) => {
    // Simple retry helper
    const fetchWithRetry = async <T,>(fn: () => Promise<T>, tries = 5): Promise<T> => {
      let lastErr: any;
      for (let i = 0; i < tries; i++) {
        try {
          return await fn();
        } catch (e) {
          lastErr = e;
          await new Promise(res => setTimeout(res, 600 * (i + 1)));
        }
      }
      throw lastErr;
    };

    try {
      const [qRes, resultsRes, statsRes, errorsRes] = await Promise.all([
        fetchWithRetry<QuestionsRes>(() => getQuestions(sessionId)),
        fetchWithRetry<ResultsRes>(() => getResults(sessionId)),
        fetchWithRetry<StatsRes>(() => getStats(sessionId)),
        fetchWithRetry<ResultsErrorsRes>(() => getResultErrors(sessionId)),
      ] as const);

      const questions = [...(qRes.questions || [])]
        .sort((a: QuestionConfigQuestion, b: QuestionConfigQuestion) => a.number - b.number)
        .map((q: QuestionConfigQuestion) => ({ number: q.number, text: q.question_id }));

      // Map question_id -> number for discrepancy question lists
      const qidToNumber: Record<string, number> = {};
      (qRes.questions || []).forEach((q) => { qidToNumber[q.question_id] = q.number; });

      const totals = statsRes.totals?.total_marks_awarded_by_model_try || {} as Record<string, Record<string, number>>;
      const disc = statsRes.discrepancies_by_model_try || {} as Record<string, Record<string, any>>;
      const byQ = resultsRes.results_by_question || {} as Record<string, Record<string, ResultItem[]>>;

      const errorsByModelTry = (errorsRes?.errors_by_model_try || {}) as Record<string, Record<string, Array<Record<string, any>>>>;
      const uniqueModels = Array.from(new Set(
        Object.keys(totals).concat(Object.keys(disc)).concat(Object.keys(errorsByModelTry))
      ));
      const modelResults = uniqueModels.map(model => {
        const triesMap = totals[model] || {};
        const errorTries = Object.keys(errorsByModelTry[model] || {});
        const tryNums = Array.from(new Set(
          Object.keys(triesMap).concat(errorTries)
        )).map(k => parseInt(k, 10)).sort((a, b) => a - b);
        const attempts = tryNums.map(tryIndex => {
          const d = (disc[model] && disc[model][String(tryIndex)]) || {} as any;
          const discrepancies100 = d.lt100?.count ?? 0;
          const questionDiscrepancies100 = d.lt100?.count ?? 0;
          const zpfDiscrepancies = d.zpf?.count ?? 0;
          const zpfQuestionDiscrepancies = d.zpf?.count ?? 0;
          const rangeDiscrepancies = d.range?.count ?? 0;
          const rangeQuestionDiscrepancies = d.range?.count ?? 0;
          const totalScore = (totals[model] && totals[model][String(tryIndex)]) ?? 0;

            // Map discrepancy question IDs to question numbers for UI
            const lt100Questions = ((d.lt100?.questions as string[] | undefined) || [])
            const zpfQuestions = ((d.zpf?.questions as string[] | undefined) || [])
            const rangeQuestions = ((d.range?.questions as string[] | undefined) || [])

            const questionFeedback = (qRes.questions || [])
              .slice()
              .sort((a: QuestionConfigQuestion, b: QuestionConfigQuestion) => a.number - b.number)
              .map((q: QuestionConfigQuestion) => {
                const itemsForModel = (byQ[q.question_id]?.[model] || []) as ResultItem[];
                const item = itemsForModel.find((it: ResultItem) => it.try_index === tryIndex) || null;
                const markVal = item?.marks_awarded;
                const markStr = `${markVal ?? 0}/${q.max_marks}`;
                return {
                  questionId: q.question_id,
                  feedback: item?.rubric_notes || '',
                  mark: markStr,
                };
              });
          // Attach failure reasons from errors endpoint
          const errs = (errorsByModelTry[model] && errorsByModelTry[model][String(tryIndex)]) || [];
          const failureReasons = errs
            .map((e: Record<string, any>) => (typeof e?.reason === 'string' && e.reason.trim())
              || (typeof e?.message === 'string' && e.message.trim())
              || JSON.stringify(e))
            .filter((s: string) => !!s);
          return {
            attemptNumber: tryIndex,
            discrepancies100,
            questionDiscrepancies100,
            zpfDiscrepancies,
            zpfQuestionDiscrepancies,
            rangeDiscrepancies,
            rangeQuestionDiscrepancies,
            totalScore,
            questionFeedback,
            lt100Questions,
            zpfQuestions,
            rangeQuestions,
            failureReasons,
          };
        });

        const avg = (key: keyof (typeof attempts)[number]) => {
          const nums = attempts.map(a => (typeof a[key] === 'number' ? (a[key] as number) : 0));
          if (nums.length === 0) return 0;
          return Math.round((nums.reduce((s, x) => s + x, 0) / nums.length) * 100) / 100;
        };

        return {
          model,
          averages: {
            discrepancies100: avg('discrepancies100'),
            questionDiscrepancies100: avg('questionDiscrepancies100'),
            zpfDiscrepancies: avg('zpfDiscrepancies'),
            zpfQuestionDiscrepancies: avg('zpfQuestionDiscrepancies'),
            rangeDiscrepancies: avg('rangeDiscrepancies'),
            rangeQuestionDiscrepancies: avg('rangeQuestionDiscrepancies'),
            totalScore: avg('totalScore'),
          },
          attempts,
        };
      });

      const totalMaxMarks = (statsRes as any)?.totals?.total_max_marks ?? 0;
      const mapped: AssessmentResults = { modelResults, questions, totalMaxMarks };
      setAssessments(prev => prev.map(a => (a.id === sessionId ? { ...a, results: mapped } : a)));
    } catch (e) {
      console.error('Failed to load assessment results:', e);
    }
  }, []);

  const addAssessment = useCallback(async (assessmentData: Omit<Assessment, 'id' | 'date'>) => {
    // 1) Create backend session
    const session = await createSession(assessmentData.name);
    const sessionId = session.session_id;

    // Create local placeholder entry immediately
    const localAssessment: Assessment = {
      ...assessmentData,
      id: sessionId,
      date: new Date().toISOString().split('T')[0],
      status: 'running',
    };
    setAssessments(prev => [...prev, localAssessment]);

    // Helper to update status/results in state
    const setComplete = (results?: AssessmentResults) => {
      setAssessments(prev => prev.map(a => (a.id === sessionId ? { ...a, status: 'complete', results: results ?? a.results } : a)));
    };
    const setFailed = () => {
      setAssessments(prev => prev.map(a => (a.id === sessionId ? { ...a, status: 'failed' } : a)));
    };

    // 2..6) Perform long-running work in the background (do not block caller)
    (async () => {
      try {
        // Upload and register images
        const uploadAndRegister = async (files: File[], role: 'student' | 'answer_key') => {
          for (let i = 0; i < files.length; i++) {
            const f = files[i];
            const signed = await getSignedUrl(f.name, f.type || 'application/octet-stream');
            await uploadToSignedUrl(signed.uploadUrl, signed.headers || {}, f, f.type || 'application/octet-stream');
            const url = signed.publicUrl || '';
            if (!url) throw new Error('No publicUrl returned for uploaded file. Ensure storage bucket is public or backend returns a read URL.');
            await registerImage(sessionId, role, url, i);
          }
        };

        await uploadAndRegister(assessmentData.studentImages, 'student');
        await uploadAndRegister(assessmentData.answerKeyImages, 'answer_key');

        // Parse and post questions config + human marks
        let questionsPayload: QuestionConfigQuestion[];
        let humanMarks: Record<string, number>;
        try {
          questionsPayload = JSON.parse(assessmentData.questions) as QuestionConfigQuestion[];
          humanMarks = JSON.parse(assessmentData.humanGrades) as Record<string, number>;
          if (!Array.isArray(questionsPayload) || typeof humanMarks !== 'object') throw new Error('invalid');
        } catch {
          throw new Error('Please paste valid JSON for Questions and Human Graded Marks per the required schema.');
        }

        await postQuestionsConfig(sessionId, questionsPayload, humanMarks);

        // Handle reasoning configuration for each model instance
        // When using same model with different reasoning, we need separate calls
        const modelInstances: Array<{model: string, reasoning?: any}> = [];
        
        assessmentData.selectedModels.forEach((model, index) => {
          const reasoning = assessmentData.reasoningBySelection?.[index];
          let reasoningConfig: any = undefined;
          
          if (reasoning && reasoning.level !== 'none') {
            const modelId = model.toLowerCase();
            
            // Determine model capabilities
            const supportsEffort = 
              modelId.includes('anthropic/') ||
              modelId.includes('mistral/magistral') ||
              modelId.includes('google/gemini-2.5') ||
              modelId.includes('google/gemini-2.0') ||
              modelId.includes('z-ai/glm');
              
            const supportsMaxTokens = 
              modelId.includes('openai/') ||
              modelId.includes('deepseek/') ||
              modelId.includes('qwen/') ||
              modelId.includes('o1-');
            
            if (reasoning.level === 'custom' && reasoning.tokens) {
              // Custom token-based reasoning
              if (supportsMaxTokens || modelId.includes('o1-')) {
                reasoningConfig = { max_tokens: reasoning.tokens };
              } else if (supportsEffort) {
                reasoningConfig = { effort: 'high' };
              }
            } else if (reasoning.level !== 'custom') {
              // Effort-based reasoning
              if (supportsEffort) {
                reasoningConfig = { effort: reasoning.level };
              } else if (supportsMaxTokens) {
                const tokenMap = { low: 1024, medium: 8192, high: 32768 };
                reasoningConfig = { max_tokens: tokenMap[reasoning.level as keyof typeof tokenMap] || 8192 };
              }
            }
          }
          
          modelInstances.push({ model, reasoning: reasoningConfig });
        });
        
        console.log('📊 Model instances with reasoning:', modelInstances);
        
        // For backend compatibility, we need to handle this properly
        // Currently backend expects a single reasoning config, so we'll use the first non-null one
        const firstReasoning = modelInstances.find(m => m.reasoning)?.reasoning;
        
        if (firstReasoning) {
          console.log('🧠 Using reasoning config:', firstReasoning);
        } else {
          console.log('⚠️ No reasoning config found');
        }

        // Start grading with per-model reasoning
        await gradeSingleWithRetry(
          sessionId, 
          assessmentData.selectedModels, 
          assessmentData.iterations,
          firstReasoning,  // Keep for backward compatibility
          assessmentData.reasoningBySelection  // Pass per-model reasoning configs
        );

        // Fetch results and stats (retry a few times for eventual consistency)
        const fetchWithRetry = async <T,>(fn: () => Promise<T>, tries = 5): Promise<T> => {
          let lastErr: any;
          for (let i = 0; i < tries; i++) {
            try {
              return await fn();
            } catch (e) {
              lastErr = e;
              await new Promise(res => setTimeout(res, 600 * (i + 1))); // backoff
            }
          }
          throw lastErr;
        };

        const resultsPromise: Promise<ResultsRes> = fetchWithRetry(() => getResults(sessionId));
        const statsPromise: Promise<StatsRes> = fetchWithRetry(() => getStats(sessionId));
        const errorsPromise: Promise<ResultsErrorsRes> = fetchWithRetry(() => getResultErrors(sessionId));
        const [resultsRes, statsRes, errorsRes] = await Promise.all([resultsPromise, statsPromise, errorsPromise] as const);

        // Transform backend responses to AssessmentResults shape
        const questions = [...questionsPayload]
          .sort((a, b) => a.number - b.number)
          .map(q => ({ number: q.number, text: q.question_id }));

        // Map question_id -> number for discrepancy question lists
        const qidToNumber: Record<string, number> = {};
        questionsPayload.forEach((q) => { qidToNumber[q.question_id] = q.number; });

        const totals = statsRes.totals?.total_marks_awarded_by_model_try || {};
        const disc = statsRes.discrepancies_by_model_try || {};
        const byQ = resultsRes.results_by_question || {};

        const errorsByModelTry = (errorsRes?.errors_by_model_try || {}) as Record<string, Record<string, Array<Record<string, any>>>>;
        const uniqueModels = Array.from(new Set(
          Object.keys(totals).concat(Object.keys(disc)).concat(Object.keys(errorsByModelTry))
        ));
        const modelResults = uniqueModels.map(model => {
          const triesMap = totals[model] || {};
          const errorTries = Object.keys(errorsByModelTry[model] || {});
          const tryNums = Array.from(new Set(
            Object.keys(triesMap).concat(errorTries)
          )).map(k => parseInt(k, 10)).sort((a, b) => a - b);
          const attempts = tryNums.map(tryIndex => {
            const d = (disc[model] && disc[model][String(tryIndex)]) || {};
            const discrepancies100 = d.lt100?.count ?? 0;
            const questionDiscrepancies100 = d.lt100?.count ?? 0;
            const zpfDiscrepancies = d.zpf?.count ?? 0;
            const zpfQuestionDiscrepancies = d.zpf?.count ?? 0;
            const rangeDiscrepancies = d.range?.count ?? 0;
            const rangeQuestionDiscrepancies = d.range?.count ?? 0;
            const totalScore = (totals[model] && totals[model][String(tryIndex)]) ?? 0;

            // Map discrepancy question IDs to question numbers for UI
          const lt100Questions = ((d.lt100?.questions as string[] | undefined) || [])
          const zpfQuestions = ((d.zpf?.questions as string[] | undefined) || [])
          const rangeQuestions = ((d.range?.questions as string[] | undefined) || [])

            const questionFeedback = questionsPayload
              .sort((a, b) => a.number - b.number)
              .map(q => {
                const itemsForModel = (byQ[q.question_id]?.[model] || []) as ResultItem[];
                const item = itemsForModel.find((it: ResultItem) => it.try_index === tryIndex) || null;
                const markVal = item?.marks_awarded;
                const markStr = `${markVal ?? 0}/${q.max_marks}`;
                return {
                  questionId: q.question_id,
                  feedback: item?.rubric_notes || '',
                  mark: markStr,
                };
              });
            // Attach failure reasons from errors endpoint
            const errs = (errorsByModelTry[model] && errorsByModelTry[model][String(tryIndex)]) || [];
            const failureReasons = errs
              .map((e: Record<string, any>) => (typeof e?.reason === 'string' && e.reason.trim())
                || (typeof e?.message === 'string' && e.message.trim())
                || JSON.stringify(e))
              .filter((s: string) => !!s);
            return {
              attemptNumber: tryIndex,
              discrepancies100,
              questionDiscrepancies100,
              zpfDiscrepancies,
              zpfQuestionDiscrepancies,
              rangeDiscrepancies,
              rangeQuestionDiscrepancies,
              totalScore,
              questionFeedback,
              lt100Questions,
              zpfQuestions,
              rangeQuestions,
              failureReasons,
            };
          });

          const avg = (key: keyof typeof attempts[number]) => {
            const nums = attempts.map(a => (typeof a[key] === 'number' ? (a[key] as number) : 0));
            if (nums.length === 0) return 0;
            return Math.round((nums.reduce((s, x) => s + x, 0) / nums.length) * 100) / 100;
          };

          return {
            model,
            averages: {
              discrepancies100: avg('discrepancies100'),
              questionDiscrepancies100: avg('questionDiscrepancies100'),
              zpfDiscrepancies: avg('zpfDiscrepancies'),
              zpfQuestionDiscrepancies: avg('zpfQuestionDiscrepancies'),
              rangeDiscrepancies: avg('rangeDiscrepancies'),
              rangeQuestionDiscrepancies: avg('rangeQuestionDiscrepancies'),
              totalScore: avg('totalScore'),
            },
            attempts,
          };
        });

        const totalMaxMarks = (statsRes as any)?.totals?.total_max_marks ?? 0;
        const mapped: AssessmentResults = { modelResults, questions, totalMaxMarks };
        setComplete(mapped);
      } catch (e) {
        console.error('Assessment creation failed:', e);
        // Mark as failed to allow retry from UI
        setFailed();
      }
      // After finishing, re-sync from backend to reflect persisted status/data
      try {
        await refreshSessions();
      } catch (e) {
        console.error('Post-create refresh failed:', e);
      }
    })();
  }, [refreshSessions]);

  const deleteAssessment = useCallback((id: string) => {
    // Optimistic update
    setAssessments(prev => prev.filter(assessment => assessment.id !== id));
    void (async () => {
      try {
        await deleteSession(id);
      } catch (e) {
        console.error('Failed to delete session on backend:', e);
      } finally {
        // Re-sync from backend to ensure consistency
        await refreshSessions();
      }
    })();
  }, [refreshSessions]);

  const getAssessment = useCallback((id: string) => {
    return assessments.find(assessment => assessment.id === id);
  }, [assessments]);

  const updateAssessmentStatus = useCallback((id: string, status: 'running' | 'complete' | 'failed', results?: AssessmentResults) => {
    setAssessments(prev =>
      prev.map(assessment =>
        assessment.id === id
          ? { ...assessment, status, results: results || assessment.results }
          : assessment
      )
    );
  }, []);

  const retryAssessment = useCallback(async (id: string) => {
    const a = assessments.find(x => x.id === id);
    if (!a) return;
    // Optimistic: set to running
    updateAssessmentStatus(id, 'running');
    try {
      // Convert reasoning configuration if available
      const reasoningConfig = convertReasoningToOpenRouterFormat(
        a.selectedModels,
        a.reasoningBySelection
      );
      
      await gradeSingleWithRetry(
        id, 
        a.selectedModels, 
        a.iterations, 
        reasoningConfig,
        a.reasoningBySelection  // Pass per-model reasoning
      );
      // Refresh sessions and results
      await refreshSessions();
      await loadAssessmentResults(id);
    } catch (e) {
      console.error('Retry grading failed:', e);
      updateAssessmentStatus(id, 'failed');
    }
  }, [assessments, updateAssessmentStatus, refreshSessions, loadAssessmentResults]);

  return (
    <AssessmentContext.Provider value={{
      assessments,
      addAssessment,
      deleteAssessment,
      getAssessment,
      updateAssessmentStatus,
      refreshSessions,
      retryAssessment,
      loadAssessmentResults,
      loading,
    }}>
      {children}
    </AssessmentContext.Provider>
  );
};