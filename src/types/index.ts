export type ReasoningLevel = 'none' | 'low' | 'medium' | 'high' | 'custom';

export interface ReasoningConfig {
  level: ReasoningLevel;
  tokens?: number;
}

// --- Grading Rubric Types ---

export interface ModelPair {
  rubricModel: string;              // Model ID for rubric analysis
  assessmentModel: string;          // Model ID for assessment grading
  rubricReasoning?: ReasoningConfig;   // Reasoning config for rubric model
  assessmentReasoning?: ReasoningConfig; // Reasoning config for assessment model
  instanceId?: string;              // Unique pair identifier
}

export interface Assessment {
  id: string;
  name: string;
  date: string;
  status: 'running' | 'complete' | 'failed';
  studentImages: File[];
  answerKeyImages: File[];
  rubricImages: File[];  // NEW: Grading rubric images
  questions: string;
  humanGrades: string;
  
  // NEW: Model pairs for rubric-based grading
  modelPairs?: ModelPair[];
  
  // LEGACY: Single models (kept for backward compatibility)
  selectedModels: string[];
  iterations: number;
  reasoningBySelection?: ReasoningConfig[];
  results?: AssessmentResults;
}

export interface AssessmentResults {
  modelResults: ModelResult[];
  questions: Question[];
  totalMaxMarks: number;
  humanGrades?: Record<string, number>; // question_id -> human grade
}

export interface ModelResult {
  // NEW: Model pair identifiers (for rubric-based grading)
  rubricModel?: string;      // Rubric model ID
  assessmentModel?: string;  // Assessment model ID
  
  // LEGACY: Combined model identifier (kept for backward compatibility)
  model: string;
  averages: {
    discrepancies100: number;
    questionDiscrepancies100: number;
    zpfDiscrepancies: number;
    zpfQuestionDiscrepancies: number;
    rangeDiscrepancies: number;
    rangeQuestionDiscrepancies: number;
    totalScore: number;
  };
  attempts: Attempt[];
}

export interface Attempt {
  attemptNumber: number;
  
  // NEW: Rubric analysis output
  rubricResponse?: string;
  
  // Existing discrepancy metrics
  discrepancies100: number;
  questionDiscrepancies100: number;
  zpfDiscrepancies: number;
  zpfQuestionDiscrepancies: number;
  rangeDiscrepancies: number;
  rangeQuestionDiscrepancies: number;
  totalScore: number;
  questionFeedback: QuestionFeedback[];
  // New: lists of question ids (e.g., ["MAI.1b(i)", "MAI.1c(ii)"]) for each discrepancy type
  lt100Questions?: string[];
  zpfQuestions?: string[];
  rangeQuestions?: string[];
  // New: failure reasons when a model attempt failed to parse/validate
  failureReasons?: string[];
  // Token usage tracking
  tokenUsage?: {
    input_tokens?: number;
    output_tokens?: number;
    reasoning_tokens?: number;
    total_tokens?: number;
  };
}

export interface QuestionFeedback {
  questionId: string;
  feedback: string;
  mark: string;
}

export interface Question {
  number: number;
  text: string;
}

export interface AIModel {
  id: string;
  name: string;
  provider: string;
}