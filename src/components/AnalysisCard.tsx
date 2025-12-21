import { AnalyzeResponse } from '@utils/mockApi';

interface AnalysisCardProps {
  data: AnalyzeResponse;
  compact?: boolean;
  onViewDetails?: () => void;
}

const verdictStyles: Record<AnalyzeResponse['verdict'], string> = {
  phish: 'bg-rose-500/10 text-rose-400 border-rose-500/20 ring-rose-500/20',
  safe: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 ring-emerald-500/20',
  suspicious: 'bg-amber-500/10 text-amber-400 border-amber-500/20 ring-amber-500/20'
};

const AnalysisCard = ({ data, compact = false, onViewDetails }: AnalysisCardProps) => {
  const phishingPercent = Math.round(data.phishing_prob * 100);
  const safetyPercent = Math.max(0, 100 - phishingPercent);
  const keyFindings = data.visual_reasons.slice(0, 4);
  const detectedBrands = data.detected_brands.slice(0, 4);
  const extractedSamples = data.extracted_urls.slice(0, 3);

  return (
    <article
      className={`glass-surface relative overflow-hidden rounded-3xl p-6 transition-all hover:bg-white dark:hover:bg-slate-900/60 ${compact ? 'space-y-5' : 'space-y-8'
        }`}
    >
      {/* Background glow based on verdict yeqhh*/}
      <div className={`absolute -right-20 -top-20 h-64 w-64 rounded-full blur-3xl opacity-20 pointer-events-none ${data.verdict === 'phish' ? 'bg-rose-500' :
          data.verdict === 'safe' ? 'bg-emerald-500' : 'bg-amber-500'
        }`} />

      <div className="relative flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">Analysis Verdict</p>
          <div className="mt-2 flex items-center gap-4">
            <span className={`rounded-full border px-4 py-1.5 text-sm font-bold uppercase tracking-wide shadow-sm ring-1 ring-inset ${verdictStyles[data.verdict]}`}>
              {data.verdict}
            </span>
            <div className="space-y-1">
              <div className="flex items-baseline gap-1.5">
                <span className="text-4xl font-black tracking-tight text-slate-900 dark:text-white">{phishingPercent}%</span>
                <span className="text-sm font-medium text-slate-500 dark:text-slate-400">phishing likelihood</span>
              </div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">Model confidence (phishing)</p>
            </div>
          </div>
        </div>
        {onViewDetails && (
          <button
            type="button"
            className="group flex items-center gap-2 rounded-full border border-slate-300 bg-slate-100 px-5 py-2.5 text-sm font-medium text-slate-900 transition-all hover:bg-slate-200 hover:pr-4 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
            onClick={onViewDetails}
          >
            View Details
            <svg className="h-4 w-4 text-slate-500 transition-transform group-hover:translate-x-0.5 group-hover:text-slate-900 dark:text-slate-400 dark:group-hover:text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </div>

      <div className="relative space-y-2">
        <div className="flex justify-between text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-500">
          <span>Safe meter</span>
          <span>{safetyPercent}/100</span>
        </div>
        <div className="probability-bar relative h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800/50 ring-1 ring-slate-300 dark:ring-white/5">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-rose-500 via-amber-500 to-emerald-500 transition-all duration-700 ease-out"
            style={{ width: `${safetyPercent}%` }}
          />
          <div className="absolute inset-0 flex items-center justify-between px-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            <span>0%</span>
            <span>100%</span>
          </div>
        </div>
      </div>

      <div className="relative">
        <p className="text-xs font-medium uppercase tracking-wider text-slate-500 dark:text-slate-400">Intelligence Fusion</p>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {Object.entries(data.fusion).map(([source, details]) => (
            <li key={source} className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white/70 p-3 transition-colors hover:border-slate-300 hover:bg-white dark:border-white/5 dark:bg-white/[0.02] dark:hover:border-white/10 dark:hover:bg-white/10">
              <div className="flex items-center gap-3">
                <div className={`h-2 w-2 rounded-full ${details.score > 0.7 ? 'bg-rose-500' : details.score > 0.3 ? 'bg-amber-500' : 'bg-emerald-500'
                  }`} />
                <div>
                  <p className="font-semibold capitalize text-slate-900 dark:text-slate-200">{source}</p>
                  <p className="text-xs text-slate-600 dark:text-slate-500">{details.label}</p>
                </div>
              </div>
              <span className="font-mono text-sm font-medium text-slate-600 group-hover:text-slate-900 dark:text-slate-400 dark:group-hover:text-white">
                {Math.round(details.score * 100)}%
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-500">Scores reflect each source's estimated phishing probability.</p>
      </div>

      <div className="relative grid gap-4 rounded-3xl border border-slate-200/80 bg-white/70 p-5 text-sm dark:border-white/10 dark:bg-white/5 sm:grid-cols-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">Key Findings</p>
          {keyFindings.length ? (
            <ul className="mt-3 space-y-1 text-slate-700 dark:text-slate-200">
              {keyFindings.map((reason) => (
                <li key={reason} className="flex items-start gap-2 text-xs sm:text-sm">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-amber-400" />
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-xs italic text-slate-400">No reasons reported</p>
          )}
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">Detected Brands</p>
          {detectedBrands.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {detectedBrands.map((brand) => (
                <span
                  key={brand}
                  className="rounded-full bg-brand-500/10 px-3 py-1 text-xs font-semibold text-brand-600 dark:text-brand-300"
                >
                  {brand}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-xs italic text-slate-400">No brand collisions</p>
          )}
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">Extracted URLs</p>
          {extractedSamples.length ? (
            <ul className="mt-3 space-y-1 font-mono text-[11px] text-slate-600 dark:text-slate-300">
              {extractedSamples.map((url) => (
                <li key={url} className="truncate" title={url}>
                  {url}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-xs italic text-slate-400">No URLs extracted</p>
          )}
        </div>
      </div>

      {data.agent && (
        <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-950 p-5 text-white">
          <div className="absolute -right-10 top-1/2 h-32 w-32 -translate-y-1/2 rounded-full bg-brand-500/20 blur-3xl" aria-hidden />
          <div className="relative flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-[0.4em] text-sky-300/80">Agent Conclusion</p>
              <p className="text-base text-slate-200">{data.agent.conclusion}</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Elapsed</p>
              <p className="text-2xl font-semibold">{(data.agent.elapsed_ms / 1000).toFixed(2)}s</p>
            </div>
          </div>
          <div className="relative mt-6 h-1.5 w-full rounded-full bg-white/10">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-400"
              style={{ width: `${Math.min((data.agent.elapsed_ms / 1500) * 100, 100)}%` }}
            />
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            {data.agent.steps.map((step) => {
              const actionLabel = step.action === 'skipped' ? 'Skipped' : step.action === 'added' ? 'Ad-hoc' : null;
              const actionTone = step.action === 'skipped'
                ? 'bg-violet-500/10 text-violet-200 border-violet-400/30'
                : 'bg-cyan-500/10 text-cyan-200 border-cyan-400/30';

              return (
                <span
                  key={step.id}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium uppercase tracking-wide"
                  title={step.reason}
                >
                  <span
                    className={`h-2 w-2 rounded-full ${
                      step.status === 'complete'
                        ? 'bg-emerald-400'
                        : step.status === 'running'
                          ? 'bg-amber-300'
                          : 'bg-slate-500'
                    }`}
                  />
                  <span className="text-white/90">{step.title}</span>
                  {step.action !== 'skipped' && (
                    <span className="text-slate-400">· {step.status}</span>
                  )}
                  {actionLabel && (
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${actionTone}`}>
                      {actionLabel}
                    </span>
                  )}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </article>
  );
};

export default AnalysisCard;
