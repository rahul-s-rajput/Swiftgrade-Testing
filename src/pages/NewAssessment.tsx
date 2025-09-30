import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertCircle, Upload, Sparkles } from 'lucide-react';
import { useAssessments } from '../context/AssessmentContext';
import { FileUpload } from '../components/FileUploadHTML5';
import { MultiSelect } from '../components/MultiSelect';
import { NumberInput } from '../components/NumberInput';
import { useOpenRouterModels } from '../hooks/useOpenRouterModels';
import { ReasoningLevel } from '../types';

export const NewAssessment: React.FC = () => {
  const navigate = useNavigate();
  const { addAssessment } = useAssessments();
  const { models, loading: modelsLoading, error: modelsError, refetch: refetchModels, modelInfoById } = useOpenRouterModels();

  // Only show models that can accept image inputs for this workflow
  const imageModels = useMemo(() =>
    models.filter(m => !!modelInfoById?.[m.id]?.supportsImage),
    [models, modelInfoById]
  );

  // If any previously selected model isn't image-capable, remove it silently
  useEffect(() => {
    if (!imageModels.length) return;
    const allowed = new Set(imageModels.map(m => m.id));
    setFormData(prev => {
      const filtered = prev.selectedModels.filter(id => allowed.has(id));
      if (filtered.length === prev.selectedModels.length) return prev;
      return { ...prev, selectedModels: filtered };
    });
  }, [imageModels]);

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

  // Story 4: Reasoning configuration per selected selection (supports duplicates)
  const [reasoningBySelection, setReasoningBySelection] = useState<Array<{ level: ReasoningLevel; tokens?: number }>>([]); // Using ReasoningLevel from types

  // Popover state for per-chip reasoning configuration
  const [chipMenu, setChipMenu] = useState<{ index: number | null; id: string | null; anchor: { left: number; top: number } | null }>({ index: null, id: null, anchor: null });
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const chipMenuContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (chipMenu.index === null) return;
      const target = e.target as Node;
      if (popoverRef.current && !popoverRef.current.contains(target)) {
        setChipMenu({ index: null, id: null, anchor: null });
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [chipMenu.index]);

  // Ensure reasoning state stays in sync with selected models (index-aligned)
  useEffect(() => {
    setReasoningBySelection(prev => formData.selectedModels.map((_, i) => prev[i] || { level: 'none' }));
  }, [formData.selectedModels]);

  const renderOptionMeta = (id: string) => {
    const raw = modelInfoById?.[id]?.raw as { context_length?: number; pricing?: { prompt?: number | string; completion?: number | string } } | undefined;
    if (!raw) return null;
    const p = raw.pricing;
    if (!p) return null;
    const fmt = (val: number | string | undefined) => {
      if (val === undefined || val === null) return null;
      const num = typeof val === 'number' ? val : Number(val);
      if (!isFinite(num)) return null;
      const usdPerMillion = num * 1_000_000;
      const display = usdPerMillion.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      return `$${display}/M`;
    };
    const input = fmt(p.prompt);
    const output = fmt(p.completion);
    const parts: string[] = [];
    if (input) parts.push(`${input} input tokens`);
    if (output) parts.push(`${output} output tokens`);
    if (parts.length === 0) return null;
    return <span>{parts.join(' | ')}</span>;
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Test name is required';
    }

    if (formData.studentImages.length === 0) {
      newErrors.studentImages = 'Please upload at least one student test image';
    }

    // Answer key images are optional - system supports grading without answer keys

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
      // Log final reasoning configuration before submission
      console.log('[NewAssessment] Submitting assessment with reasoning configuration:', {
        assessmentName: formData.name,
        selectedModels: formData.selectedModels,
        reasoningBySelection: reasoningBySelection,
        modelReasoningDetails: formData.selectedModels.map((modelId, index) => {
          const modelInfo = modelInfoById?.[modelId];
          const model = models.find(m => m.id === modelId);
          const reasoning = reasoningBySelection[index];
          return {
            modelId,
            modelName: model?.name || 'Unknown',
            modelIndex: index,
            supportsReasoning: modelInfo?.supportsReasoning || false,
            reasoningType: modelInfo?.reasoningType || 'none',
            reasoningLevel: reasoning?.level || 'none',
            reasoningTokens: reasoning?.tokens,
            willUseReasoning: reasoning?.level !== 'none' && (modelInfo?.supportsReasoning || false)
          };
        })
      });

      // Fire-and-forget: start assessment creation and grading in background
      void addAssessment({
        name: formData.name,
        studentImages: formData.studentImages,
        answerKeyImages: formData.answerKeyImages,
        questions: formData.questions,
        humanGrades: formData.humanGrades,
        selectedModels: formData.selectedModels,
        iterations: formData.iterations,
        reasoningBySelection: reasoningBySelection,
        status: 'running'
      });

      // Immediately navigate back to dashboard to show running state
      navigate('/');
    } catch (error) {
      console.error('Failed to create assessment:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full">
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
      <div className="bg-white/70 backdrop-blur-sm shadow-xl rounded-2xl border border-white/50 overflow-visible">
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
                  Question List (JSON Format)
                </label>
                <textarea
                  id="questions"
                  rows={6}
                  value={formData.questions}
                  onChange={(e) => setFormData({ ...formData, questions: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 ${
                    errors.questions ? 'border-red-300 focus:border-red-500' : 'border-slate-300 focus:border-blue-500'
                  } bg-white/80 backdrop-blur-sm resize-none`}
                  placeholder='[{"question_number":"DES.1","max_mark":1},{"question_number":"DES.2","max_mark":1}]'
                />
                <p className="text-xs text-slate-500 mt-1">Enter a JSON array with question_number and max_mark for each question</p>
                {errors.questions && (
                  <div className="mt-2 flex items-center text-sm text-red-600">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {errors.questions}
                  </div>
                )}
              </div>

              {/* AI Model Selection */}
              <div>
                {modelsLoading ? (
                  <div className="flex items-center text-slate-600">
                    <Upload className="w-4 h-4 mr-2 animate-spin" />
                    Loading models...
                  </div>
                ) : modelsError ? (
                  <div className="flex items-center justify-between gap-3 p-3 border border-red-200 rounded-lg bg-red-50">
                    <div className="flex items-center text-sm text-red-700">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      {modelsError}
                    </div>
                    <button
                      type="button"
                      onClick={refetchModels}
                      className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
                    >
                      Retry
                    </button>
                  </div>
                ) : (
                  <div ref={chipMenuContainerRef} className="relative">
                  <MultiSelect
                    label="Select AI Models for Testing"
                    options={imageModels}
                    selectedValues={formData.selectedModels}
                    onChange={(values) => {
                      const prev = formData.selectedModels;
                      // Append case (allowDuplicates adds to end)
                      if (values.length === prev.length + 1 && prev.every((v, i) => v === values[i])) {
                        const newModelId = values[values.length - 1];
                        const modelInfo = modelInfoById?.[newModelId];
                        const model = models.find(m => m.id === newModelId);
                        console.log('[NewAssessment] Model selected:', {
                          modelId: newModelId,
                          modelName: model?.name || 'Unknown',
                          supportsReasoning: modelInfo?.supportsReasoning || false,
                          reasoningType: modelInfo?.reasoningType || 'none',
                          totalSelectedModels: values.length
                        });
                        setFormData({ ...formData, selectedModels: values });
                        setReasoningBySelection(prevReasoning => [...prevReasoning, { level: 'none' }]);
                        return;
                      }
                      // Removal case: detect removed index by first mismatch
                      if (values.length + 1 === prev.length) {
                        let removedIndex = values.length; // default: last
                        for (let i = 0; i < values.length; i++) {
                          if (values[i] !== prev[i]) { removedIndex = i; break; }
                        }
                        const removedModelId = prev[removedIndex];
                        const model = models.find(m => m.id === removedModelId);
                        console.log('[NewAssessment] Model removed:', {
                          modelId: removedModelId,
                          modelName: model?.name || 'Unknown',
                          removedIndex,
                          remainingModels: values.length
                        });
                        setFormData({ ...formData, selectedModels: values });
                        setReasoningBySelection(prevReasoning => prevReasoning.filter((_, i) => i !== removedIndex));
                        return;
                      }
                      // Fallback: length unchanged or other reorder - realign by index
                      console.log('[NewAssessment] Models reordered or bulk changed:', {
                        previousCount: prev.length,
                        newCount: values.length,
                        previousModels: prev.map(id => ({ id, name: models.find(m => m.id === id)?.name || 'Unknown' })),
                        newModels: values.map(id => ({ id, name: models.find(m => m.id === id)?.name || 'Unknown' }))
                      });
                      setFormData({ ...formData, selectedModels: values });
                      setReasoningBySelection(prevReasoning => values.map((_, i) => prevReasoning[i] || { level: 'none' }));
                    }}
                    placeholder="Choose models to evaluate..."
                    dropdownPlacement="right"
                    renderOptionMeta={renderOptionMeta}
                    allowDuplicates
                    maxPerOption={4}
                    shouldShowChipMenuAt={(id, _index) => !!modelInfoById?.[id]?.supportsReasoning}
                    getChipBadgeAt={(_id, index) => {
                       const conf = reasoningBySelection[index];
                       if (!conf || conf.level === 'none') return (
                         <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/70 text-slate-600 border">None</span>
                       );
                       return (
                         <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/70 text-slate-700 border">{conf.level.charAt(0).toUpperCase() + conf.level.slice(1)}</span>
                       );
                     }}
                    onChipMenuRequestAt={(id, index, rect) => {
                      const containerRect = chipMenuContainerRef.current?.getBoundingClientRect();
                      const left = containerRect ? (rect.right - containerRect.left + 6) : (rect.right + 6);
                      const top = containerRect ? (rect.top - containerRect.top + rect.height / 2) : (rect.top + rect.height / 2);
                      setChipMenu({ index, id, anchor: { left, top } });
                    }}
                  />
                  {/* Popover for per-chip reasoning configuration */}
                  {chipMenu.index !== null && chipMenu.anchor && (
                    <div
                      ref={popoverRef}
                      className="absolute z-50 bg-white border rounded-lg shadow-lg p-2 w-56 transform -translate-y-1/2"
                      style={{ left: chipMenu.anchor.left, top: chipMenu.anchor.top }}
                    >
                      {(() => {
                        const idx = chipMenu.index as number;
                        const id = (chipMenu.id as string) || formData.selectedModels[idx];
                        const info = modelInfoById?.[id];
                        const supportsReasoning = info?.supportsReasoning ?? false;
                        const conf = reasoningBySelection[idx] || { level: 'none' as ReasoningLevel };
                        const options: ReasoningLevel[] = !supportsReasoning
                          ? ['none']
                          : ['none', 'low', 'medium', 'high'];
                        const currentLevel: ReasoningLevel = (options.includes(conf.level) ? conf.level : 'none');
                        return (
                          <div className="space-y-2">
                            {supportsReasoning ? (
                              <>
                                <div className="flex flex-col gap-1">
                                  {options.filter(opt => opt !== 'custom').map(opt => (
                                    <button
                                      key={opt}
                                      type="button"
                                      className={`w-full text-left px-2 py-1 rounded text-sm hover:bg-slate-50 ${currentLevel === opt ? 'bg-slate-100' : ''}`}
                                      onClick={() => {
                                        const modelId = formData.selectedModels[idx];
                                          const modelInfo = modelInfoById?.[modelId];
                                          const model = models.find(m => m.id === modelId);
                                          console.log('[NewAssessment] Reasoning level changed:', {
                                            modelId,
                                            modelName: model?.name || 'Unknown',
                                            modelIndex: idx,
                                            previousLevel: reasoningBySelection[idx]?.level || 'none',
                                            newLevel: opt,
                                            reasoningType: modelInfo?.reasoningType || 'none'
                                          });
                                        setReasoningBySelection(prev => {
                                          const next = [...prev];
                                          next[idx] = { level: opt };
                                          return next;
                                        });
                                        setChipMenu({ index: null, id: null, anchor: null });
                                      }}
                                    >
                                      {opt.charAt(0).toUpperCase() + opt.slice(1)}
                                    </button>
                                  ))}

                                </div>
                              </>
                            ) : (
                              <div className="text-xs text-slate-500 px-2 py-1">Reasoning not supported</div>
                            )}
                          </div>
                        );
                      })()}
                    </div>
                  )}
                  </div>
                )}
                {formData.selectedModels.length > 0 && (
                  <div className="mt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, selectedModels: [] })}
                      className="text-sm text-slate-600 hover:text-slate-900 underline"
                    >
                      Clear all
                    </button>
                  </div>
                )}
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
                  label="Upload Answer Key Images (Optional)"
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
                  Human Graded Marks (JSON Format)
                </label>
                <textarea
                  id="humanGrades"
                  rows={6}
                  value={formData.humanGrades}
                  onChange={(e) => setFormData({ ...formData, humanGrades: e.target.value })}
                  className={`w-full px-4 py-3 border rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 ${
                    errors.humanGrades ? 'border-red-300 focus:border-red-500' : 'border-slate-300 focus:border-blue-500'
                  } bg-white/80 backdrop-blur-sm resize-none`}
                  placeholder='{"Q1":8,"Q2":6,"Q3":18}'
                />
                <p className="text-xs text-slate-500 mt-1">Enter a JSON object with question_id as keys and marks as values</p>
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