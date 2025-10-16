import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertCircle, Upload, Sparkles, ArrowRight, Link2 } from 'lucide-react';
import { useAssessments } from '../context/AssessmentContext';
import { FileUpload } from '../components/FileUploadHTML5';
import { MultiSelect } from '../components/MultiSelect';
import { NumberInput } from '../components/NumberInput';
import { useOpenRouterModels } from '../hooks/useOpenRouterModels';
import { ReasoningLevel } from '../types';
import { getTemplates, Template } from '../utils/api';

export const NewAssessment: React.FC = () => {
  const navigate = useNavigate();
  const { addAssessment } = useAssessments();
  const { models, loading: modelsLoading, error: modelsError, refetch: refetchModels, modelInfoById } = useOpenRouterModels();

  const imageModels = useMemo(() =>
    models.filter(m => !!modelInfoById?.[m.id]?.supportsImage),
    [models, modelInfoById]
  );

  const [formData, setFormData] = useState({
    name: '',
    studentImages: [] as File[],
    answerKeyImages: [] as File[],
    rubricImages: [] as File[],
    questions: '',
    humanGrades: '',
    iterations: 1
  });

  // Independent model selections (not paired until submission)
  const [rubricModels, setRubricModels] = useState<string[]>([]);
  const [assessmentModels, setAssessmentModels] = useState<string[]>([]);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [rubricReasoningBySelection, setRubricReasoningBySelection] = useState<Array<{ level: ReasoningLevel; tokens?: number }>>([]);
  const [assessmentReasoningBySelection, setAssessmentReasoningBySelection] = useState<Array<{ level: ReasoningLevel; tokens?: number }>>([]);

  // Template selection state
  const [rubricTemplates, setRubricTemplates] = useState<Template[]>([]);
  const [assessmentTemplates, setAssessmentTemplates] = useState<Template[]>([]);
  const [selectedRubricTemplate, setSelectedRubricTemplate] = useState<string>('');
  const [selectedAssessmentTemplate, setSelectedAssessmentTemplate] = useState<string>('');

  const [chipMenu, setChipMenu] = useState<{ 
    index: number | null; 
    id: string | null; 
    anchor: { left: number; top: number } | null; 
    type: 'rubric' | 'assessment' | null 
  }>({ index: null, id: null, anchor: null, type: null });
  
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const rubricContainerRef = useRef<HTMLDivElement | null>(null);
  const assessmentContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (chipMenu.index === null) return;
      const target = e.target as Node;
      if (popoverRef.current && !popoverRef.current.contains(target)) {
        setChipMenu({ index: null, id: null, anchor: null, type: null });
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [chipMenu.index]);

  useEffect(() => {
    setRubricReasoningBySelection(prev => 
      rubricModels.map((_, i) => prev[i] || { level: 'none' })
    );
  }, [rubricModels.length]);

  useEffect(() => {
    setAssessmentReasoningBySelection(prev => 
      assessmentModels.map((_, i) => prev[i] || { level: 'none' })
    );
  }, [assessmentModels.length]);

  // Load templates on mount
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const [rubricRes, assessmentRes] = await Promise.all([
          getTemplates('rubric'),
          getTemplates('assessment')
        ]);
        setRubricTemplates(rubricRes.templates);
        setAssessmentTemplates(assessmentRes.templates);
        
        // Auto-select default template
        setSelectedRubricTemplate('default');
        setSelectedAssessmentTemplate('default');
      } catch (e) {
        console.error('Failed to load templates:', e);
      }
    };
    loadTemplates();
  }, []);

  // Create model pairs from independent selections
  const modelPairs = useMemo(() => {
    const maxLength = Math.max(rubricModels.length, assessmentModels.length);
    return Array.from({ length: maxLength }, (_, i) => ({
      rubricModel: rubricModels[i] || '',
      assessmentModel: assessmentModels[i] || '',
      rubricReasoning: rubricReasoningBySelection[i],
      assessmentReasoning: assessmentReasoningBySelection[i]
    }));
  }, [rubricModels, assessmentModels, rubricReasoningBySelection, assessmentReasoningBySelection]);

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

    if (!formData.questions.trim()) {
      newErrors.questions = 'Question list is required';
    }

    if (!formData.humanGrades.trim()) {
      newErrors.humanGrades = 'Human graded marks are required';
    }

    if (modelPairs.length === 0 || !modelPairs.some(p => p.rubricModel && p.assessmentModel)) {
      newErrors.modelPairs = 'Please select at least one complete model pair (both rubric and assessment models)';
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
      console.log('[NewAssessment] Submitting assessment with model pairs:', {
        assessmentName: formData.name,
        modelPairs: modelPairs,
      });

      void addAssessment({
        name: formData.name,
        studentImages: formData.studentImages,
        answerKeyImages: formData.answerKeyImages,
        rubricImages: formData.rubricImages,
        questions: formData.questions,
        humanGrades: formData.humanGrades,
        modelPairs: modelPairs,
        selectedModels: [],
        iterations: formData.iterations,
        reasoningBySelection: [],
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

              {/* Rubric Images */}
              <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6">
                <FileUpload
                  label="Upload Grading Rubric Images"
                  files={formData.rubricImages}
                  onChange={(files) => setFormData({ ...formData, rubricImages: files })}
                />
                <p className="text-xs text-slate-500 mt-2">
                  Upload images of the grading rubric that will guide the AI assessment
                </p>
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

              {/* Testing Iterations */}
              <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-6">
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

          {/* Template Selection */}
          <div className="mt-8 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
            <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-blue-600" />
              Prompt Templates
            </h3>
            <p className="text-sm text-slate-600 mb-4">
              Select which prompt templates to use for rubric analysis and assessment grading.
            </p>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Rubric Template */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Rubric Template
                </label>
                <select
                  value={selectedRubricTemplate}
                  onChange={(e) => setSelectedRubricTemplate(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 px-3 py-2 text-sm bg-white"
                >
                  {rubricTemplates.map(template => (
                    <option key={template.name} value={template.name}>
                      {template.display_name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  Template for analyzing grading rubric images
                </p>
              </div>

              {/* Assessment Template */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Assessment Template
                </label>
                <select
                  value={selectedAssessmentTemplate}
                  onChange={(e) => setSelectedAssessmentTemplate(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 px-3 py-2 text-sm bg-white"
                >
                  {assessmentTemplates.map(template => (
                    <option key={template.name} value={template.name}>
                      {template.display_name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  Template for grading student assessments
                </p>
              </div>
            </div>
          </div>

          {/* Model Selectors - Side by Side at Same Level */}
          <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Rubric Model Selector */}
            <div ref={rubricContainerRef} className="relative bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6">
              <label className="block text-sm font-semibold text-slate-700 mb-3">
                Select Grading Rubric Models
              </label>
              <p className="text-xs text-slate-500 mb-3">
                These models will analyze the grading rubric images first
              </p>
              {modelsLoading ? (
                <div className="flex items-center text-slate-600">
                  <Upload className="w-4 h-4 mr-2 animate-spin" />
                  Loading models...
                </div>
              ) : modelsError ? (
                <div className="p-3 border border-red-200 rounded-lg bg-red-50">
                  <div className="flex items-center text-sm text-red-700">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {modelsError}
                  </div>
                  <button
                    type="button"
                    onClick={refetchModels}
                    className="mt-2 px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
                  >
                    Retry
                  </button>
                </div>
              ) : (
                <MultiSelect
                  label=""
                  options={imageModels}
                  selectedValues={rubricModels}
                  onChange={setRubricModels}
                  placeholder="Choose rubric analysis models..."
                  dropdownPlacement="top"
                  renderOptionMeta={renderOptionMeta}
                  allowDuplicates
                  maxPerOption={4}
                  shouldShowChipMenuAt={(id, _index) => !!modelInfoById?.[id]?.supportsReasoning}
                  getChipBadgeAt={(_id, index) => {
                    const conf = rubricReasoningBySelection[index];
                    if (!conf || conf.level === 'none') return (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/70 text-slate-600 border">None</span>
                    );
                    return (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 border border-purple-300">{conf.level.charAt(0).toUpperCase() + conf.level.slice(1)}</span>
                    );
                  }}
                  onChipMenuRequestAt={(id, index, rect) => {
                    const containerRect = rubricContainerRef.current?.getBoundingClientRect();
                    const left = containerRect ? (rect.right - containerRect.left + 6) : (rect.right + 6);
                    const top = containerRect ? (rect.top - containerRect.top + rect.height / 2) : (rect.top + rect.height / 2);
                    setChipMenu({ index, id, anchor: { left, top }, type: 'rubric' });
                  }}
                />
              )}
              {/* Reasoning Configuration Popover for Rubric Models */}
              {chipMenu.index !== null && chipMenu.anchor && chipMenu.type === 'rubric' && (
                <div
                  ref={popoverRef}
                  className="absolute z-50 bg-white border rounded-lg shadow-lg p-2 w-56 transform -translate-y-1/2"
                  style={{ left: chipMenu.anchor.left, top: chipMenu.anchor.top }}
                >
                  {(() => {
                    const idx = chipMenu.index as number;
                    const id = rubricModels[idx];
                    const info = modelInfoById?.[id];
                    const supportsReasoning = info?.supportsReasoning ?? false;
                    const conf = rubricReasoningBySelection[idx] || { level: 'none' as ReasoningLevel };
                    const options: ReasoningLevel[] = !supportsReasoning
                      ? ['none']
                      : ['none', 'low', 'medium', 'high'];
                    const currentLevel: ReasoningLevel = (options.includes(conf.level) ? conf.level : 'none');
                    
                    return (
                      <div className="space-y-2">
                        <div className="text-xs font-semibold text-slate-600 px-2 pb-1 border-b">
                          Rubric Model Reasoning
                        </div>
                        {supportsReasoning ? (
                          <div className="flex flex-col gap-1">
                            {options.filter(opt => opt !== 'custom').map(opt => (
                              <button
                                key={opt}
                                type="button"
                                className={`w-full text-left px-2 py-1 rounded text-sm hover:bg-slate-50 ${currentLevel === opt ? 'bg-slate-100' : ''}`}
                                onClick={() => {
                                  setRubricReasoningBySelection(prev => {
                                    const next = [...prev];
                                    next[idx] = { level: opt };
                                    return next;
                                  });
                                  setChipMenu({ index: null, id: null, anchor: null, type: null });
                                }}
                              >
                                {opt.charAt(0).toUpperCase() + opt.slice(1)}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-slate-500 px-2 py-1">Reasoning not supported</div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>

            {/* Assessment Model Selector */}
            <div ref={assessmentContainerRef} className="relative bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-6">
              <label className="block text-sm font-semibold text-slate-700 mb-3">
                Select Assessment Models
              </label>
              <p className="text-xs text-slate-500 mb-3">
                These models will grade using the rubric from paired models (left side)
              </p>
              {modelsLoading ? (
                <div className="flex items-center text-slate-600">
                  <Upload className="w-4 h-4 mr-2 animate-spin" />
                  Loading models...
                </div>
              ) : modelsError ? (
                <div className="p-3 border border-red-200 rounded-lg bg-red-50">
                  <div className="flex items-center text-sm text-red-700">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    {modelsError}
                  </div>
                </div>
              ) : (
                <MultiSelect
                  label=""
                  options={imageModels}
                  selectedValues={assessmentModels}
                  onChange={setAssessmentModels}
                  placeholder="Choose assessment models..."
                  dropdownPlacement="top"
                  renderOptionMeta={renderOptionMeta}
                  allowDuplicates
                  maxPerOption={4}
                  shouldShowChipMenuAt={(id, _index) => !!modelInfoById?.[id]?.supportsReasoning}
                  getChipBadgeAt={(_id, index) => {
                    const conf = assessmentReasoningBySelection[index];
                    if (!conf || conf.level === 'none') return (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/70 text-slate-600 border">None</span>
                    );
                    return (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 border border-blue-300">{conf.level.charAt(0).toUpperCase() + conf.level.slice(1)}</span>
                    );
                  }}
                  onChipMenuRequestAt={(id, index, rect) => {
                    const containerRect = assessmentContainerRef.current?.getBoundingClientRect();
                    const left = containerRect ? (rect.right - containerRect.left + 6) : (rect.right + 6);
                    const top = containerRect ? (rect.top - containerRect.top + rect.height / 2) : (rect.top + rect.height / 2);
                    setChipMenu({ index, id, anchor: { left, top }, type: 'assessment' });
                  }}
                />
              )}
              {/* Reasoning Configuration Popover for Assessment Models */}
              {chipMenu.index !== null && chipMenu.anchor && chipMenu.type === 'assessment' && (
                <div
                  ref={popoverRef}
                  className="absolute z-50 bg-white border rounded-lg shadow-lg p-2 w-56 transform -translate-y-1/2"
                  style={{ left: chipMenu.anchor.left, top: chipMenu.anchor.top }}
                >
                  {(() => {
                    const idx = chipMenu.index as number;
                    const id = assessmentModels[idx];
                    const info = modelInfoById?.[id];
                    const supportsReasoning = info?.supportsReasoning ?? false;
                    const conf = assessmentReasoningBySelection[idx] || { level: 'none' as ReasoningLevel };
                    const options: ReasoningLevel[] = !supportsReasoning
                      ? ['none']
                      : ['none', 'low', 'medium', 'high'];
                    const currentLevel: ReasoningLevel = (options.includes(conf.level) ? conf.level : 'none');
                    
                    return (
                      <div className="space-y-2">
                        <div className="text-xs font-semibold text-slate-600 px-2 pb-1 border-b">
                          Assessment Model Reasoning
                        </div>
                        {supportsReasoning ? (
                          <div className="flex flex-col gap-1">
                            {options.filter(opt => opt !== 'custom').map(opt => (
                              <button
                                key={opt}
                                type="button"
                                className={`w-full text-left px-2 py-1 rounded text-sm hover:bg-slate-50 ${currentLevel === opt ? 'bg-slate-100' : ''}`}
                                onClick={() => {
                                  setAssessmentReasoningBySelection(prev => {
                                    const next = [...prev];
                                    next[idx] = { level: opt };
                                    return next;
                                  });
                                  setChipMenu({ index: null, id: null, anchor: null, type: null });
                                }}
                              >
                                {opt.charAt(0).toUpperCase() + opt.slice(1)}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-slate-500 px-2 py-1">Reasoning not supported</div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>
          </div>

          {/* Model Pairs Preview - Full Width */}
          {modelPairs.length > 0 && modelPairs.some(p => p.rubricModel && p.assessmentModel) && (
            <div className="mt-8 p-6 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-300 shadow-md">
              <h4 className="text-base font-bold text-slate-800 mb-4 flex items-center">
                <Link2 className="w-5 h-5 mr-2 text-blue-600" />
                Model Pairs Configured
              </h4>
              <div className="space-y-3">
                {modelPairs.map((pair, idx) => {
                  if (!pair.rubricModel || !pair.assessmentModel) return null;
                  const rubricModel = models.find(m => m.id === pair.rubricModel);
                  const assessmentModel = models.find(m => m.id === pair.assessmentModel);
                  return (
                    <div key={idx} className="flex items-center gap-3 p-4 bg-white rounded-lg border border-blue-200 shadow-sm">
                      <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-purple-200 to-blue-200 border-2 border-blue-400 font-bold text-slate-700">
                        {idx + 1}
                      </span>
                      <div className="flex items-center gap-3 flex-1">
                        <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-md font-semibold text-sm border border-purple-300">
                          {rubricModel?.name || pair.rubricModel}
                        </span>
                        <ArrowRight className="w-5 h-5 text-blue-600 flex-shrink-0" />
                        <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-md font-semibold text-sm border border-blue-300">
                          {assessmentModel?.name || pair.assessmentModel}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {errors.modelPairs && (
            <div className="mt-4 flex items-center text-sm text-red-600">
              <AlertCircle className="w-4 h-4 mr-1" />
              {errors.modelPairs}
            </div>
          )}

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
