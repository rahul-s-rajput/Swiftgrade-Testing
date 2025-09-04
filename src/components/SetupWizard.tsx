import { useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { CheckCircle, AlertCircle } from 'lucide-react';

interface SetupWizardProps {
  onComplete: () => void;
}

export function SetupWizard({ onComplete }: SetupWizardProps) {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState({
    api_key: '',
    supabase_url: '',
    supabase_key: '',
    storage_bucket: 'grading-images'
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      // Validate inputs
      if (!config.api_key || !config.supabase_url || !config.supabase_key) {
        setError('All fields except storage bucket are required');
        return;
      }

      // Save configuration
      await invoke('save_env_config', {
        apiKey: config.api_key,
        supabaseUrl: config.supabase_url,
        supabaseKey: config.supabase_key,
        storageBucket: config.storage_bucket || 'grading-images'
      });

      // Start backend
      const port = await invoke<number>('start_backend');
      console.log('Backend started on port:', port);

      // Update API base
      const { setApiBase } = await import('../utils/api');
      setApiBase(`http://127.0.0.1:${port}`);

      // Complete setup
      onComplete();
    } catch (e: any) {
      setError(e?.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome to Mark Grading Assistant</h1>
          <p className="text-gray-600">Let's set up your environment to get started</p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-400'
            }`}>
              {step > 1 ? <CheckCircle className="w-6 h-6" /> : '1'}
            </div>
            <span className="ml-3 font-medium text-gray-900">API Configuration</span>
          </div>
          <div className="flex-1 h-1 mx-4 bg-gray-200">
            <div className={`h-1 bg-blue-600 transition-all ${step > 1 ? 'w-full' : 'w-0'}`} />
          </div>
          <div className="flex items-center">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
              step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-400'
            }`}>
              2
            </div>
            <span className="ml-3 font-medium text-gray-900">Storage Settings</span>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        {step === 1 ? (
          <div className="space-y-6">
            <div>
              <label htmlFor="api_key" className="block text-sm font-medium text-gray-700 mb-2">
                OpenRouter API Key
              </label>
              <input
                type="password"
                id="api_key"
                value={config.api_key}
                onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="sk-or-v1-..."
              />
              <p className="mt-1 text-sm text-gray-500">
                Get your API key from <a href="https://openrouter.ai" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">openrouter.ai</a>
              </p>
            </div>

            <div>
              <label htmlFor="supabase_url" className="block text-sm font-medium text-gray-700 mb-2">
                Supabase Project URL
              </label>
              <input
                type="text"
                id="supabase_url"
                value={config.supabase_url}
                onChange={(e) => setConfig({ ...config, supabase_url: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://xxxxxxxxxxxxx.supabase.co"
              />
            </div>

            <div>
              <label htmlFor="supabase_key" className="block text-sm font-medium text-gray-700 mb-2">
                Supabase Service Role Key
              </label>
              <input
                type="password"
                id="supabase_key"
                value={config.supabase_key}
                onChange={(e) => setConfig({ ...config, supabase_key: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
              />
              <p className="mt-1 text-sm text-gray-500">
                Found in Supabase Dashboard → Settings → API → Service Role Key
              </p>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setStep(2)}
                disabled={!config.api_key || !config.supabase_url || !config.supabase_key}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next Step →
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <label htmlFor="storage_bucket" className="block text-sm font-medium text-gray-700 mb-2">
                Supabase Storage Bucket Name
              </label>
              <input
                type="text"
                id="storage_bucket"
                value={config.storage_bucket}
                onChange={(e) => setConfig({ ...config, storage_bucket: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="grading-images"
              />
              <p className="mt-1 text-sm text-gray-500">
                The bucket name for storing assessment images (default: grading-images)
              </p>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-medium text-blue-900 mb-2">Configuration Summary</h3>
              <ul className="space-y-1 text-sm text-blue-800">
                <li>• OpenRouter API configured</li>
                <li>• Supabase connection configured</li>
                <li>• Storage bucket: {config.storage_bucket || 'grading-images'}</li>
              </ul>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep(1)}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                ← Previous
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Setting up...' : 'Complete Setup'}
              </button>
            </div>
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-500 text-center">
            You can change these settings later from the Configuration menu or Settings page
          </p>
        </div>
      </div>
    </div>
  );
}