import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import AnalyzeForm from '@components/AnalyzeForm';
import ScrollFade from '@components/ScrollFade';
import Globe from '@components/Globe';
import ComparisonTable from '@components/ComparisonTable';
import PerformanceChart from '@components/PerformanceChart';

const features = [
    {
        title: '4-Source Fusion',
        body: 'Scanner + HuggingFace + Graph + OTX consensus with 2-of-4 voting for maximum accuracy.',
        metric: '<100ms',
        helper: 'Detection latency'
    },
    {
        title: 'Multi-Modal Analysis',
        body: 'DistilBERT text, YOLOv5/v8 brand detection, enhanced OCR, and GNN graph intelligence.',
        metric: '99.6%',
        helper: 'Detection accuracy'
    },
    {
        title: 'Real-Time Protection',
        body: 'Chrome MV3 extension with automatic scanning and threat intelligence integration.',
        metric: '24.7ms',
        helper: 'Text analysis speed'
    }
];

const HeroIllustration = () => (
    <div className="relative h-64 w-full overflow-hidden rounded-2xl bg-slate-100 shadow-inner dark:bg-slate-900/50">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 400 300"
            role="img"
            aria-labelledby="hero-graphic"
        >
            <title id="hero-graphic">Threat clusters visualized</title>
            <defs>
                <linearGradient id="pulse" x1="0" x2="1" y1="0" y2="1">
                    <stop offset="0%" stopColor="#0ea5e9" />
                    <stop offset="100%" stopColor="#22d3ee" />
                </linearGradient>
                <filter id="glow">
                    <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                    <feMerge>
                        <feMergeNode in="coloredBlur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>
            </defs>
            {[...Array(8)].map((_, idx) => (
                <motion.circle
                    key={idx}
                    cx={50 + idx * 45}
                    cy={150 + Math.sin(idx) * 40}
                    r={4 + (idx % 3) * 2}
                    fill="url(#pulse)"
                    filter="url(#glow)"
                    initial={{ opacity: 0.3, scale: 0.8 }}
                    animate={{
                        opacity: [0.3, 0.8, 0.3],
                        scale: [0.8, 1.2, 0.8],
                        y: [0, -10, 0]
                    }}
                    transition={{
                        duration: 3 + idx * 0.5,
                        repeat: Infinity,
                        ease: "easeInOut"
                    }}
                />
            ))}
            <motion.path
                d="M40,200 Q120,100 200,170 T360,140"
                fill="none"
                stroke="url(#pulse)"
                strokeWidth="2"
                strokeLinecap="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 0.6 }}
                transition={{ duration: 2, ease: "easeOut" }}
            />
            <motion.path
                d="M40,200 Q120,100 200,170 T360,140"
                fill="none"
                stroke="url(#pulse)"
                strokeWidth="6"
                strokeLinecap="round"
                filter="url(#glow)"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 0.2 }}
                transition={{ duration: 2, ease: "easeOut" }}
            />
        </svg>

        {/* Floating shield icon */}
        <motion.div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/90 p-4 backdrop-blur-md border border-brand-500/30 shadow-2xl shadow-brand-500/20 dark:bg-slate-950/80"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
        >
            <div className="h-12 w-12 text-brand-400">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    <path d="M9 12l2 2 4-4" />
                </svg>
            </div>
        </motion.div>
    </div>
);

const Home = () => {
    const location = useLocation();

    useEffect(() => {
        if (location.hash) {
            const target = document.querySelector(location.hash);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }, [location.hash]);

    return (
    <div className="space-y-24 px-4 pb-20 pt-10 sm:px-8 lg:px-10">
        <section className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[minmax(0,1fr)_380px]">
            <div className="space-y-10">
                <ScrollFade>
                    <div className="inline-flex items-center gap-2 rounded-full border border-brand-500/20 bg-brand-500/10 px-3 py-1 text-xs font-medium uppercase tracking-widest text-brand-300 backdrop-blur-sm">
                        <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-400 opacity-75"></span>
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-500"></span>
                        </span>
                        AI/ML-Powered Protection
                    </div>

                    <h1 className="mt-6 text-5xl font-black leading-[1.1] tracking-tight text-slate-900 dark:text-white sm:text-6xl lg:text-7xl">
                        Real-time phishing<br />
                        <span className="text-gradient-brand">detection & prevention.</span>
                    </h1>

                    <p className="mt-8 max-w-2xl text-lg leading-relaxed text-slate-700 dark:text-slate-300">
                        Multi-modal AI system combining DistilBERT NLP, YOLOv5/v8 vision models, and GNN graph analysis with 4-source threat intelligence fusion. Production-ready with &lt;100ms response time and 99.6% accuracy.
                    </p>

                    <div className="mt-10 flex flex-wrap gap-4">
                        <a
                            href="/analyze"
                            className="btn-primary"
                        >
                            Launch Console
                            <svg className="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                        </a>
                        <a
                            href="https://github.com/yourusername/phishinglens"
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white/80 px-6 py-3 text-base font-semibold text-slate-900 transition-all duration-200 hover:bg-white hover:scale-105 dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
                        >
                            View Source
                        </a>
                    </div>
                </ScrollFade>

                <ScrollFade delay={0.1}>
                    <div className="grid gap-5 sm:grid-cols-3">
                        {features.map((feature, idx) => (
                            <div key={feature.title} className="glass-surface group relative overflow-hidden rounded-2xl p-5 transition-all hover:-translate-y-1 hover:shadow-2xl">
                                <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-gradient-to-br from-brand-400/20 to-purple-500/20 blur-2xl transition-all group-hover:from-brand-500/30 group-hover:to-purple-600/30"></div>
                                <p className="text-xs uppercase tracking-widest text-slate-500 dark:text-slate-400">{feature.helper}</p>
                                <p className="mt-2 text-3xl font-black text-slate-900 dark:text-white">{feature.metric}</p>
                                <p className="mt-1 text-sm font-medium text-brand-600 dark:text-brand-200">
                                    {feature.title}
                                    {idx === 0 && (
                                        <span className="group/tip relative ml-1 inline-flex align-top">
                                            <span
                                                tabIndex={0}
                                                className="cursor-help text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                                            >
                                                ⓘ
                                            </span>
                                            <span
                                                className="pointer-events-none absolute bottom-full left-1/2 mb-2 w-48 -translate-x-1/2 rounded-lg bg-white p-2 text-xs text-slate-700 opacity-0 shadow-xl ring-1 ring-slate-200 transition-all group-hover/tip:opacity-100 dark:bg-slate-900 dark:text-slate-300 dark:ring-white/10"
                                            >
                                                4-source consensus: Scanner + HF + Graph + OTX with 2-of-4 voting.
                                            </span>
                                        </span>
                                    )}
                                </p>
                            </div>
                        ))}
                    </div>
                </ScrollFade>
            </div>

            <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
                <motion.a
                    href="#analyze"
                    className="glass-surface group relative flex items-center justify-between overflow-hidden rounded-2xl p-6 text-slate-900 shadow-lg hover:shadow-2xl dark:text-white"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                >
                    <div className="absolute inset-0 bg-gradient-to-r from-brand-500/15 via-purple-500/10 to-transparent opacity-0 transition-opacity group-hover:opacity-100"></div>
                    <div className="relative">
                        <p className="text-xs uppercase tracking-[0.4em] text-brand-400 dark:text-brand-300">Live detection</p>
                        <p className="mt-1 text-xl font-bold">Analyze threat</p>
                    </div>
                    <motion.div
                        className="relative flex h-12 w-12 items-center justify-center rounded-full bg-brand-500 text-white shadow-lg shadow-brand-500/30"
                        animate={{ scale: [1, 1.1, 1] }}
                        transition={{ repeat: Infinity, duration: 2 }}
                    >
                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </motion.div>
                </motion.a>

                <div className="glass-surface rounded-2xl p-1">
                    <Globe />
                    <div className="border-t border-slate-200 p-4 text-center text-sm text-slate-600 dark:border-white/5 dark:text-slate-400">
                        <span className="mr-2 inline-block h-2 w-2 rounded-full bg-green-500"></span>
                        Live threat detection worldwide
                    </div>
                </div>
            </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[minmax(0,1fr)_360px]">
            <ScrollFade>
                <div className="relative">
                    <div className="absolute -inset-1 rounded-3xl bg-gradient-to-r from-brand-500 to-purple-600 opacity-30 blur-lg"></div>
                    <div className="relative rounded-3xl bg-slate-100 dark:bg-slate-950">
                        <AnalyzeForm compact />
                    </div>
                </div>
            </ScrollFade>

            <ScrollFade delay={0.1}>
                <div className="glass-surface h-full space-y-6 rounded-3xl p-8 shadow-xl">
                    <div>
                        <p className="text-xs uppercase tracking-[0.3em] text-brand-500 dark:text-brand-300">Intelligence Sources</p>
                        <h3 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">Threat feeds</h3>
                    </div>
                    <ul className="space-y-4">
                        {[
                            { name: 'PhishTank', desc: 'Real-time submissions' },
                            { name: 'AlienVault OTX', desc: 'Global threat intel' },
                            { name: 'MISP Platform', desc: 'Open source sharing' }
                        ].map((item) => (
                            <li key={item.name} className="flex items-start gap-3">
                                <div className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-brand-500/20 text-brand-400">
                                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                                <div>
                                    <p className="font-medium text-slate-900 dark:text-white">{item.name}</p>
                                    <p className="text-sm text-slate-600 dark:text-slate-400">{item.desc}</p>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            </ScrollFade>
        </section>

        <section id="features" className="mx-auto max-w-6xl space-y-8">
            <ScrollFade>
                <div className="text-center">
                    <p className="text-xs uppercase tracking-[0.4em] text-brand-300">AICTE Problem Statement</p>
                    <h2 className="mt-3 text-3xl font-bold text-slate-900 dark:text-white sm:text-4xl">Production-grade detection</h2>
                </div>
            </ScrollFade>

            <div className="grid gap-6 lg:grid-cols-2">
                <ScrollFade delay={0.1}>
                    <PerformanceChart />
                </ScrollFade>

                <div className="grid gap-6">
                    {[
                        { title: 'Multi-modal fusion', desc: 'Text (DistilBERT), Image (YOLOv5/v8), URL, and Graph (GNN) analysis with 4-source consensus.' },
                        { title: 'Graph analysis', desc: 'Domain relationships, WHOIS intel, SSL fingerprints, and redirection chain detection.' },
                        { title: 'Edge deployment', desc: 'Chrome MV3 extension with <50ms latency and real-time blocking capabilities.' },
                        { title: 'Continuous learning', desc: 'Automated retraining with PhishTank, OTX, and MISP feeds. Model drift detection included.' }
                    ].map((item, idx) => (
                        <ScrollFade key={item.title} delay={idx * 0.05 + 0.15}>
                            <div className="glass-surface group h-full rounded-3xl p-8 transition-all hover:shadow-2xl hover:-translate-y-1 dark:hover:bg-slate-900/60">
                                <p className="text-sm font-mono text-brand-500/50">{`0${idx + 1}`}</p>
                                <h3 className="mt-4 text-xl font-bold text-slate-900 dark:text-white group-hover:text-brand-500 dark:group-hover:text-brand-300 transition-colors">{item.title}</h3>
                                <p className="mt-3 text-base leading-relaxed text-slate-600 dark:text-slate-400">
                                    {item.desc}
                                </p>
                            </div>
                        </ScrollFade>
                    ))}
                </div>
            </div>
        </section>

        <section className="mx-auto max-w-6xl">
            <ScrollFade>
                <ComparisonTable />
            </ScrollFade>
        </section>
    </div>
    );
};

export default Home;
