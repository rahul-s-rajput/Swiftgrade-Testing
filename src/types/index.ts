export type ReasoningLevel = 'none' | 'low' | 'medium' | 'high' | 'custom';

export interface ReasoningConfig {
  level: ReasoningLevel;
  tokens?: number;
}

export interface Assessment {
  id: string;
  name: string;
  date: string;
  status: 'running' | 'complete' | 'failed';
  studentImages: File[];
  answerKeyImages: File[];
  questions: string;
  humanGrades: string;
  selectedModels: string[];
  iterations: number;
  reasoningBySelection?: ReasoningConfig[];
  results?: AssessmentResults;
}

export interface AssessmentResults {
  modelResults: ModelResult[];
  questions: Question[];
  totalMaxMarks: number;
}

export interface ModelResult {
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
  discrepancies100: number;
  questionDiscrepancies100: number;
  zpfDiscrepancies: number;
  zpfQuestionDiscrepancies: number;
  rangeDiscrepancies: number;
  rangeQuestionDiscrepancies: number;
  totalScore: number;
  questionFeedback: QuestionFeedback[];
  // New: lists of question numbers (e.g., [1, 3, 7]) for each discrepancy type
  lt100Questions?: number[];
  zpfQuestions?: number[];
  rangeQuestions?: number[];
  // New: failure reasons when a model attempt failed to parse/validate
  failureReasons?: string[];
}

export interface QuestionFeedback {
  questionNumber: number;
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