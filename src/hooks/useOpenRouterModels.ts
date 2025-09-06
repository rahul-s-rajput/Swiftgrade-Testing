import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AIModel } from '../types';
import { API_BASE } from '../utils/api';

// Minimal OpenRouter model shape (only fields we may use)
interface OpenRouterModel {
  id: string;
  name?: string;
  context_length?: number;
  pricing?: {
    prompt?: number | string;
    completion?: number | string;
    request?: number | string;
    image?: number | string;
    internal_reasoning?: number | string;
  };
  architecture?: {
    modality?: string;
    input_modalities?: string[];
    output_modalities?: string[];
  };
  supported_parameters?: string[];
  // Provider is derivable from id (prefix before "/") but may exist
  // in some responses as meta; we keep it minimal and optional here.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
}

function detectImageCapability(model: OpenRouterModel): boolean {
  const arch = model.architecture;
  const inputs: string[] = Array.isArray(arch?.input_modalities) ? arch!.input_modalities! : [];
  const viaArray = inputs.map(s => String(s).toLowerCase()).includes('image');
  const viaModality = typeof arch?.modality === 'string' && arch!.modality!.toLowerCase().includes('image');
  return viaArray || viaModality;
}

type ReasoningType = 'effort' | 'max_tokens' | 'both' | 'none';

interface ModelInfo {
  supportsReasoning: boolean;
  reasoningType: ReasoningType;
  hasIncludeReasoning: boolean;
  hasInternalReasoningPricing: boolean;
  supportsImage: boolean;
  variants: string[];
  contextDisplay: string;
  priceDisplay: string;
  raw?: OpenRouterModel;
}

const CACHE_KEY = 'openrouter_models_cache_v1';
const ONE_HOUR = 60 * 60 * 1000;

function titleCase(input: string): string {
  return input
    .split(/[-_\s]+/)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function idToProvider(id: string): string {
  const provider = id.split('/')[0] || id;
  return titleCase(provider.replace(/[^a-z0-9]+/gi, ' '));
}

function idToName(id: string, fallbackName?: string): string {
  if (fallbackName) return fallbackName;
  const afterSlash = id.includes('/') ? id.split('/')[1] : id;
  const base = afterSlash.split(':')[0];
  return titleCase(base.replace(/[^a-z0-9]+/gi, ' '));
}

function parseVariants(id: string): string[] {
  const parts = id.split(':');
  // first part is the base id (may contain "/")
  return parts.length > 1 ? parts.slice(1) : [];
}

function detectReasoningCapabilities(model: OpenRouterModel) {
  const params: string[] = Array.isArray(model.supported_parameters) ? model.supported_parameters : [];
  const hasReasoningParam = params.includes('reasoning');
  const hasIncludeReasoning = params.includes('include_reasoning');
  const hasInternalReasoningPricing = !!model.pricing?.internal_reasoning;

  let reasoningType: ReasoningType = 'none';
  if (hasReasoningParam || hasIncludeReasoning) {
    // All reasoning models now use effort-based reasoning (low/medium/high)
    // OpenRouter handles the conversion internally for different model types
    reasoningType = 'effort';
  }

  return {
    supportsReasoning: hasReasoningParam || hasIncludeReasoning,
    reasoningType,
    hasIncludeReasoning,
    hasInternalReasoningPricing,
  } as const;
}

function safeContextDisplay(model?: OpenRouterModel): string {
  const len = model?.context_length;
  if (typeof len === 'number') return `${len.toLocaleString()} tokens`;
  return 'Context: —';
}

function safePriceDisplay(model?: OpenRouterModel): string {
  const p = model?.pricing;
  if (!p) return 'Price: —';
  const prompt = p.prompt ?? p.request;
  const completion = p.completion;
  const str = [
    prompt !== undefined ? `P: ${String(prompt)}` : undefined,
    completion !== undefined ? `C: ${String(completion)}` : undefined,
  ].filter(Boolean).join(' · ');
  return str || 'Price: —';
}

export function useOpenRouterModels() {
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const modelInfoRef = useRef<Record<string, ModelInfo>>({});
  const [infoTick, setInfoTick] = useState(0);

  const buildInfoFromRaw = useCallback((raw: OpenRouterModel[]) => {
    const info: Record<string, ModelInfo> = {};
    raw.forEach(m => {
      const id = m.id;
      const caps = detectReasoningCapabilities(m);
      info[id] = {
        supportsReasoning: caps.supportsReasoning,
        reasoningType: caps.reasoningType,
        hasIncludeReasoning: caps.hasIncludeReasoning,
        hasInternalReasoningPricing: caps.hasInternalReasoningPricing,
        supportsImage: detectImageCapability(m),
        variants: parseVariants(id),
        contextDisplay: safeContextDisplay(m),
        priceDisplay: safePriceDisplay(m),
        raw: m,
      };
    });
    modelInfoRef.current = info;
    setInfoTick(t => t + 1);
  }, []);

  const buildInfoFromAIModels = useCallback((items: AIModel[]) => {
    const info: Record<string, ModelInfo> = {};
    items.forEach(m => {
      info[m.id] = {
        supportsReasoning: false,
        reasoningType: 'none',
        hasIncludeReasoning: false,
        hasInternalReasoningPricing: false,
        supportsImage: false,
        variants: parseVariants(m.id),
        contextDisplay: 'Context: —',
        priceDisplay: 'Price: —',
      };
    });
    modelInfoRef.current = info;
    setInfoTick(t => t + 1);
  }, []);

  const loadFromCache = useCallback(() => {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return false;
      const parsed = JSON.parse(raw) as { timestamp: number; items: AIModel[] };
      if (!parsed?.timestamp || !Array.isArray(parsed.items)) return false;
      const fresh = Date.now() - parsed.timestamp < ONE_HOUR;
      if (!fresh) return false;
      setModels(parsed.items);
      buildInfoFromAIModels(parsed.items);
      return true;
    } catch {
      return false;
    }
  }, [buildInfoFromAIModels]);

  const persistCache = useCallback((items: AIModel[]) => {
    try {
      const payload = JSON.stringify({ timestamp: Date.now(), items });
      localStorage.setItem(CACHE_KEY, payload);
    } catch {
      // ignore storage errors
    }
  }, []);

  const fetchModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Use backend proxy endpoint instead of direct OpenRouter API
      const res = await fetch(`${API_BASE}/models`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const items: OpenRouterModel[] = Array.isArray(data?.data) ? data.data : (Array.isArray(data) ? data : []);

      const transformed: AIModel[] = items.map((m: OpenRouterModel) => {
        const provider = idToProvider(m.id);
        const name = idToName(m.id, m.name);
        return { id: m.id, name, provider };
      });

      setModels(transformed);
      buildInfoFromRaw(items);
      persistCache(transformed);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setError(`Failed to fetch models: ${msg}`);
    } finally {
      setLoading(false);
    }
  }, [buildInfoFromRaw, persistCache]);

  // Silent info-only refresh to populate capabilities when loading from cache
  const fetchModelInfoOnly = useCallback(async () => {
    try {
      // Use backend proxy endpoint instead of direct OpenRouter API
      const res = await fetch(`${API_BASE}/models`);
      if (!res.ok) return;
      const data = await res.json();
      const items: OpenRouterModel[] = Array.isArray(data?.data) ? data.data : (Array.isArray(data) ? data : []);
      buildInfoFromRaw(items);
    } catch {
      // ignore
    }
  }, [buildInfoFromRaw]);

  useEffect(() => {
    // Try cache first; if not fresh, fetch from network
    const usedCache = loadFromCache();
    if (usedCache) {
      // Populate real capabilities in background
      void fetchModelInfoOnly();
    } else {
      void fetchModels();
    }
  }, [fetchModels, loadFromCache, fetchModelInfoOnly]);

  const refetch = useCallback(() => {
    void fetchModels();
  }, [fetchModels]);

  const modelInfoById = useMemo(() => modelInfoRef.current, [infoTick]);

  return { models, loading, error, refetch, modelInfoById } as const;
}
