import { motion } from 'framer-motion';
import type { AgentStep } from '@utils/mockApi';

interface AgentDemoTrackProps {
  steps: AgentStep[];
}

const statusAccent: Record<string, string> = {
  complete: 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200',
  running: 'border-amber-400/40 bg-amber-500/10 text-amber-200',
  pending: 'border-slate-400/40 bg-slate-500/10 text-slate-200'
};

const stepIcons: Record<string, string> = {
  plan: '🧭',
  planner: '🧭',
  text: '📝',
  textanalyzer: '📝',
  url: '🔗',
  urlscanner: '🔗',
  image: '🖼️',
  imagevision: '🖼️',
  decision: '⚖️'
};

const AgentDemoTrack = ({ steps }: AgentDemoTrackProps) => {
  return (
    <div className="relative mt-8">
      <div className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-white/10" aria-hidden />
      <ol className="space-y-10">
        {steps.map((step, idx) => {
          const isLeft = idx % 2 === 0;
          const icon = stepIcons[step.id.toLowerCase()] || '⚙️';
          const card = (
            <motion.div
              className="relative w-full max-w-sm rounded-2xl border border-white/10 bg-slate-950/70 p-5 backdrop-blur"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: idx * 0.15 }}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-2xl">
                  {icon}
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Phase {String(idx + 1).padStart(2, '0')}</p>
                  <p className="text-lg font-semibold text-white">{step.title}</p>
                </div>
              </div>
              <p className="mt-3 text-sm text-slate-300">{step.description}</p>
              {step.output && <p className="mt-2 text-xs text-slate-400">{step.output}</p>}
              <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                <span className={`rounded-full border px-3 py-1 uppercase tracking-widest ${statusAccent[step.status]}`}>
                  {step.status}
                </span>
                {typeof step.duration_ms === 'number' && <span>{step.duration_ms} ms</span>}
              </div>
            </motion.div>
          );

          return (
            <li key={step.id} className="relative grid grid-cols-[1fr_auto_1fr] items-center gap-6">
              <div
                className={`relative flex ${isLeft ? 'justify-end pr-6' : 'justify-end pr-6 opacity-0 pointer-events-none'}`}
                aria-hidden={!isLeft}
              >
                {isLeft && (
                  <>
                    <div className="absolute right-0 top-1/2 h-px w-6 -translate-y-1/2 bg-white/20" />
                    {card}
                  </>
                )}
              </div>
              <div className="relative flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-gradient-to-br from-slate-900 to-slate-800 text-sm font-bold text-white shadow-xl">
                {String(idx + 1).padStart(2, '0')}
                {idx !== steps.length - 1 && (
                  <span className="absolute left-1/2 top-12 h-10 w-px -translate-x-1/2 bg-white/10" aria-hidden />
                )}
              </div>
              <div
                className={`relative flex ${!isLeft ? 'justify-start pl-6' : 'justify-start pl-6 opacity-0 pointer-events-none'}`}
                aria-hidden={isLeft}
              >
                {!isLeft && (
                  <>
                    <div className="absolute left-0 top-1/2 h-px w-6 -translate-y-1/2 bg-white/20" />
                    {card}
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
};

export default AgentDemoTrack;
