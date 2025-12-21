import {
  AnalyzePayload,
  AnalyzeResponse,
  AgentSummary,
  AgentStep,
  AgentStepStatus,
  FusionSource,
  analyzeMockRequest
} from '@utils/mockApi';

type UrlModelResponse = {
  confidence?: number;
  score?: number;
  verdict?: boolean | string;
  final_verdict?: boolean;
  is_phishing?: boolean;
  label?: string;
  reasons?: string[] | string;
  reason?: string;
  detected_brands?: string[];
  extracted_urls?: string[];
  elapsed_ms?: number;
};

type UrlAnalysisResponse = {
  url: string;
  final_verdict: boolean;
  confidence: number;
  models?: Record<string, UrlModelResponse>;
  detected_brands?: string[];
  visual_reasons?: string[];
  extracted_urls?: string[];
  model_version?: string;
  request_id?: string;
  timestamp?: string;
  agent?: AgentSummary;
};

type TextAnalysisResponse = {
  is_phishing: boolean;
  confidence: number;
  reasons?: string[];
  extracted_urls?: string[];
  model_version?: string;
  request_id?: string;
  timestamp?: string;
};

const prodFallback = '/api/proxy';
const rawEnvBase = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? prodFallback : '');
const RAW_API_BASE_URL = rawEnvBase.replace(/\/$/, '');
const DEV_PROXY_PATH = import.meta.env.VITE_DEV_PROXY_PATH?.replace(/\/$/, '') ?? '';

const API_BASE_URL = import.meta.env.DEV && DEV_PROXY_PATH ? DEV_PROXY_PATH : RAW_API_BASE_URL;

const ROUTES: Record<Exclude<AnalyzePayload['mode'], 'image'>, string> = {
  url: '/analyze_url_v2',
  text: '/analyze_text'
};

const safeRequestId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `req_${Math.random().toString(36).slice(2, 10)}`;
};

const normalizeScore = (value: unknown): number => {
  if (typeof value === 'number') {
    // Backend sometimes returns 0..100; normalize to 0..1
    if (value > 1) {
      return Math.min(value / 100, 1);
    }
    return Math.min(Math.max(value, 0), 1);
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      if (parsed > 1) {
        return Math.min(parsed / 100, 1);
      }
      return Math.min(Math.max(parsed, 0), 1);
    }
  }
  return 0;
};

const booleanFromModel = (model: UrlModelResponse): boolean => {
  if (typeof model.verdict === 'string') {
    const verdict = model.verdict.toLowerCase();
    if (verdict.includes('phish') || verdict.includes('malicious') || verdict.includes('block')) {
      return true;
    }
    if (verdict.includes('safe') || verdict.includes('benign') || verdict.includes('allow')) {
      return false;
    }
    if (verdict.includes('suspicious') || verdict.includes('review')) {
      return false;
    }
  }
  if (typeof model.verdict === 'boolean') return model.verdict;
  if (typeof model.final_verdict === 'boolean') return model.final_verdict;
  if (typeof model.is_phishing === 'boolean') return model.is_phishing;
  if (typeof model.score === 'number') return model.score >= 0.7;
  if (typeof model.confidence === 'number') return model.confidence >= 0.7;
  return false;
};

const toNumberLike = (value: unknown): number | null => {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
};

const extractModelScore = (model: UrlModelResponse): number => {
  const preferredKeys = [
    'confidence',
    'score',
    'probability',
    'phishing_prob',
    'risk',
    'threat_score',
    'value'
  ];

  for (const key of preferredKeys) {
    const candidate = toNumberLike((model as Record<string, unknown>)[key]);
    if (candidate !== null) {
      return candidate;
    }
  }

  const dig = (payload: unknown, depth = 0): number | null => {
    if (depth > 2 || !payload || typeof payload !== 'object') {
      return null;
    }
    for (const value of Object.values(payload)) {
      if (value === null || value === undefined) continue;
      const direct = toNumberLike(value);
      if (direct !== null) {
        return direct;
      }
      if (typeof value === 'object') {
        const nested = dig(value, depth + 1);
        if (nested !== null) {
          return nested;
        }
      }
    }
    return null;
  };

  return dig(model) ?? 0;
};

const normalizeVerdictLabel = (value: unknown): AnalyzeResponse['verdict'] | undefined => {
  if (typeof value === 'string') {
    const verdict = value.toLowerCase();
    if (verdict.includes('phish') || verdict.includes('malicious') || verdict.includes('block')) {
      return 'phish';
    }
    if (verdict.includes('suspicious') || verdict.includes('review')) {
      return 'suspicious';
    }
    if (verdict.includes('safe') || verdict.includes('benign') || verdict.includes('allow')) {
      return 'safe';
    }
  }
  if (typeof value === 'boolean') {
    return value ? 'phish' : 'safe';
  }
  return undefined;
};

const buildFusionFromModels = (models?: Record<string, UrlModelResponse>): Record<string, FusionSource> => {
  if (!models || !Object.keys(models).length) {
    return {};
  }

  return Object.entries(models).reduce<Record<string, FusionSource>>((acc, [name, model]) => {
    const rawScore = extractModelScore(model);
    let score = normalizeScore(rawScore);

    let label: AnalyzeResponse['verdict'] =
      normalizeVerdictLabel(model.label) ??
      normalizeVerdictLabel(model.verdict) ??
      (booleanFromModel(model) ? 'phish' : score >= 0.5 ? 'suspicious' : 'safe');

    if (!score) {
      if (label === 'phish') {
        score = 1;
      } else if (label === 'suspicious') {
        score = 0.5;
      }
    }

    acc[name] = {
      label,
      score: Math.round(score * 1000) / 1000
    };
    return acc;
  }, {});
};

const titleCaseSource = (name: string): string =>
  name
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());

const buildAgentFromModels = (
  models: Record<string, UrlModelResponse> | undefined,
  verdict: AnalyzeResponse['verdict']
): AgentSummary | undefined => {
  if (!models || !Object.keys(models).length) {
    return undefined;
  }

  const steps: AgentStep[] = Object.entries(models).map(([source, model]) => {
    const score = normalizeScore(model.confidence ?? model.score ?? 0);

    const status: AgentStepStatus = booleanFromModel(model) ? 'complete' : 'complete';

    return {
      id: source,
      title: titleCaseSource(source),
      description: 'Live analyzer output from backend fusion service.',
      status,
      action: 'run' as const,
      output: model.reason ?? (model.reasons?.[0] ?? `Confidence ${(score * 100).toFixed(1)}%`),
      duration_ms: model.elapsed_ms ?? 180
    } satisfies AgentStep;
  });

  const elapsed = steps.reduce((sum, step) => sum + (step.duration_ms ?? 120), 0);

  return {
    planner: 'Live fusion orchestrator routed analyzers based on payload metadata.',
    conclusion:
      verdict === 'phish'
        ? 'Fusion flagged phishing indicators across multiple analyzers.'
        : verdict === 'suspicious'
          ? 'Signals mixed; recommend manual review.'
          : 'No strong phishing indicators detected.',
    steps,
    elapsed_ms: elapsed,
    guardrails: {
      budget_ms: 3000,
      consumed_ms: elapsed,
      escalated: verdict === 'phish',
      note: 'Guardrail summary synthesized from analyzer timings.'
    }
  };
};

const fallbackFusion = (
  verdict: AnalyzeResponse['verdict'],
  probability: number
): Record<string, FusionSource> => ({
  consensus: {
    label: verdict,
    score: Math.round(probability * 1000) / 1000
  }
});

const collectReasons = (models?: Record<string, UrlModelResponse>): string[] => {
  if (!models) return [];
  const reasons: string[] = [];
  Object.values(models).forEach((model) => {
    if (typeof model.reason === 'string' && model.reason.trim()) {
      reasons.push(model.reason.trim());
    }

    if (!model.reasons) {
      return;
    }

    if (Array.isArray(model.reasons)) {
      model.reasons.forEach((item) => {
        if (typeof item === 'string' && item.trim()) {
          reasons.push(item.trim());
        }
      });
      return;
    }

    if (typeof model.reasons === 'string' && model.reasons.trim()) {
      reasons.push(model.reasons.trim());
    }
  });
  return reasons;
};

const collectUrls = (models?: Record<string, UrlModelResponse>): string[] => {
  if (!models) return [];
  const urls = new Set<string>();
  Object.values(models).forEach((model) => {
    model.extracted_urls?.forEach((url) => {
      if (url) urls.add(url);
    });
  });
  return [...urls];
};

const adaptUrlResponse = (response: UrlAnalysisResponse): AnalyzeResponse => {
  const phishingProb = normalizeScore(response.confidence);
  const verdict: AnalyzeResponse['verdict'] = response.final_verdict
    ? 'phish'
    : phishingProb > 0.55
      ? 'suspicious'
      : 'safe';

  const fusion = buildFusionFromModels(response.models);
  const extractedFromModels = collectUrls(response.models);
  const visualSignals = response.visual_reasons ?? [];
  const modelReasons = collectReasons(response.models);

  return {
    verdict,
    phishing_prob: phishingProb,
    fusion: Object.keys(fusion).length ? fusion : fallbackFusion(verdict, phishingProb),
    detected_brands: response.detected_brands ?? [],
    visual_reasons: [...visualSignals, ...modelReasons],
    extracted_urls: [...new Set([...(response.extracted_urls ?? []), ...extractedFromModels])],
    model_version: response.model_version ?? 'url_service_v2',
    request_id: response.request_id ?? safeRequestId(),
    timestamp: response.timestamp ?? new Date().toISOString(),
    agent: response.agent ?? buildAgentFromModels(response.models, verdict)
  };
};

const adaptTextResponse = (response: TextAnalysisResponse): AnalyzeResponse => {
  const phishingProb = normalizeScore(response.confidence);
  const verdict: AnalyzeResponse['verdict'] = response.is_phishing
    ? 'phish'
    : phishingProb > 0.55
      ? 'suspicious'
      : 'safe';

  return {
    verdict,
    phishing_prob: phishingProb,
    fusion: {
      distilbert: {
        label: verdict,
        score: Math.round(phishingProb * 1000) / 1000
      }
    },
    detected_brands: [],
    visual_reasons: response.reasons ?? [],
    extracted_urls: response.extracted_urls ?? [],
    model_version: response.model_version ?? 'text_service_v2',
    request_id: response.request_id ?? safeRequestId(),
    timestamp: response.timestamp ?? new Date().toISOString()
  };
};

const postJson = async <T>(path: string, body: Record<string, unknown>): Promise<T> => {
  if (!API_BASE_URL) {
    throw new Error('Set VITE_API_BASE_URL to connect to the live analysis service.');
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    let message: string | undefined;
    try {
      const data = await response.json();
      message = data?.detail ?? data?.message;
    } catch {
      message = await response.text();
    }
    throw new Error(message || `Analysis API ${response.status} error.`);
  }

  return response.json() as Promise<T>;
};

export const analyzeRequest = async (payload: AnalyzePayload): Promise<AnalyzeResponse> => {
  if (!API_BASE_URL) {
    return analyzeMockRequest(payload);
  }

  if (payload.mode === 'image') {
    throw new Error('Image ingress is not yet enabled in this frontend build.');
  }

  try {
    if (payload.mode === 'url') {
      const liveResponse = await postJson<UrlAnalysisResponse>(ROUTES.url, { url: payload.value });
      return adaptUrlResponse(liveResponse);
    }

    const liveResponse = await postJson<TextAnalysisResponse>(ROUTES.text, { text: payload.value });
    return adaptTextResponse(liveResponse);
  } catch (error) {
    console.error('Live analysis request failed', error);
    throw error instanceof Error ? error : new Error('Live analysis request failed.');
  }
};
