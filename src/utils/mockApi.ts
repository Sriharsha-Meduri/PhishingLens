export type FusionSource = { label: 'phish' | 'safe' | 'suspicious'; score: number };

export type AnalyzeResponse = {
  verdict: 'phish' | 'safe' | 'suspicious';
  phishing_prob: number;
  fusion: Record<string, FusionSource>;
  detected_brands: string[];
  visual_reasons: string[];
  extracted_urls: string[];
  model_version: string;
  request_id: string;
  timestamp: string;
  agent?: AgentSummary;
};

export type AnalyzePayload = {
  mode: 'url' | 'text' | 'image';
  value: string;
};

export type AgentStepStatus = 'pending' | 'running' | 'complete';
export type AgentStepAction = 'run' | 'skipped' | 'added';

export type AgentStep = {
  id: string;
  title: string;
  description: string;
  status: AgentStepStatus;
  action: AgentStepAction;
  reason?: string;
  output?: string;
  duration_ms?: number;
};

export type AgentGuardrails = {
  budget_ms: number;
  consumed_ms: number;
  escalated: boolean;
  note?: string;
};

export type AgentSummary = {
  planner: string;
  conclusion: string;
  steps: AgentStep[];
  elapsed_ms: number;
  guardrails: AgentGuardrails;
};

const safeRequestId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `req_${Math.random().toString(36).slice(2, 10)}`;
};

const verdictPalette: AnalyzeResponse['verdict'][] = ['phish', 'safe', 'suspicious'];

const randomFusion = (): Record<string, FusionSource> => {
  const keys = ['DistilBERT', 'pipeline', 'graph', 'otx'];
  return keys.reduce<Record<string, FusionSource>>((acc, key) => {
    const score = Math.random();
    const label = score > 0.66 ? 'phish' : score > 0.33 ? 'suspicious' : 'safe';
    acc[key] = {
      label,
      score: Math.round(score * 1000) / 1000
    };
    return acc;
  }, {});
};

export const analyzeMockRequest = async (payload: AnalyzePayload): Promise<AnalyzeResponse> => {
  const delay = 700 + Math.random() * 500;
  await new Promise((resolve) => setTimeout(resolve, delay));

  const phishingProb = payload.value.length % 100 / 100;
  const verdict = phishingProb > 0.7 ? 'phish' : phishingProb > 0.4 ? 'suspicious' : 'safe';

  const steps: AgentStep[] = [
    {
      id: 'plan',
      title: 'Planner',
      description: 'Decide which analyzers to run based on provided payload.',
      status: 'complete',
      action: 'run',
      output: 'Need text, URL, and image checks; prioritizing URL since payload includes a link.',
      duration_ms: 120
    },
    {
      id: 'text',
      title: 'TextAnalyzer',
      description: 'DistilBERT ONNX inference on message body.',
      status: 'complete',
      action: payload.mode === 'text' ? 'run' : 'skipped',
      reason: payload.mode === 'text' ? undefined : 'Skipped because payload lacked rich text.',
      output: payload.mode === 'text' ? 'Detected urgency + credential harvest language.' : 'No text payload provided.',
      duration_ms: payload.mode === 'text' ? 340 : undefined
    },
    {
      id: 'url',
      title: 'UrlScanner',
      description: 'Scanner + HF + Graph + OTX fusion on submitted domain.',
      status: 'complete',
      action: payload.mode !== 'image' ? 'run' : 'skipped',
      reason: payload.mode !== 'image' ? undefined : 'Skipped until URL artifacts exist.',
      output: 'Domain observed on OpenPhish and newly registered 3 days ago.',
      duration_ms: 270
    },
    {
      id: 'image',
      title: 'ImageVision',
      description: 'OCR + brand signature verify screenshot attachments.',
      status: payload.mode === 'image' ? 'running' : 'complete',
      action: payload.mode === 'image' ? 'run' : 'skipped',
      reason: payload.mode === 'image' ? undefined : 'Skipped — no screenshots detected.',
      output: payload.mode === 'image' ? 'Found mismatched bank logo + base64 form.' : 'No screenshot supplied.',
      duration_ms: payload.mode === 'image' ? 480 : undefined
    },
    {
      id: 'decision',
      title: 'Decision Engine',
      description: 'Fuse tool outputs and apply policy rules.',
      status: 'complete',
      action: 'run',
      output: verdict === 'phish'
        ? 'Multiple sources high-risk. Recommend block and auto-quarantine.'
        : verdict === 'suspicious'
          ? 'Signals mixed. Escalate to analyst queue.'
          : 'Low risk. Allow but continue monitoring.',
      duration_ms: 90
    }
  ];

  const elapsedMs = steps.reduce((sum, step) => sum + (step.duration_ms ?? 60), 0);

  const agent: AgentSummary = {
    planner: 'Orchestrator v0.2 determines modality workflow based on payload metadata.',
    conclusion: steps[steps.length - 1].output ?? 'Analysis complete.',
    steps,
    elapsed_ms: elapsedMs,
    guardrails: {
      budget_ms: 2000,
      consumed_ms: elapsedMs,
      escalated: verdict === 'phish' && phishingProb > 0.85,
      note: 'Operating within normal guardrails.'
    }
  };

  return {
    verdict,
    phishing_prob: phishingProb,
    fusion: randomFusion(),
    detected_brands: ['Microsoft 365', 'Okta'].slice(0, payload.mode === 'url' ? 2 : 1),
    visual_reasons: [
      'Links to mismatched login domains',
      'Form collects credentials over http'
    ],
    extracted_urls: ['https://secure.ms-login.help', 'https://cdn-ms-assets.com/js/app.js'],
    model_version: 'analyze_url_v2',
    request_id: safeRequestId(),
    timestamp: new Date().toISOString(),
    agent
  };
};
