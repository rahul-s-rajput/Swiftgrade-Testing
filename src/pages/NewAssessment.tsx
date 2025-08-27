import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertCircle, Upload, Sparkles } from 'lucide-react';
import { useAssessments } from '../context/AssessmentContext';
import { FileUpload } from '../components/FileUpload';
import { MultiSelect } from '../components/MultiSelect';
import { NumberInput } from '../components/NumberInput';
import { mockAIModels } from '../utils/mockData';

export const NewAssessment: React.FC = () => {
  const navigate = useNavigate();
  const { addAssessment } = useAssessments();

  const [formData, setFormData] = useState({
    name: '',
    studentImages: [] as File[],
    answerKeyImages: [] as File[],
    questions: '',
    humanGrades: '',
    selectedModels: [] as string[],
    iterations: 1
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Test name is required';
    }

    if (formData.studentImages.length === 0) {
      newErrors.studentImages = 'Please upload at least one student test image';
    }

    if (formData.answerKeyImages.length === 0) {
      newErrors.answerKeyImages = 'Please upload at least one answer key image';
    }

    if (!formData.questions.trim()) {
      newErrors.questions = 'Question list is required';
    }

    if (!formData.humanGrades.trim()) {
      newErrors.humanGrades = 'Human graded marks are required';
    }

    if (formData.selectedModels.length === 0) {
      newErrors.selectedModels = 'Please select at least one AI model';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await addAssessment({
        name: formData.name,
        studentImages: formData.studentImages,
        answerKeyImages: formData.answerKeyImages,
        questions: formData.questions,
        humanGrades: formData.humanGrades,
        selectedModels: formData.selectedModels,
        iterations: formData.iterations,
        status: 'running'
      });

      navigate('/');
    } catch (error) {
      console.error('Failed to create assessment:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-slate-600 hover:text-slate-900 mb-6 transition-all duration-200 hover:scale-105"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Dashboard
        </button>
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-2xl mb-6 shadow-lg">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent mb-2">
            Create New Assessment
          </h2>
          <p className="text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Set up a comprehensive AI grading test with your custom parameters and models
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-white/70 backdrop-blur-sm shadow-xl rounded-2xl border border-white/50 overflow-hidden">
        <form onSubmit={handleSubmit} className="p-8">
          {/* Test Name - Full Width */}
          <div className="mb-8">
            <label htmlFor="testName" className="block text-sm font-semibold text-slate-700 mb-3">
              Assessment Name
            </label>
            <input
              type="text"
              id="testName"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 ${
                errors.name ? 'border-red-300 focus:border-red-500' : 'border-slate-300 focus:border-blue-500'
              } bg-white/80 backdrop-blur-sm`}
              placeholder="e.g., Advanced Calculus Final Exam - Spring 2024"
            />
            {errors.name && (
              <div className="mt-2 flex items-center text-sm text-red-600">
                <AlertCircle className="w-4 h-4 mr-1" />
                {errors.name}
              </div>
            )}
          </div>

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left Column */}
            <div className="space-y-8">
              {/* Student Test Images */}
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6">
                <FileUpload
                  label="Upload Student Test Images"
                  files={formData.studentImages}
                  onChange={(files) => setFormData({ ...formData, studentImages: files })}
                />
                {errors.studentImages && (
                  <div className="mt-2 flex items-center text-sm text-red-600">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.studentImages}
                  </div>
                )}
              </div>

              {/* Questions */}
              <div>
                <label htmlFor="questions" className="block text-sm font-semibold text-slate-700 mb-3">
                  Question List
                </label>
                <textarea
                  id="questions"
                  rows={6}
                  value={formData.questions}
                  onChange={(e) => setFormData({ ...formData, questions: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 ${
                    errors.questions ? 'border-red-300 focus:border-red-500' : 'border-slate-300 focus:border-blue-500'
                  } bg-white/80 backdrop-blur-sm resize-none`}
                  placeholder="Q1: What is the derivative of x²?&#10;Q2: Solve the integral ∫x dx&#10;Q3: Explain the concept of limits"
                />
                {errors.questions && (
                  <div className="mt-2 flex items-center text-sm text-red-600">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.questions}
                  </div>
                )}
              </div>

              {/* AI Model Selection */}
              <div>
                <MultiSelect
                  label="Select AI Models for Testing"
                  options={mockAIModels}
                  selectedValues={formData.selectedModels}
                  onChange={(values) => setFormData({ ...formData, selectedModels: values })}
                  placeholder="Choose models to evaluate..."
                />
                {errors.selectedModels && (
                  <div className="mt-2 flex items-center text-sm text-red-600">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.selectedModels}
                  </div>
                )}
              </div>
            </div>

            {/* Right Column */}
            <div className="space-y-8">
              {/* Answer Key Images */}
              <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-6">
                <FileUpload
                  label="Upload Answer Key Images"
                  files={formData.answerKeyImages}
                  onChange={(files) => setFormData({ ...formData, answerKeyImages: files })}
                />
                {errors.answerKeyImages && (
                  <div className="mt-2 flex items-center text-sm text-red-600">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.answerKeyImages}
                  </div>
                )}
              </div>

              {/* Human Grades */}
              <div>
                <label htmlFor="humanGrades" className="block text-sm font-semibold text-slate-700 mb-3">
                  Human Graded Marks (Reference)
                </label>
                <textarea
                  id="humanGrades"
                  rows={6}
                  value={formData.humanGrades}
                  onChange={(e) => setFormData({ ...formData, humanGrades: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 ${
                    errors.humanGrades ? 'border-red-300 focus:border-red-500' : 'border-slate-300 focus:border-blue-500'
                  } bg-white/80 backdrop-blur-sm resize-none`}
                  placeholder="Q1: 8/10 - Good understanding of derivatives&#10;Q2: 6/10 - Correct method, minor calculation error&#10;Q3: 9/10 - Excellent explanation"
                />
                {errors.humanGrades && (
                  <div className="mt-2 flex items-center text-sm text-red-600">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.humanGrades}
                  </div>
                )}
              </div>

              {/* Iterations */}
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6">
                <NumberInput
                  label="Testing Iterations"
                  value={formData.iterations}
                  onChange={(value) => setFormData({ ...formData, iterations: value })}
                  min={1}
                  max={10}
                />
                <p className="text-sm text-slate-600 mt-3">
                  Multiple iterations help ensure consistent AI performance evaluation
                </p>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="mt-10 flex justify-center">
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-1 min-w-48"
            >
              {isSubmitting ? (
                <div className="flex items-center justify-center">
                  <Upload className="w-5 h-5 mr-2 animate-spin" />
                  Processing Assessment...
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <Sparkles className="w-5 h-5 mr-2" />
                  Launch Assessment
                </div>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};