import React, { useEffect, useState } from 'react';
import { getPromptSettings, putPromptSettings, PromptSettingsRes } from '../utils/api';

export const Settings: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [systemTemplate, setSystemTemplate] = useState('');
  const [userTemplate, setUserTemplate] = useState('');
  const [schemaTemplate, setSchemaTemplate] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [initial, setInitial] = useState<PromptSettingsRes | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        console.log('🔍 Loading prompt settings...');
        const data = await getPromptSettings();
        console.log('📦 Received settings:', data);
        console.log('  System template length:', data.system_template?.length || 0);
        console.log('  User template length:', data.user_template?.length || 0);
        console.log('  Schema template length:', data.schema_template?.length || 0);
        
        if (!mounted) return;
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
    })();
    return () => { mounted = false; };
  }, []);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!systemTemplate.trim() || !userTemplate.trim() || !schemaTemplate.trim()) {
      setError('System, User, and Schema templates are all required.');
      return;
    }
    
    // Debug logging
    console.log('💾 Saving prompt settings...');
    console.log('  System template length:', systemTemplate.length);
    console.log('  User template length:', userTemplate.length);
    console.log('  Schema template length:', schemaTemplate.length);
    console.log('  System preview:', systemTemplate.substring(0, 100));
    console.log('  User preview:', userTemplate.substring(0, 100));
    console.log('  Schema preview:', schemaTemplate.substring(0, 100));
    
    setSaving(true);
    try {
      const res = await putPromptSettings({ 
        system_template: systemTemplate, 
        user_template: userTemplate,
        schema_template: schemaTemplate
      });
      console.log('✅ Settings saved successfully:', res);
      setInitial(res);
      setSuccess('Settings saved successfully. New grading sessions will use these templates.');
    } catch (e: any) {
      console.error('❌ Failed to save settings:', e);
      setError(e?.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  }

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
        <h2 className="text-2xl font-bold text-slate-800">LLM Prompt Settings</h2>
        <p className="text-slate-600 mt-1">Customize the System, User, and Schema templates used for grading.</p>
      </div>

      {loading ? (
        <div className="text-slate-600">Loading…</div>
      ) : (
        <form onSubmit={onSave} className="space-y-6">
          {error && <div className="rounded-md bg-red-50 border border-red-200 text-red-700 px-4 py-3">{error}</div>}
          {success && <div className="rounded-md bg-green-50 border border-green-200 text-green-700 px-4 py-3">{success}</div>}

          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-700">System Template</label>
            <textarea
              value={systemTemplate}
              onChange={(e) => setSystemTemplate(e.target.value)}
              className="w-full min-h-[200px] rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 p-3 font-mono text-sm bg-white"
              placeholder="Enter the system template..."
            />
            <p className="text-xs text-slate-500">Supported placeholders: [Answer key], [Question list]</p>
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
                <div>
                  <strong>With confidence scores:</strong>
                  <pre className="bg-slate-100 p-2 rounded mt-1 overflow-x-auto">
{`{"result": [{"question_id": "Q1", "score": 10, 
"confidence": 0.95, "explanation": "..."}]}`}
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
              {saving ? 'Saving…' : 'Save Settings'}
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
      )}
    </div>
  );
}
