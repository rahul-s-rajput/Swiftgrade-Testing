import { AssessmentResults, AIModel } from '../types';

export const mockAIModels: AIModel[] = [
  { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
  { id: 'claude-3', name: 'Claude 3 Opus', provider: 'Anthropic' },
  { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet', provider: 'Anthropic' },
  { id: 'claude-3-haiku', name: 'Claude 3 Haiku', provider: 'Anthropic' },
  { id: 'llama-2', name: 'Llama 2 70B', provider: 'Meta' },
  { id: 'llama-2-13b', name: 'Llama 2 13B', provider: 'Meta' },
  { id: 'mixtral-8x7b', name: 'Mixtral 8x7B', provider: 'Mistral AI' },
  { id: 'gemini-pro', name: 'Gemini Pro', provider: 'Google' },
  { id: 'palm-2', name: 'PaLM 2', provider: 'Google' }
];

export const generateMockResults = (selectedModels: string[], iterations: number): AssessmentResults => {
  const modelResults = selectedModels.map(modelId => {
    const model = mockAIModels.find(m => m.id === modelId)?.name || modelId;
    
    const attempts = Array.from({ length: iterations }, (_, i) => ({
      attemptNumber: i + 1,
      discrepancies100: Math.round((Math.random() * 20 + 5) * 100) / 100,
      questionDiscrepancies100: Math.round((Math.random() * 15 + 3) * 100) / 100,
      zpfDiscrepancies: Math.round((Math.random() * 25 + 8) * 100) / 100,
      zpfQuestionDiscrepancies: Math.round((Math.random() * 18 + 5) * 100) / 100,
      rangeDiscrepancies: Math.round((Math.random() * 30 + 10) * 100) / 100,
      rangeQuestionDiscrepancies: Math.round((Math.random() * 22 + 7) * 100) / 100,
      totalScore: Math.round((Math.random() * 30 + 70) * 100) / 100,
      questionFeedback: [
        {
          questionNumber: 1,
          feedback: `AI feedback for question 1 from ${model}, attempt ${i + 1}. The student's answer shows ${Math.random() > 0.5 ? 'good understanding' : 'some confusion'} of the concept.`,
          mark: `${Math.floor(Math.random() * 5 + 1)}/5`
        },
        {
          questionNumber: 2,
          feedback: `AI feedback for question 2 from ${model}, attempt ${i + 1}. ${Math.random() > 0.5 ? 'Excellent work' : 'Needs improvement'} on this problem.`,
          mark: `${Math.floor(Math.random() * 5 + 1)}/5`
        }
      ]
    }));

    const averages = {
      discrepancies100: Math.round((attempts.reduce((sum, a) => sum + a.discrepancies100, 0) / attempts.length) * 100) / 100,
      questionDiscrepancies100: Math.round((attempts.reduce((sum, a) => sum + a.questionDiscrepancies100, 0) / attempts.length) * 100) / 100,
      zpfDiscrepancies: Math.round((attempts.reduce((sum, a) => sum + a.zpfDiscrepancies, 0) / attempts.length) * 100) / 100,
      zpfQuestionDiscrepancies: Math.round((attempts.reduce((sum, a) => sum + a.zpfQuestionDiscrepancies, 0) / attempts.length) * 100) / 100,
      rangeDiscrepancies: Math.round((attempts.reduce((sum, a) => sum + a.rangeDiscrepancies, 0) / attempts.length) * 100) / 100,
      rangeQuestionDiscrepancies: Math.round((attempts.reduce((sum, a) => sum + a.rangeQuestionDiscrepancies, 0) / attempts.length) * 100) / 100,
      totalScore: Math.round((attempts.reduce((sum, a) => sum + a.totalScore, 0) / attempts.length) * 100) / 100
    };

    return {
      model,
      averages,
      attempts
    };
  });

  const questions = [
    { number: 1, text: 'What is 2+2?' },
    { number: 2, text: 'Solve 10-5' }
  ];

  return {
    modelResults,
    questions
  };
};