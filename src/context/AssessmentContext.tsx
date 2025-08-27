import React, { createContext, useContext, useState, useCallback } from 'react';
import { Assessment, AssessmentResults } from '../types';
import { generateMockResults } from '../utils/mockData';

interface AssessmentContextType {
  assessments: Assessment[];
  addAssessment: (assessment: Omit<Assessment, 'id' | 'date'>) => Promise<void>;
  deleteAssessment: (id: string) => void;
  getAssessment: (id: string) => Assessment | undefined;
  updateAssessmentStatus: (id: string, status: 'running' | 'complete', results?: AssessmentResults) => void;
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

export const useAssessments = () => {
  const context = useContext(AssessmentContext);
  if (!context) {
    throw new Error('useAssessments must be used within an AssessmentProvider');
  }
  return context;
};

export const AssessmentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [assessments, setAssessments] = useState<Assessment[]>([
    {
      id: '1',
      name: 'Math Quiz Grade 5',
      date: '2024-01-15',
      status: 'complete',
      studentImages: [],
      answerKeyImages: [],
      questions: 'Q1: What is 2+2?\nQ2: Solve 10-5',
      humanGrades: 'Q1: 4/5\nQ2: 5/5',
      selectedModels: ['gpt-4', 'claude-3'],
      iterations: 3,
      results: generateMockResults(['gpt-4', 'claude-3'], 3)
    },
    {
      id: '2',
      name: 'Science Test - Physics',
      date: '2024-01-14',
      status: 'running',
      studentImages: [],
      answerKeyImages: [],
      questions: 'Q1: Explain gravity\nQ2: What is Newton\'s first law?',
      humanGrades: 'Q1: 8/10\nQ2: 9/10',
      selectedModels: ['llama-2', 'claude-3'],
      iterations: 2
    }
  ]);

  const addAssessment = useCallback(async (assessmentData: Omit<Assessment, 'id' | 'date'>) => {
    const newAssessment: Assessment = {
      ...assessmentData,
      id: Date.now().toString(),
      date: new Date().toISOString().split('T')[0],
      status: 'running'
    };

    setAssessments(prev => [...prev, newAssessment]);

    // Simulate API call and processing time
    setTimeout(() => {
      const results = generateMockResults(assessmentData.selectedModels, assessmentData.iterations);
      setAssessments(prev => 
        prev.map(assessment => 
          assessment.id === newAssessment.id 
            ? { ...assessment, status: 'complete', results }
            : assessment
        )
      );
    }, 3000 + Math.random() * 2000); // 3-5 second delay
  }, []);

  const deleteAssessment = useCallback((id: string) => {
    setAssessments(prev => prev.filter(assessment => assessment.id !== id));
  }, []);

  const getAssessment = useCallback((id: string) => {
    return assessments.find(assessment => assessment.id === id);
  }, [assessments]);

  const updateAssessmentStatus = useCallback((id: string, status: 'running' | 'complete', results?: AssessmentResults) => {
    setAssessments(prev =>
      prev.map(assessment =>
        assessment.id === id
          ? { ...assessment, status, results: results || assessment.results }
          : assessment
      )
    );
  }, []);

  return (
    <AssessmentContext.Provider value={{
      assessments,
      addAssessment,
      deleteAssessment,
      getAssessment,
      updateAssessmentStatus
    }}>
      {children}
    </AssessmentContext.Provider>
  );
};