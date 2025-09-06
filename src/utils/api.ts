/* Frontend API client for backend integration (Story 26) */

// Dynamic API base that can be overridden by Tauri
export let API_BASE: string = (window as any).API_BASE || (import.meta as any).env?.VITE_API_BASE || 'http://127.0.0.1:8000';

// Function to update API_BASE (for Tauri)
export const setApiBase = (url: string) => {
  console.log('[API] Setting API_BASE from', API_BASE, 'to', url);
  API_BASE = url;
  (window as any).API_BASE = url;
  console.log('[API] API_BASE is now:', API_BASE);
};

export type ErrorEnvelope = { error?: { code?: string; message?: string; details?: any } } | undefined;

async function parseJsonSafe<T>(resp: Response): Promise<T | undefined> {
  try {
    return await resp.json();
  } catch {
    return undefined;
  }
}

// Helper to log API calls in development
function logApiCall(method: string, path: string, fullUrl: string) {
  console.log(`[API] ${method} ${path}`);
  console.log(`[API] Full URL: ${fullUrl}`);
}

export async function postJSON<T>(path: string, body: any, init?: RequestInit): Promise<T> {
  const fullUrl = `${API_BASE}${path}`;
  logApiCall('POST', path, fullUrl);
  
  const resp = await fetch(fullUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    body: JSON.stringify(body),
    ...init,
  });
  
  console.log(`[API] Response status: ${resp.status}`);
  
  if (!resp.ok) {
    const data = await parseJsonSafe<ErrorEnvelope>(resp);
    const msg = data?.error?.message || `${resp.status} ${resp.statusText}`;
    console.error(`[API] Error: ${msg}`);
    const err: any = new Error(msg);
    err.status = resp.status;
    err.retryAfter = resp.headers.get('Retry-After');
    throw err;
  }
  
  const result = (await resp.json()) as T;
  console.log('[API] Success');
  return result;
}

export async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const fullUrl = `${API_BASE}${path}`;
  logApiCall('GET', path, fullUrl);
  
  const resp = await fetch(fullUrl, { method: 'GET', ...(init || {}) });
  
  console.log(`[API] Response status: ${resp.status}`);
  
  if (!resp.ok) {
    const data = await parseJsonSafe<ErrorEnvelope>(resp);
    const msg = data?.error?.message || `${resp.status} ${resp.statusText}`;
    console.error(`[API] Error: ${msg}`);
    const err: any = new Error(msg);
    err.status = resp.status;
    err.retryAfter = resp.headers.get('Retry-After');
    throw err;
  }
  
  const result = (await resp.json()) as T;
  console.log('[API] Success');
  return result;
}

export async function del(path: string, init?: RequestInit): Promise<void> {
  const fullUrl = `${API_BASE}${path}`;
  logApiCall('DELETE', path, fullUrl);
  
  const resp = await fetch(fullUrl, { method: 'DELETE', ...(init || {}) });
  
  console.log(`[API] Response status: ${resp.status}`);
  
  if (!resp.ok) {
    const data = await parseJsonSafe<ErrorEnvelope>(resp);
    const msg = data?.error?.message || `${resp.status} ${resp.statusText}`;
    console.error(`[API] Error: ${msg}`);
    const err: any = new Error(msg);
    err.status = resp.status;
    throw err;
  }
  
  console.log('[API] Success');
}

export async function sleep(ms: number) { return new Promise(res => setTimeout(res, ms)); }

// --- Endpoint wrappers ---

export interface SessionCreateRes { session_id: string; status: string }
export const createSession = (name?: string) => postJSON<SessionCreateRes>('/sessions', name ? { name } : {});

export interface SignedUrlRes {
  uploadUrl: string;
  token?: string | null;
  path: string;
  headers: Record<string, string>;
  publicUrl?: string | null;
}
export const getSignedUrl = (filename: string, contentType: string) =>
  postJSON<SignedUrlRes>('/images/signed-url', { filename, content_type: contentType });

export async function uploadToSignedUrl(uploadUrl: string, headers: Record<string, string>, file: File, contentType: string) {
  const finalHeaders = new Headers();
  for (const [k, v] of Object.entries(headers || {})) finalHeaders.set(k, v);
  if (!finalHeaders.has('content-type')) finalHeaders.set('content-type', contentType);
  const resp = await fetch(uploadUrl, { method: 'PUT', headers: finalHeaders, body: file });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`Upload failed: ${resp.status} ${resp.statusText} ${text}`);
  }
}

export interface OkRes { ok: boolean }
export const registerImage = (session_id: string, role: 'student' | 'answer_key', url: string, order_index: number) =>
  postJSON<OkRes>('/images/register', { session_id, role, url, order_index });

export interface QuestionConfigQuestion { 
  question_number: string;  // Input field (what user provides)
  max_mark: number;         // Input field (what user provides)
  // Backend may also return these alternative field names:
  question_id?: string;     // Backend storage field
  max_marks?: number;       // Backend storage field
}
export const postQuestionsConfig = (
  session_id: string,
  questions: QuestionConfigQuestion[],
  human_marks_by_qid: Record<string, number>
) => postJSON<OkRes>('/questions/config', { session_id, questions, human_marks_by_qid });

export interface GradeSingleRes { ok: boolean; session_id: string }
export async function gradeSingleWithRetry(
  session_id: string, 
  models: string[], 
  default_tries: number, 
  reasoning?: any,
  reasoningBySelection?: any[],
  maxAttempts = 5
): Promise<GradeSingleRes> {
  // Create model specs with per-model reasoning
  const modelSpecs = models.map((name, index) => {
    const spec: any = { name };
    
    // Add instance ID to differentiate same model with different reasoning
    if (reasoningBySelection && reasoningBySelection[index]) {
      const reasoningConfig = reasoningBySelection[index];
      if (reasoningConfig) {
        // Create unique instance ID based on model and reasoning
        spec.instance_id = `${name}_${index}_${reasoningConfig.level}`;
        
        // Add reasoning config to this specific model
        if (reasoningConfig.level === 'none') {
          spec.reasoning = { exclude: true };
        } else if (reasoningConfig.level === 'custom' && reasoningConfig.tokens) {
          spec.reasoning = { max_tokens: reasoningConfig.tokens };
        } else if (reasoningConfig.level !== 'custom') {
          spec.reasoning = { effort: reasoningConfig.level };
        }
      }
    }
    
    return spec;
  });
  
  // Log reasoning configuration if present
  if (modelSpecs.some(m => m.reasoning)) {
    console.log('%c🧠 Sending model-specific reasoning configurations:', 'color: #4CAF50; font-weight: bold');
    modelSpecs.forEach((spec, i) => {
      console.log(`  Model ${i + 1}: ${spec.name}`);
      if (spec.reasoning) {
        console.log(`    Reasoning: ${JSON.stringify(spec.reasoning)}`);
        console.log(`    Instance ID: ${spec.instance_id}`);
      } else {
        console.log(`    No reasoning`);
      }
    });
  }
  
  let attempt = 0;
  while (true) {
    try {
      return await postJSON<GradeSingleRes>('/grade/single', {
        session_id,
        models: modelSpecs,
        default_tries,
        reasoning,  // Keep global reasoning for backward compatibility
      });
    } catch (e: any) {
      attempt++;
      if (e?.status === 429 && attempt < maxAttempts) {
        const ra = Number(e.retryAfter || 2);
        const backoff = (isFinite(ra) && ra > 0 ? ra : 2) * Math.pow(2, attempt - 1) * 1000;
        await sleep(backoff);
        continue;
      }
      throw e;
    }
  }
}

export interface ResultItem { 
  try_index: number; 
  marks_awarded: number | null; 
  rubric_notes: string | null;
  token_usage?: {
    input_tokens?: number;
    output_tokens?: number;
    reasoning_tokens?: number;
    total_tokens?: number;
  };
}
export interface ResultsRes { session_id: string; results_by_question: Record<string, Record<string, ResultItem[]>> }
export const getResults = (session_id: string) => getJSON<ResultsRes>(`/results/${session_id}`);

// Per-model/try validation errors captured during parsing
export interface ResultsErrorsRes {
  session_id: string;
  errors_by_model_try: Record<string, Record<string, Array<Record<string, any>>>>;
}
export const getResultErrors = (session_id: string) => getJSON<ResultsErrorsRes>(`/results/errors/${session_id}`);

export interface StatsRes {
  session_id: string;
  human_marks_by_qid: Record<string, number>;
  totals: { total_max_marks: number; total_marks_awarded_by_model_try: Record<string, Record<string, number>> };
  discrepancies_by_model_try: Record<string, Record<string, any>>;
}
export const getStats = (session_id: string) => getJSON<StatsRes>(`/stats/${session_id}`);

// --- Questions GET ---
export interface QuestionsRes {
  session_id: string;
  questions: QuestionConfigQuestion[];
}
export const getQuestions = (session_id: string) => getJSON<QuestionsRes>(`/questions/${session_id}`);

// --- Sessions listing ---
export interface SessionListItem {
  id: string;
  status: string;
  created_at: string;
  name?: string;
  selected_models?: string[];
  default_tries?: number;
}
export const getSessions = () => {
  console.log('[API] getSessions called');
  console.log('[API] Current API_BASE:', API_BASE);
  console.log('[API] window.API_BASE:', (window as any).API_BASE);
  return getJSON<SessionListItem[]>(`/sessions`);
};

export const deleteSession = (session_id: string) => del(`/sessions/${session_id}`);

// Debug function to test current API base
export const debugApiBase = () => {
  const info = {
    API_BASE,
    windowApiBase: (window as any).API_BASE,
    metaEnv: (import.meta as any).env?.VITE_API_BASE
  };
  console.log('[API Debug]', info);
  return info;
};

// Test connection to backend
export const testBackendConnection = async () => {
  console.log('[API] Testing backend connection...');
  console.log('[API] API_BASE:', API_BASE);
  
  try {
    const response = await fetch(`${API_BASE}/health`);
    const data = await response.json();
    console.log('[API] Health check response:', data);
    return { success: true, data };
  } catch (error) {
    console.error('[API] Health check failed:', error);
    return { success: false, error };
  }
};

// --- Prompt Settings ---
export interface PromptSettingsRes { 
  system_template: string; 
  user_template: string;
  schema_template: string;
}
export type PromptSettingsReq = PromptSettingsRes;
export const getPromptSettings = () => getJSON<PromptSettingsRes>(`/settings/prompt`);
export const putPromptSettings = (body: PromptSettingsReq) => fetch(`${API_BASE}/settings/prompt`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
}).then(async (r) => {
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`${r.status} ${r.statusText} ${text}`);
  }
  return r.json() as Promise<PromptSettingsRes>;
});
