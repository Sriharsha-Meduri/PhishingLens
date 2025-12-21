import type { AgentSummary, AnalyzeResponse } from '@utils/mockApi';

interface AgentTimelineProps {
  agent?: AgentSummary;
  verdict: AnalyzeResponse['verdict'];
}

const verdictAccent: Record<AnalyzeResponse['verdict'], { label: string; badge: string }> = {
  phish: { label: 'Block', badge: 'bg-rose-500/15 text-rose-200 border-rose-400/40' },
  suspicious: { label: 'Escalate', badge: 'bg-amber-500/15 text-amber-200 border-amber-400/40' },
  safe: { label: 'Allow', badge: 'bg-emerald-500/15 text-emerald-200 border-emerald-400/40' }
};

const stepIcons: Record<string, string> = {
  plan: '🧠',
  planner: '🧠',
  text: '📝',
  textanalyzer: '📝',
  url: '🔗',
  urlscanner: '🔗',
  image: '🖼️',
  imagevision: '🖼️',
  sandbox: '🧪',
  decision: '⚖️'
};

const statusBadge = (status: string) => {
  if (status === 'complete') return 'bg-emerald-500/15 text-emerald-200 border-emerald-400/30';
  if (status === 'running') return 'bg-amber-500/15 text-amber-200 border-amber-400/30';
  return 'bg-slate-500/15 text-slate-300 border-white/10';
};

const actionMeta = {
  run: {
    badge: 'border-white/10 bg-slate-950/60',
    label: 'Primary',
    pill: 'border-white/10 bg-white/5 text-white/80',
    dot: 'bg-emerald-400'
  },
  skipped: {
    badge: 'border-violet-400/40 bg-violet-500/15 shadow-[0_0_15px_rgba(139,92,246,0.3)]',
    label: 'Skipped',
    pill: 'border-violet-400/40 bg-violet-500/15 text-violet-100',
    dot: 'bg-violet-400'
  },
  added: {
    badge: 'border-cyan-400/40 bg-cyan-500/15 shadow-[0_0_15px_rgba(34,211,238,0.35)]',
    label: 'Ad-hoc',
    pill: 'border-cyan-400/40 bg-cyan-500/15 text-cyan-100',
    dot: 'bg-cyan-400'
  }
} satisfies Record<string, { badge: string; label: string; pill: string; dot: string }>;

const AgentTimeline = ({ agent, verdict }: AgentTimelineProps) => {
  if (!agent) return null;

  const accent = verdictAccent[verdict];
  const budgetPct = Math.min(Math.round((agent.guardrails.consumed_ms / agent.guardrails.budget_ms) * 100), 200);
  const uniqueActions = Array.from(new Set(agent.steps.map((step) => step.action))).filter((action) => action !== 'run');

  return (
    <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-950 to-slate-900 p-6 text-white">
      <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-white/10 to-transparent" aria-hidden />
      <div className="relative flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-sky-300/80">Agent Activity</p>
          <h3 className="text-3xl font-semibold tracking-tight">Autonomous workflow trace</h3>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="group inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.3em] text-slate-200 transition hover:bg-white/10"
          >
            Copy Trace
            <svg className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-px" viewBox="0 0 20 20" fill="none">
              <path d="M6 6V4c0-1.1.9-2 2-2h6c1.1 0 2 .9 2 2v8c0 1.1-.9 2-2 2h-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              <rect x="2" y="6" width="8" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </button>
          <span className={`rounded-full border px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] ${accent.badge}`}>
            {accent.label}
          </span>
        </div>
      </div>

      <p className="relative mt-4 text-sm text-slate-300">{agent.conclusion}</p>

      <ol className="relative mt-8 space-y-4">
        {agent.steps.map((step, idx) => {
          const key = step.id.toLowerCase();
          const icon = stepIcons[key] || '⚙️';
          const actionStyle = actionMeta[step.action] ?? actionMeta.run;
          return (
            <li key={step.id} className="relative flex gap-4 rounded-2xl border border-white/5 bg-white/5 p-4">
              <div className="flex flex-col items-center">
                <div className={`flex h-12 w-12 items-center justify-center rounded-2xl border text-xl ${actionStyle.badge}`}>
                  {icon}
                </div>
                {idx !== agent.steps.length - 1 && <div className="mt-2 h-full w-0.5 bg-white/10" />}
              </div>
              <div className="flex-1 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.4em] text-slate-400">Step {String(idx + 1).padStart(2, '0')}</p>
                    <p className="text-lg font-semibold text-white">{step.title}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold capitalize ${statusBadge(step.status)}`}>
                      {step.status}
                    </span>
                    {step.action !== 'run' && (
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-widest ${actionMeta[step.action].pill}`}>
                        {actionMeta[step.action].label}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-sm text-slate-300">{step.description}</p>
                {step.output && <p className="text-sm text-slate-400">{step.output}</p>}
                {step.reason && (
                  <p className="text-xs text-slate-400">Note: {step.reason}</p>
                )}
                <div className="flex items-center gap-4 text-xs text-slate-400">
                  {typeof step.duration_ms === 'number' && <span>{step.duration_ms} ms</span>}
                  <span className="font-mono text-white/70">ID: {step.id}</span>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
      {uniqueActions.length > 0 && (
        <div className="mt-6 flex flex-wrap items-center gap-3 text-xs text-slate-400">
          {uniqueActions.map((action) => (
            <span key={action} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1">
              <span className={`h-2 w-2 rounded-full ${actionMeta[action].dot}`} />
              {actionMeta[action].label} steps
            </span>
          ))}
        </div>
      )}

      <div className="mt-8 grid gap-4 rounded-2xl border border-white/5 bg-white/5 p-4 text-xs uppercase tracking-[0.3em] text-slate-400 sm:grid-cols-2">
        <div>
          <p className="text-[11px] text-white/60">Total agent time</p>
          <p className="mt-1 text-lg font-semibold tracking-tight text-white">{(agent.elapsed_ms / 1000).toFixed(2)}s</p>
        </div>
        <div>
          <p className="text-[11px] text-white/60">Guardrail budget</p>
          <p className="mt-1 text-lg font-semibold tracking-tight text-white">{budgetPct}% used</p>
          <p className="text-[10px] normal-case text-slate-300">{agent.guardrails.note}</p>
        </div>
        <div className="sm:col-span-2 flex flex-wrap items-center justify-between gap-3 text-[11px] normal-case">
          <span>Planner · {agent.planner}</span>
          <span>Escalation · {agent.guardrails.escalated ? 'Triggered' : 'Not needed'}</span>
        </div>
      </div>
    </section>
  );
};

export default AgentTimeline;
