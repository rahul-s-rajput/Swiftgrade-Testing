export interface Assessment {
  id: string;
  name: string;
  date: string;
  status: 'running' | 'complete';
  studentImages: File[];
  answerKeyImages: File[];
  questions: string;
  humanGrades: string;
  selectedModels: string[];
  iterations: number;
  results?: AssessmentResults;
}

export interface AssessmentResults {
  modelResults: ModelResult[];
  questions: Question[];
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