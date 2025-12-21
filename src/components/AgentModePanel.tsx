import { useState } from 'react';
import AgentDemoTrack from '@components/AgentDemoTrack';
import type { AgentSummary, AnalyzeResponse } from '@utils/mockApi';

interface AgentModePanelProps {
  agent: AgentSummary;
  verdict: AnalyzeResponse['verdict'];
}

const verdictChip: Record<AnalyzeResponse['verdict'], string> = {
  phish: 'text-rose-200 border-rose-400/40 bg-rose-500/10',
  suspicious: 'text-amber-200 border-amber-400/40 bg-amber-500/10',
  safe: 'text-emerald-200 border-emerald-400/40 bg-emerald-500/10'
};

const AgentModePanel = ({ agent, verdict }: AgentModePanelProps) => {
  const [showDetails, setShowDetails] = useState(false);
  const guardrailUsage = Math.min(Math.round((agent.guardrails.consumed_ms / agent.guardrails.budget_ms) * 100), 200);

  return (
    <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-900 p-6 text-white shadow-2xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.4em] text-sky-300/80">Agent replay</p>
          <p className="text-2xl font-semibold">{agent.conclusion}</p>
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] ${verdictChip[verdict]}`}>
              {verdict}
            </span>
            <span>Planner · {agent.planner}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Elapsed</p>
          <p className="text-3xl font-bold">{(agent.elapsed_ms / 1000).toFixed(2)}s</p>
          <p className="text-xs text-slate-400">Guardrail usage · {guardrailUsage}%</p>
        </div>
      </div>

      <AgentDemoTrack steps={agent.steps} />

      <div className="mt-8">
        <button
          type="button"
          onClick={() => setShowDetails((prev) => !prev)}
          className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-200 transition hover:border-white/40 hover:bg-white/10"
        >
          {showDetails ? 'Hide guardrail details' : 'Show guardrail details'}
          <span className={`transition-transform ${showDetails ? 'rotate-180' : ''}`}>
            <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 4l3 3 3-3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
        </button>

        {showDetails && (
          <div className="mt-4 grid gap-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs uppercase tracking-[0.3em] text-slate-300 sm:grid-cols-2">
            <div>
              <p className="text-[11px] text-white/70">Escalation</p>
              <p className="mt-1 text-lg font-semibold text-white">{agent.guardrails.escalated ? 'Triggered' : 'Not required'}</p>
            </div>
            <div>
              <p className="text-[11px] text-white/70">Budget note</p>
              <p className="mt-1 text-sm normal-case text-slate-200">{agent.guardrails.note}</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default AgentModePanel;
