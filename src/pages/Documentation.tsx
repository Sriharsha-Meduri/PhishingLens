import React from 'react';

const overviewHighlights = [
  {
    title: '🎯 Mission',
    copy: 'Protect organizations from sophisticated phishing attacks using cutting-edge AI technology.',
    tone: 'bg-blue-500/10 border-blue-400/30'
  },
  {
    title: '🚀 Innovation',
    copy: 'Multi-modal AI approach combining NLP, computer vision, and graph neural networks.',
    tone: 'bg-emerald-500/10 border-emerald-400/30'
  },
  {
    title: '🌍 Impact',
    copy: 'Achieved 96% detection accuracy with real-time decisioning and analyst-ready insights.',
    tone: 'bg-purple-500/10 border-purple-400/30'
  }
];

const techStack = [
  {
    icon: '🎨',
    title: 'Frontend',
    accent: 'from-blue-500/20 via-slate-950/70 to-transparent',
    bullets: [
      'React 18 with hooks & concurrent rendering',
      'Vite dev server + build tooling',
      'JavaScript ES2020 with async/await',
      'Tailwind CSS utility system',
      'Framer Motion micro-interactions',
      'Axios + Chrome Extension APIs'
    ]
  },
  {
    icon: '⚙️',
    title: 'Backend',
    accent: 'from-emerald-500/20 via-slate-950/70 to-transparent',
    bullets: [
      'FastAPI services on Python 3.9+',
      'Uvicorn ASGI runtime with httpx',
      'Pydantic validation & typed contracts',
      'Asyncio orchestrated microservices',
      'Structured logging + tracing'
    ]
  },
  {
    icon: '🤖',
    title: 'AI / ML',
    accent: 'from-purple-500/20 via-slate-950/70 to-transparent',
    bullets: [
      'DistilBERT NLP inference (ONNX)',
      'MobileNet vision phishing scan',
      'Graph neural networks for URL intel',
      'ONNX Runtime acceleration',
      'OpenPhish + HuggingFace integrations'
    ]
  },
  {
    icon: '🏗️',
    title: 'Infrastructure',
    accent: 'from-amber-500/20 via-slate-950/70 to-transparent',
    bullets: [
      'Dockerized services, Compose & Helm',
      'Kubernetes blue/green rollouts',
      'Prometheus + Grafana dashboards',
      'Nginx / Redis edge & cache layer'
    ]
  }
];

const architecturePillars = [
  {
    icon: '🌐',
    label: 'API Gateway',
    copy: 'Central entry, auth, throttling, and traffic shaping across services.'
  },
  {
    icon: '📝',
    label: 'Text Service',
    copy: 'DistilBERT ONNX worker analyzing email, SMS, and chat payloads.'
  },
  {
    icon: '🔗',
    label: 'URL Service',
    copy: '4-source fusion: pattern scanner, HF transformer, graph intel, and OTX feeds.'
  },
  {
    icon: '🖼️',
    label: 'Image Service',
    copy: 'MobileNet classifier with OCR + brand signature detection.'
  }
];

const pipelines = [
  {
    title: '📝 Text Analysis Pipeline',
    bullets: [
      'Pre-processing, cleanup, and tokenization',
      'DistilBERT inference (quantized ONNX runtime)',
      'Feature extraction & heuristics blend',
      'Confidence scoring + classification',
      'Reason generation for analyst explainability'
    ]
  },
  {
    title: '🔗 URL Analysis Pipeline',
    bullets: [
      'URL parsing & lexical feature extraction',
      'Pattern scanner + transformer verdicts',
      'Graph traversal for relationship risk',
      'OTX + OpenPhish intelligence merge',
      '4-source fusion for final decision'
    ]
  },
  {
    title: '🖼️ Image Analysis Pipeline',
    bullets: [
      'Normalization & asset sanitization',
      'MobileNet phishing detection',
      'Brand & logo recognition layer',
      'OCR text extraction + NLP review',
      'Multi-modal fusion confidence output'
    ]
  }
];

const performanceStats = [
  { label: 'Detection Accuracy', value: '96%', tone: 'text-rose-300 bg-rose-500/10 border-rose-500/30' },
  { label: 'Average Response Time', value: '<500ms', tone: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30' },
  { label: 'System Uptime', value: '99.9%', tone: 'text-sky-300 bg-sky-500/10 border-sky-500/30' },
  { label: 'Threats Detected', value: '2.4M+', tone: 'text-violet-300 bg-violet-500/10 border-violet-500/30' }
];

const benchmarkStats = [
  { label: 'Text Analysis', copy: 'Avg: 200ms · Max: 500ms' },
  { label: 'URL Analysis', copy: 'Avg: 300ms · Max: 800ms' },
  { label: 'Image Analysis', copy: 'Avg: 400ms · Max: 1s' },
  { label: 'Memory Usage', copy: 'Peak: 2GB · Avg: 1.2GB' }
];

const operations = [
  {
    title: '🐳 Containerization',
    bullets: [
      'Docker microservices with multi-stage builds',
      'Automated health checks + restart policies',
      'Resource quotas, seccomp, and vulnerability scan'
    ]
  },
  {
    title: '📊 Monitoring',
    bullets: [
      'Prometheus metrics and trace exports',
      'Grafana situational dashboards',
      'Alert routing + Slack/PagerDuty hooks'
    ]
  },
  {
    title: '🔄 CI/CD Pipeline',
    bullets: [
      'Automated testing & supply-chain scanning',
      'Container registry promotion gates',
      'Kubernetes rolling updates & instant rollbacks'
    ]
  }
];

const apiEndpoints = [
  {
    method: 'POST',
    route: '/analyze_text',
    description: 'Analyze text payloads for phishing signals.',
    request: '{ "text": "string" }',
    response: '{ "is_phishing": boolean, "confidence": number, "reasons": [] }'
  },
  {
    method: 'POST',
    route: '/analyze_url_v2',
    description: 'Enhanced URL analysis with 4-source fusion.',
    request: '{ "url": "string" }',
    response: '{ "final_verdict": boolean, "confidence": number, "models": { ... } }'
  },
  {
    method: 'POST',
    route: '/analyze_image_v2',
    description: 'Screenshot/image vetting with brand detection.',
    request: '{ "image_base64": "string" }',
    response: '{ "is_phishing": boolean, "confidence": number, "detected_brands": [] }'
  }
];

const Section = ({ title, children, icon }: { title: string; children: React.ReactNode; icon: string }) => (
  <section className="bg-slate-950/80 text-white rounded-3xl border border-white/10 shadow-2xl shadow-black/40 p-8 md:p-10 backdrop-blur-xl">
    <div className="flex items-center gap-3 mb-6">
      <span className="text-3xl" aria-hidden>
        {icon}
      </span>
      <h2 className="text-2xl font-bold tracking-tight text-white">{title}</h2>
    </div>
    {children}
  </section>
);

const Documentation = () => {
  return (
    <div className="relative min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),transparent_45%)]" aria-hidden />
      <div className="relative z-10 mx-auto max-w-6xl px-4 pb-24 pt-32 text-white">
        <header className="text-center mb-16">
          <p className="text-sm uppercase tracking-[0.3em] text-sky-300">Product Documentation</p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight md:text-5xl">
            Everything you need to operate <span className="text-sky-300">PhishingLens Intelligence</span>
          </h1>
          <p className="mt-4 text-base text-slate-300 md:text-lg">
            Architecture, pipelines, metrics, and deployment notes migrated from the original design doc, reimagined to match the live experience.
          </p>
        </header>

        <div className="space-y-10">
          <Section title="Project Overview" icon="🎯">
            <p className="text-slate-300 text-base leading-relaxed">
              PhishingLens combines multiple machine learning models to inspect text, URLs, and rich media simultaneously. The platform blends deterministic checks with adaptive AI to deliver explainable verdicts under 500 ms.
            </p>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {overviewHighlights.map((item) => (
                <div key={item.title} className={`rounded-2xl border px-5 py-4 ${item.tone} text-slate-100`}>
                  <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                  <p className="text-sm text-slate-100/80 leading-relaxed">{item.copy}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Technology Stack" icon="🛠️">
            <div className="grid gap-4 md:grid-cols-2">
              {techStack.map((item) => (
                <div key={item.title} className={`rounded-2xl border border-white/10 bg-gradient-to-br ${item.accent} p-6`}>
                  <div className="flex items-center gap-3 text-lg font-semibold text-white">
                    <span>{item.icon}</span>
                    {item.title}
                  </div>
                  <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-200">
                    {item.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </Section>

          <Section title="System Architecture" icon="🏗️">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {architecturePillars.map((pillar) => (
                <article key={pillar.label} className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 text-slate-100">
                  <div className="text-3xl mb-3">{pillar.icon}</div>
                  <h3 className="text-base font-semibold mb-2 text-white">{pillar.label}</h3>
                  <p className="text-sm leading-relaxed text-slate-200/80">{pillar.copy}</p>
                </article>
              ))}
            </div>
            <div className="mt-8 rounded-2xl border border-white/10 bg-slate-900/70 p-6 text-slate-200">
              <h3 className="font-semibold text-white mb-3">🔄 Data Flow</h3>
              <ol className="list-decimal space-y-2 pl-5 text-sm leading-relaxed text-slate-300">
                <li>Clients submit text, URLs, or imagery via web app, extension, or API.</li>
                <li>API Gateway authenticates, rate-limits, and routes workload to specialized services.</li>
                <li>Model services run ONNX, transformer, and graph workloads in parallel.</li>
                <li>Fusion layer aggregates verdicts, confidence scores, and enrichment.</li>
                <li>Decision engine applies policy, safe-list, and tenant controls.</li>
                <li>Responses return with human-readable explanations for auditability.</li>
                <li>Metrics + logs stream into Prometheus, Loki, and SIEM connectors.</li>
              </ol>
            </div>
          </Section>

          <Section title="Working Model" icon="⚙️">
            <div className="grid gap-4 md:grid-cols-3">
              {pipelines.map((pipeline) => (
                <div key={pipeline.title} className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 text-slate-200">
                  <h3 className="text-base font-semibold text-white mb-3">{pipeline.title}</h3>
                  <ol className="list-decimal space-y-2 pl-5 text-sm leading-relaxed text-slate-300">
                    {pipeline.bullets.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Performance Metrics" icon="📊">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {performanceStats.map((stat) => (
                <div key={stat.label} className={`rounded-2xl border p-6 text-center ${stat.tone}`}>
                  <div className="text-3xl font-bold">{stat.value}</div>
                  <p className="mt-2 text-sm text-slate-200/80">{stat.label}</p>
                </div>
              ))}
            </div>
            <div className="mt-8 rounded-2xl border border-white/10 bg-slate-950/50 p-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-sm">
                {benchmarkStats.map((item) => (
                  <div key={item.label} className="rounded-xl border border-white/10 bg-slate-900/70 p-4 text-slate-200">
                    <h4 className="font-semibold text-white">{item.label}</h4>
                    <p className="mt-2 text-slate-300">{item.copy}</p>
                  </div>
                ))}
              </div>
            </div>
          </Section>

          <Section title="Deployment & Operations" icon="🚀">
            <div className="grid gap-4 md:grid-cols-3">
              {operations.map((op) => (
                <article key={op.title} className="rounded-2xl border border-white/10 bg-slate-900/70 p-6 text-slate-200">
                  <h3 className="text-base font-semibold text-white mb-3">{op.title}</h3>
                  <ul className="list-disc space-y-2 pl-5 text-sm text-slate-300">
                    {op.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </Section>

          <Section title="API Documentation" icon="📚">
            <div className="space-y-4">
              {apiEndpoints.map((endpoint) => (
                <article key={endpoint.route} className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 font-mono text-sm text-slate-200">
                  <div className="flex flex-wrap items-center gap-3 text-white">
                    <span className="rounded-full bg-white/10 text-sky-300 px-3 py-0.5 text-xs font-semibold">{endpoint.method}</span>
                    <span className="text-base font-semibold">{endpoint.route}</span>
                  </div>
                  <p className="mt-2 text-slate-300">{endpoint.description}</p>
                  <div className="mt-4 space-y-1">
                    <p className="text-amber-300">Request:</p>
                    <code className="block rounded-lg border border-white/10 bg-slate-950/70 p-3 text-slate-100">{endpoint.request}</code>
                    <p className="pt-2 text-emerald-300">Response:</p>
                    <code className="block rounded-lg border border-white/10 bg-slate-950/70 p-3 text-slate-100">{endpoint.response}</code>
                  </div>
                </article>
              ))}
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
};

export default Documentation;
