import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import AnalyzeForm from '@components/AnalyzeForm';
import AnalysisCard from '@components/AnalysisCard';
import AgentTimeline from '@components/AgentTimeline';
import AgentModePanel from '@components/AgentModePanel';
import ScrollFade from '@components/ScrollFade';
import type { AnalyzeResponse } from '@utils/mockApi';

interface DetailsModalProps {
  open: boolean;
  onClose: () => void;
  data: AnalyzeResponse | null;
}

const DetailsModal = ({ open, onClose, data }: DetailsModalProps) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || !modalRef.current) return;

    const focusable = modalRef.current.querySelectorAll<HTMLElement>(
      'button, [href], textarea, [tabindex]:not([tabindex="-1"])'
    );
    focusable[0]?.focus();

    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }

      if (event.key === 'Tab' && focusable.length) {
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeydown);
    return () => document.removeEventListener('keydown', handleKeydown);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && data && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="analysis-details-title"
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
          />

          <motion.div
            ref={modalRef}
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', duration: 0.5 }}
            className="glass-surface relative w-full max-w-2xl overflow-hidden rounded-3xl p-0 text-slate-900 shadow-2xl dark:text-white"
          >
            <div className="border-b border-slate-200 bg-white/90 p-6 dark:border-white/5 dark:bg-white/5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-brand-600 dark:text-brand-300">Analysis details</p>
                  <h3 id="analysis-details-title" className="mt-1 text-2xl font-bold">
                    Request {data.request_id.split('-')[0]}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="group rounded-full border border-slate-200 bg-white/70 p-2 text-slate-500 transition-colors hover:bg-white hover:text-slate-900 dark:border-white/10 dark:bg-white/5 dark:text-white/70"
                >
                  <span className="sr-only">Close modal</span>
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="grid gap-6 p-6 text-sm text-slate-600 dark:text-slate-300 md:grid-cols-2">
              <div className="space-y-2">
                <p className="font-medium text-slate-900 dark:text-white">Detected brands</p>
                {data.detected_brands.length ? (
                  <ul className="space-y-1">
                    {data.detected_brands.map((brand) => (
                      <li key={brand} className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-brand-400" />
                        {brand}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="italic text-slate-400 dark:text-slate-500">No brands detected</p>
                )}
              </div>

              <div className="space-y-2">
                <p className="font-medium text-slate-900 dark:text-white">Visual reasons</p>
                {data.visual_reasons.length ? (
                  <ul className="space-y-1">
                    {data.visual_reasons.map((reason) => (
                      <li key={reason} className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                        {reason}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="italic text-slate-400 dark:text-slate-500">No visual flags</p>
                )}
              </div>

              <div className="space-y-2 md:col-span-2">
                <p className="font-medium text-slate-900 dark:text-white">Extracted URLs</p>
                {data.extracted_urls.length ? (
                  <div className="max-h-32 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-slate-950/30">
                    <ul className="space-y-1 font-mono text-xs">
                      {data.extracted_urls.map((url) => (
                        <li key={url} className="break-all text-slate-600 dark:text-slate-300">
                          {url}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="italic text-slate-400 dark:text-slate-500">No URLs extracted</p>
                )}
              </div>

              <div className="md:col-span-2">
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white/80 p-4 dark:border-white/10 dark:bg-white/5">
                  <div>
                    <p className="text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400">Model Version</p>
                    <p className="font-mono text-brand-500 dark:text-brand-300">{data.model_version}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400">Timestamp</p>
                    <p className="font-medium text-slate-900 dark:text-white">
                      {new Date(data.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

type ExperienceMode = 'intelligence' | 'agent';

const Analyze = () => {
  const [latest, setLatest] = useState<AnalyzeResponse | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [experienceMode, setExperienceMode] = useState<ExperienceMode>('intelligence');
  const stackedPanelClass = 'mx-auto w-full max-w-4xl';
  const resultPanelRef = useRef<HTMLDivElement | null>(null);

  const handleComplete = useCallback((response: AnalyzeResponse) => {
    setLatest(response);
    setIsModalOpen(false);
  }, []);

  useEffect(() => {
    const shouldScroll = experienceMode === 'agent' ? Boolean(latest?.agent) : Boolean(latest);
    if (!shouldScroll) return;

    const timer = window.setTimeout(() => {
      const target = resultPanelRef.current;
      if (!target) return;
      const offset = target.getBoundingClientRect().top + window.scrollY - 140;
      window.scrollTo({ top: Math.max(offset, 0), behavior: 'smooth' });
    }, 180);

    return () => window.clearTimeout(timer);
  }, [experienceMode, latest]);

  const heroDescription =
    experienceMode === 'intelligence'
      ? 'Analyze URLs, text, and images with AI/ML models. Results combine Scanner + HuggingFace + Graph + OTX intelligence with 2-of-4 consensus voting.'
      : 'Agent mode replays the autonomous plan → execute → reflect loop with guardrails, so you can watch every tool fire in sequence.';

  const rightPanelPlaceholder = (
    <div className="glass-surface flex h-64 w-full flex-col items-center justify-center rounded-3xl p-8 text-center text-slate-600 dark:text-slate-400">
      <div className="mb-4 rounded-full border border-slate-200 bg-white/70 p-4 text-slate-400 dark:border-white/10 dark:bg-white/5">
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <p className="font-semibold">{experienceMode === 'intelligence' ? 'Awaiting submission…' : 'Run an analysis to watch the agent mission log.'}</p>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
        {experienceMode === 'intelligence'
          ? 'Results will show verdict from Scanner, HF transformer, Graph GNN, and OTX feeds.'
          : 'Agent mode animates each step along the guardrailed workflow.'}
      </p>
    </div>
  );

  const renderRightPanel = () => {
    if (!latest) return rightPanelPlaceholder;
    if (experienceMode === 'agent' && latest.agent) {
      return <AgentModePanel agent={latest.agent} verdict={latest.verdict} />;
    }
    return <AnalysisCard data={latest} compact onViewDetails={() => setIsModalOpen(true)} />;
  };

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-12 px-4 pb-20 pt-10 text-slate-900 dark:text-white sm:px-8">
      <ScrollFade>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-500/20 bg-brand-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-brand-600 dark:text-brand-300">
              {experienceMode === 'intelligence' ? 'Multi-Modal Detection' : 'Agent Mode Demo'}
            </div>
            <div className="flex overflow-hidden rounded-full border border-white/10 bg-white/5 text-xs font-semibold uppercase tracking-[0.3em] text-slate-400 dark:bg-white/10">
              {(['intelligence', 'agent'] as ExperienceMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setExperienceMode(mode)}
                  className={`px-4 py-2 transition ${
                    experienceMode === mode
                      ? 'bg-gradient-to-r from-brand-500 to-brand-600 text-white shadow-lg'
                      : 'hover:text-white/90'
                  }`}
                >
                  {mode === 'intelligence' ? 'Intelligence Mode' : 'Agent Mode'}
                </button>
              ))}
            </div>
          </div>
          <h1 className="text-4xl font-black text-slate-900 dark:text-white sm:text-5xl">
            {experienceMode === 'intelligence' ? '4-Source ' : 'Autonomous '}<span className="text-gradient-brand">{experienceMode === 'intelligence' ? 'fusion analysis' : 'agent replay'}</span>
          </h1>
          <p className="max-w-3xl text-lg text-slate-600 dark:text-slate-300">{heroDescription}</p>
        </div>
      </ScrollFade>

      <div className="space-y-10">
        <ScrollFade className={stackedPanelClass}>
          <div className="relative">
            <div className="absolute -inset-0.5 rounded-[2rem] bg-gradient-to-r from-brand-500 to-purple-600 opacity-20 blur-xl" />
            <div className="relative rounded-[2rem] bg-white/90 p-px dark:bg-slate-950/60">
              <AnalyzeForm
                showInlineResult={false}
                onComplete={handleComplete}
                modeStrategy={experienceMode === 'agent' ? 'auto' : 'manual'}
                autoFocusOnMount
              />
            </div>
          </div>
        </ScrollFade>

        <ScrollFade key={experienceMode} delay={0.1} className={stackedPanelClass}>
          <div ref={resultPanelRef} className="w-full">
            {renderRightPanel()}
          </div>
        </ScrollFade>
      </div>

      {experienceMode === 'intelligence' && latest?.agent && (
        <ScrollFade delay={0.15}>
          <AgentTimeline agent={latest.agent} verdict={latest.verdict} />
        </ScrollFade>
      )}

      <DetailsModal open={isModalOpen} onClose={() => setIsModalOpen(false)} data={latest} />
    </div>
  );
};

export default Analyze;
