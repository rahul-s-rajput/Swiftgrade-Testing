import React, { useEffect, useState } from 'react';
import { getPromptSettings, putPromptSettings, PromptSettingsRes, getRubricPromptSettings, putRubricPromptSettings, RubricPromptSettingsRes, getTemplates, saveTemplate, deleteTemplate, Template } from '../utils/api';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { Save, RefreshCw, FolderOpen, FileEdit, AlertCircle, FileText, Settings as SettingsIcon, Plus, Trash2 } from 'lucide-react';

interface EnvConfig {
  api_key: string;
  supabase_url: string;
  supabase_key: string;
  storage_bucket: string;
}

export const Settings: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState<'prompt' | 'rubric-prompt' | 'environment'>('prompt');
  
  // Prompt settings state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [systemTemplate, setSystemTemplate] = useState('');
  const [userTemplate, setUserTemplate] = useState('');
  const [schemaTemplate, setSchemaTemplate] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [initial, setInitial] = useState<PromptSettingsRes | null>(null);
  
  // Rubric prompt settings state
  const [rubricSystemTemplate, setRubricSystemTemplate] = useState('');
  const [rubricUserTemplate, setRubricUserTemplate] = useState('');
  const [rubricSaving, setRubricSaving] = useState(false);
  const [rubricInitial, setRubricInitial] = useState<RubricPromptSettingsRes | null>(null);
  
  // Template management state
  const [rubricTemplates, setRubricTemplates] = useState<Template[]>([]);
  const [assessmentTemplates, setAssessmentTemplates] = useState<Template[]>([]);
  const [selectedRubricTemplate, setSelectedRubricTemplate] = useState<string>('');
  const [selectedAssessmentTemplate, setSelectedAssessmentTemplate] = useState<string>('');
  const [templatesLoading, setTemplatesLoading] = useState(true);
  
  // Environment settings state
  const [envConfig, setEnvConfig] = useState<EnvConfig>({
    api_key: '',
    supabase_url: '',
    supabase_key: '',
    storage_bucket: 'grading-images'
  });
  const [envSaving, setEnvSaving] = useState(false);
  const [envLoading, setEnvLoading] = useState(true);
  const [backendStatus, setBackendStatus] = useState<'running' | 'stopped' | 'restarting'>('running');

  // Check if running in Tauri
  const isTauri = () => {
    return window.__TAURI__ !== undefined;
  };

  useEffect(() => {
    loadPromptSettings();
    loadRubricPromptSettings();
    loadTemplates();
    if (isTauri()) {
      loadEnvConfig();
      
      // Listen for restart backend event
      const unlisten = listen('restart-backend', async () => {
        await restartBackend();
      });

      return () => {
        unlisten.then(fn => fn());
      };
    } else {
      setEnvLoading(false);
    }
  }, []);

  const loadPromptSettings = async () => {
    try {
      console.log('🔍 Loading prompt settings...');
      const data = await getPromptSettings();
      console.log('📦 Received settings:', data);
      
      setSystemTemplate(data.system_template || '');
      setUserTemplate(data.user_template || '');
      setSchemaTemplate(data.schema_template || '');
      setInitial(data);
      
      if (!data.system_template || !data.user_template || !data.schema_template) {
        console.warn('⚠️ Some settings are using defaults. Save custom templates to override.');
      }
    } catch (e: any) {
      console.error('❌ Failed to load settings:', e);
      setError(e?.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const loadRubricPromptSettings = async () => {
    try {
      console.log('🔍 Loading rubric prompt settings...');
      const data = await getRubricPromptSettings();
      console.log('📦 Received rubric settings:', data);
      
      setRubricSystemTemplate(data.system_template || '');
      setRubricUserTemplate(data.user_template || '');
      setRubricInitial(data);
      
      if (!data.system_template || !data.user_template) {
        console.warn('⚠️ Some rubric settings are using defaults.');
      }
    } catch (e: any) {
      console.error('❌ Failed to load rubric settings:', e);
      setError(e?.message || 'Failed to load rubric settings');
    }
  };

  const loadEnvConfig = async () => {
    try {
      setEnvLoading(true);
      const existingConfig = await invoke<EnvConfig>('get_env_config');
      setEnvConfig(existingConfig);
    } catch (error) {
      console.log('No existing environment configuration found');
      // Keep default values
    } finally {
      setEnvLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      setTemplatesLoading(true);
      const [rubricRes, assessmentRes] = await Promise.all([
        getTemplates('rubric'),
        getTemplates('assessment')
      ]);
      setRubricTemplates(rubricRes.templates);
      setAssessmentTemplates(assessmentRes.templates);
      
      // Auto-select default template and load its content
      if (rubricRes.templates.length > 0) {
        const defaultTemplate = rubricRes.templates.find(t => t.name === 'default');
        if (defaultTemplate) {
          setSelectedRubricTemplate('default');
          setRubricSystemTemplate(defaultTemplate.system_template);
          setRubricUserTemplate(defaultTemplate.user_template);
        }
      }
      
      if (assessmentRes.templates.length > 0) {
        const defaultTemplate = assessmentRes.templates.find(t => t.name === 'default');
        if (defaultTemplate) {
          setSelectedAssessmentTemplate('default');
          setSystemTemplate(defaultTemplate.system_template);
          setUserTemplate(defaultTemplate.user_template);
          setSchemaTemplate(defaultTemplate.schema_template || '');
        }
      }
    } catch (e: any) {
      console.error('Failed to load templates:', e);
    } finally {
      setTemplatesLoading(false);
    }
  };

  const handleRubricTemplateSelect = (templateName: string) => {
    setSelectedRubricTemplate(templateName);
    const template = rubricTemplates.find(t => t.name === templateName);
    if (template) {
      setRubricSystemTemplate(template.system_template);
      setRubricUserTemplate(template.user_template);
    }
  };

  const handleAssessmentTemplateSelect = (templateName: string) => {
    setSelectedAssessmentTemplate(templateName);
    const template = assessmentTemplates.find(t => t.name === templateName);
    if (template) {
      setSystemTemplate(template.system_template);
      setUserTemplate(template.user_template);
      setSchemaTemplate(template.schema_template || '');
    }
  };

  const handleSaveAsNewTemplate = async (type: 'rubric' | 'assessment') => {
    const templateName = prompt(`Enter a name for the new ${type} template:`);
    if (!templateName || !templateName.trim()) return;
    
    const cleanName = templateName.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    
    try {
      if (type === 'rubric') {
        await saveTemplate('rubric', cleanName, {
          display_name: templateName.trim(),
          system_template: rubricSystemTemplate,
          user_template: rubricUserTemplate
        });
        setSuccess(`Rubric template "${templateName}" saved successfully!`);
      } else {
        await saveTemplate('assessment', cleanName, {
          display_name: templateName.trim(),
          system_template: systemTemplate,
          user_template: userTemplate,
          schema_template: schemaTemplate
        });
        setSuccess(`Assessment template "${templateName}" saved successfully!`);
      }
      await loadTemplates(); // Reload templates
    } catch (e: any) {
      setError(`Failed to save template: ${e.message}`);
    }
  };

  const handleDeleteTemplate = async (type: 'rubric' | 'assessment', templateName: string) => {
    if (!confirm(`Are you sure you want to delete the template "${templateName}"?`)) return;
    
    try {
      await deleteTemplate(type, templateName);
      setSuccess(`Template "${templateName}" deleted successfully!`);
      await loadTemplates(); // Reload templates
      
      // Clear selection if deleted template was selected
      if (type === 'rubric' && selectedRubricTemplate === templateName) {
        setSelectedRubricTemplate('');
      } else if (type === 'assessment' && selectedAssessmentTemplate === templateName) {
        setSelectedAssessmentTemplate('');
      }
    } catch (e: any) {
      setError(`Failed to delete template: ${e.message}`);
    }
  };

  async function onSavePrompt(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!systemTemplate.trim() || !userTemplate.trim() || !schemaTemplate.trim()) {
      setError('System, User, and Schema templates are all required.');
      return;
    }
    
    console.log('💾 Saving prompt settings...');
    setSaving(true);
    try {
      // If a template is selected, save to that template
      if (selectedAssessmentTemplate) {
        await saveTemplate('assessment', selectedAssessmentTemplate, {
          display_name: assessmentTemplates.find(t => t.name === selectedAssessmentTemplate)?.display_name || selectedAssessmentTemplate,
          system_template: systemTemplate,
          user_template: userTemplate,
          schema_template: schemaTemplate
        });
        setSuccess(`Template "${selectedAssessmentTemplate}" saved successfully!`);
        await loadTemplates(); // Reload to get updated template
      } else {
        // Fallback: save to original settings (shouldn't happen with auto-select)
        const res = await putPromptSettings({ 
          system_template: systemTemplate, 
          user_template: userTemplate,
          schema_template: schemaTemplate
        });
        console.log('✅ Settings saved successfully:', res);
        setInitial(res);
        setSuccess('Prompt settings saved successfully!');
      }
    } catch (e: any) {
      console.error('❌ Failed to save settings:', e);
      setError(e?.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

  async function onSaveRubricPrompt(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!rubricSystemTemplate.trim() || !rubricUserTemplate.trim()) {
      setError('System and User templates are both required for rubric prompts.');
      return;
    }
    
    console.log('💾 Saving rubric prompt settings...');
    setRubricSaving(true);
    try {
      // If a template is selected, save to that template
      if (selectedRubricTemplate) {
        await saveTemplate('rubric', selectedRubricTemplate, {
          display_name: rubricTemplates.find(t => t.name === selectedRubricTemplate)?.display_name || selectedRubricTemplate,
          system_template: rubricSystemTemplate,
          user_template: rubricUserTemplate
        });
        setSuccess(`Template "${selectedRubricTemplate}" saved successfully!`);
        await loadTemplates(); // Reload to get updated template
      } else {
        // Fallback: save to original settings (shouldn't happen with auto-select)
        const res = await putRubricPromptSettings({ 
          system_template: rubricSystemTemplate, 
          user_template: rubricUserTemplate
        });
        console.log('✅ Rubric settings saved successfully:', res);
        setRubricInitial(res);
        setSuccess('Rubric prompt settings saved successfully. New grading sessions will use these templates.');
      }
    } catch (e: any) {
      console.error('❌ Failed to save rubric settings:', e);
      setError(e?.message || 'Failed to save rubric settings');
    } finally {
      setRubricSaving(false);
    }
  }

  function onResetRubric() {
    if (rubricInitial) {
      setRubricSystemTemplate(rubricInitial.system_template);
      setRubricUserTemplate(rubricInitial.user_template);
      setSuccess(null);
      setError(null);
    }
  }

  const saveEnvConfig = async () => {
    try {
      setEnvSaving(true);
      setError(null);
      setSuccess(null);
      
      await invoke('save_env_config', {
        apiKey: envConfig.api_key,
        supabaseUrl: envConfig.supabase_url,
        supabaseKey: envConfig.supabase_key,
        storageBucket: envConfig.storage_bucket
      });
      
      setSuccess('Environment configuration saved successfully! Restart the backend to apply changes.');
    } catch (error) {
      setError(`Failed to save configuration: ${error}`);
    } finally {
      setEnvSaving(false);
    }
  };

  const restartBackend = async () => {
    try {
      setBackendStatus('restarting');
      setSuccess('Restarting backend...');
      
      await invoke('stop_backend');
      await new Promise(resolve => setTimeout(resolve, 1000));
      const port = await invoke<number>('start_backend');
      
      setBackendStatus('running');
      setSuccess(`Backend restarted successfully on port ${port}`);
    } catch (error) {
      setBackendStatus('stopped');
      setError(`Failed to restart backend: ${error}`);
    }
  };

  const openConfigFolder = async () => {
    try {
      const appDataDir = await invoke<string>('get_app_data_dir');
      if (window.__TAURI__) {
        const { open } = await import('@tauri-apps/plugin-shell');
        await open(appDataDir);
      }
    } catch (error) {
      setError(`Failed to open config folder: ${error}`);
    }
  };

  const openEnvFile = async () => {
    try {
      await invoke('open_env_file');
      setSuccess('Opening environment file in system editor...');
    } catch (error) {
      setError(`Failed to open env file: ${error}`);
    }
  };

  function onReset() {
    if (initial) {
      setSystemTemplate(initial.system_template);
      setUserTemplate(initial.user_template);
      setSchemaTemplate(initial.schema_template || '');
      setSuccess(null);
      setError(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Settings</h2>
        <p className="text-slate-600 mt-1">Configure prompts and environment settings.</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('prompt')}
            className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
              activeTab === 'prompt'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <FileText className="w-4 h-4" />
            LLM Prompt Settings
            </button>
            <button
          onClick={() => setActiveTab('rubric-prompt')}
          className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
            activeTab === 'rubric-prompt'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          <FileText className="w-4 h-4" />
          Rubric Prompt Settings
        </button>
        {isTauri() && (
            <button
              onClick={() => setActiveTab('environment')}
              className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                activeTab === 'environment'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <SettingsIcon className="w-4 h-4" />
              Environment Configuration
            </button>
          )}
        </nav>
      </div>

      {/* Tab Content */}
      {error && <div className="rounded-md bg-red-50 border border-red-200 text-red-700 px-4 py-3 flex items-start gap-2">
        <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
        <span>{error}</span>
      </div>}
      {success && <div className="rounded-md bg-green-50 border border-green-200 text-green-700 px-4 py-3 flex items-start gap-2">
        <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
        <span>{success}</span>
      </div>}

      {activeTab === 'prompt' ? (
        loading ? (
          <div className="text-slate-600">Loading prompt settings…</div>
        ) : (
          <form onSubmit={onSavePrompt} className="space-y-6">
            {/* Template Management */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
              <label className="block text-sm font-medium text-slate-700">Template</label>
              <div className="flex gap-2">
                <select
                  value={selectedAssessmentTemplate}
                  onChange={(e) => handleAssessmentTemplateSelect(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 px-3 py-2 text-sm"
                >
                  {assessmentTemplates.map(template => (
                    <option key={template.name} value={template.name}>
                      {template.display_name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => handleSaveAsNewTemplate('assessment')}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 text-sm"
                  title="Save current settings as a new template"
                >
                  <Plus className="w-4 h-4" />
                  Save as New
                </button>
                {selectedAssessmentTemplate && selectedAssessmentTemplate !== 'default' && (
                  <button
                    type="button"
                    onClick={() => handleDeleteTemplate('assessment', selectedAssessmentTemplate)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 text-sm"
                    title="Delete selected template"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Select a template to load, or save your current settings as a new template.
              </p>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">System Template</label>
              <textarea
                value={systemTemplate}
                onChange={(e) => setSystemTemplate(e.target.value)}
                className="w-full min-h-[200px] rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 p-3 font-mono text-sm bg-white"
                placeholder="Enter the system template..."
              />
              <p className="text-xs text-slate-500">Supported placeholders: [Answer key], [Question list], [Response schema]</p>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">User Template</label>
              <textarea
                value={userTemplate}
                onChange={(e) => setUserTemplate(e.target.value)}
                className="w-full min-h-[150px] rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 p-3 font-mono text-sm bg-white"
                placeholder="Enter the user template..."
              />
              <p className="text-xs text-slate-500">Supported placeholders: [Student assessment]</p>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">
                Response Schema Template
                <span className="ml-2 text-xs font-normal text-slate-500">(JSON format the AI should return)</span>
              </label>
              <textarea
                value={schemaTemplate}
                onChange={(e) => setSchemaTemplate(e.target.value)}
                className="w-full min-h-[150px] rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 p-3 font-mono text-sm bg-white"
                placeholder='Return ONLY JSON with this exact schema...'
              />
              <p className="text-xs text-slate-500">
                Define the exact JSON structure the AI should return. This controls the response format.
              </p>
              <details className="text-xs text-slate-600 mt-2">
                <summary className="cursor-pointer hover:text-slate-800">Example schemas (click to expand)</summary>
                <div className="mt-2 space-y-2 pl-4">
                  <div>
                    <strong>Default (detailed):</strong>
                    <pre className="bg-slate-100 p-2 rounded mt-1 overflow-x-auto">
{`{"result":[{"first_name":string,"last_name":string,
"answers":[{"question_id":string,"marks_awarded":number,
"rubric_notes":string}]}]}`}
                    </pre>
                  </div>
                  <div>
                    <strong>Simple format:</strong>
                    <pre className="bg-slate-100 p-2 rounded mt-1 overflow-x-auto">
{`{"grades": {"Q1": 10, "Q2": 15, "Q3": 12}}`}
                    </pre>
                  </div>
                </div>
              </details>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
              >
                {saving ? 'Saving…' : 'Save Prompt Settings'}
              </button>
              <button
                type="button"
                onClick={onReset}
                className="inline-flex items-center px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                Revert Changes
              </button>
            </div>
          </form>
        )
      ) : activeTab === 'rubric-prompt' ? (
        loading ? (
          <div className="text-slate-600">Loading rubric prompt settings…</div>
        ) : (
          <form onSubmit={onSaveRubricPrompt} className="space-y-6">

            {/* Template Management */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-3">
              <label className="block text-sm font-medium text-slate-700">Template</label>
              <div className="flex gap-2">
                <select
                  value={selectedRubricTemplate}
                  onChange={(e) => handleRubricTemplateSelect(e.target.value)}
                  className="flex-1 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 px-3 py-2 text-sm"
                >
                  {rubricTemplates.map(template => (
                    <option key={template.name} value={template.name}>
                      {template.display_name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => handleSaveAsNewTemplate('rubric')}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 text-sm"
                  title="Save current settings as a new template"
                >
                  <Plus className="w-4 h-4" />
                  Save as New
                </button>
                {selectedRubricTemplate && selectedRubricTemplate !== 'default' && (
                  <button
                    type="button"
                    onClick={() => handleDeleteTemplate('rubric', selectedRubricTemplate)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 text-sm"
                    title="Delete selected template"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Select a template to load, or save your current settings as a new template.
              </p>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">Rubric System Template</label>
              <textarea
                value={rubricSystemTemplate}
                onChange={(e) => setRubricSystemTemplate(e.target.value)}
                className="w-full min-h-[200px] rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 p-3 font-mono text-sm bg-white"
                placeholder="Enter the system template for rubric analysis..."
              />
              <p className="text-xs text-slate-500">Supported placeholders: [Grading rubric images], [Question list]</p>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-700">Rubric User Template</label>
              <textarea
                value={rubricUserTemplate}
                onChange={(e) => setRubricUserTemplate(e.target.value)}
                className="w-full min-h-[150px] rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 p-3 font-mono text-sm bg-white"
                placeholder="Enter the user template for rubric analysis..."
              />
              <p className="text-xs text-slate-500">The instructions for analyzing the rubric images</p>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={rubricSaving}
                className="inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
              >
                {rubricSaving ? 'Saving…' : 'Save Rubric Settings'}
              </button>
              <button
                type="button"
                onClick={onResetRubric}
                className="inline-flex items-center px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                Revert Changes
              </button>
            </div>
          </form>
        )
      ) : (
        envLoading ? (
          <div className="text-slate-600">Loading environment configuration…</div>
        ) : (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <h3 className="text-lg font-semibold mb-4">API Configuration</h3>
              
              <div className="space-y-4">
                <div>
                  <label htmlFor="api_key" className="block text-sm font-medium text-gray-700 mb-1">
                    OpenRouter API Key
                  </label>
                  <input
                    type="password"
                    id="api_key"
                    value={envConfig.api_key}
                    onChange={(e) => setEnvConfig({ ...envConfig, api_key: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="sk-or-v1-..."
                  />
                </div>

                <div>
                  <label htmlFor="supabase_url" className="block text-sm font-medium text-gray-700 mb-1">
                    Supabase URL
                  </label>
                  <input
                    type="text"
                    id="supabase_url"
                    value={envConfig.supabase_url}
                    onChange={(e) => setEnvConfig({ ...envConfig, supabase_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="https://xxxxxxxxxxxxx.supabase.co"
                  />
                </div>

                <div>
                  <label htmlFor="supabase_key" className="block text-sm font-medium text-gray-700 mb-1">
                    Supabase Service Role Key
                  </label>
                  <input
                    type="password"
                    id="supabase_key"
                    value={envConfig.supabase_key}
                    onChange={(e) => setEnvConfig({ ...envConfig, supabase_key: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                  />
                </div>

                <div>
                  <label htmlFor="storage_bucket" className="block text-sm font-medium text-gray-700 mb-1">
                    Supabase Storage Bucket
                  </label>
                  <input
                    type="text"
                    id="storage_bucket"
                    value={envConfig.storage_bucket}
                    onChange={(e) => setEnvConfig({ ...envConfig, storage_bucket: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="grading-images"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    The Supabase storage bucket for storing grading images
                  </p>
                </div>
              </div>

              <div className="mt-6 flex gap-3">
                <button
                  onClick={saveEnvConfig}
                  disabled={envSaving}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {envSaving ? 'Saving...' : 'Save Configuration'}
                </button>

                <button
                  onClick={restartBackend}
                  disabled={backendStatus === 'restarting'}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${backendStatus === 'restarting' ? 'animate-spin' : ''}`} />
                  {backendStatus === 'restarting' ? 'Restarting...' : 'Restart Backend'}
                </button>
              </div>
            </div>

            <div className="bg-white rounded-lg border border-slate-200 p-6">
              <h3 className="text-lg font-semibold mb-4">Advanced Options</h3>
              
              <div className="space-y-3">
                <button
                  onClick={openEnvFile}
                  className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md flex items-center gap-2 text-left"
                >
                  <FileEdit className="w-4 h-4" />
                  <div>
                    <div className="font-medium">Edit Environment File</div>
                    <div className="text-sm text-gray-500">Open the .env file in your system text editor</div>
                  </div>
                </button>

                <button
                  onClick={openConfigFolder}
                  className="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md flex items-center gap-2 text-left"
                >
                  <FolderOpen className="w-4 h-4" />
                  <div>
                    <div className="font-medium">Open Configuration Folder</div>
                    <div className="text-sm text-gray-500">Browse the application data directory</div>
                  </div>
                </button>
              </div>

              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <p className="text-sm text-yellow-800">
                  <strong>Note:</strong> After editing the environment file manually, restart the backend to apply changes.
                  You can also access these options from the Configuration menu in the menu bar.
                </p>
              </div>
            </div>

            <div className="text-sm text-gray-500">
              <p>Backend Status: <span className={`font-medium ${
                backendStatus === 'running' ? 'text-green-600' :
                backendStatus === 'restarting' ? 'text-yellow-600' :
                'text-red-600'
              }`}>{backendStatus}</span></p>
            </div>
          </div>
        )
      )}
    </div>
  );
}