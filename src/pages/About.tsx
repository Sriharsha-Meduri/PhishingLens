import { motion } from 'framer-motion';
import ScrollFade from '@components/ScrollFade';

const techStack = [
    {
        icon: '🧠',
        title: 'DistilBERT NLP',
        description: 'Fine-tuned transformer model for phishing text detection with 99.2% accuracy on email bodies and suspicious messages.'
    },
    {
        icon: '👁️',
        title: 'YOLOv5/v8 Vision',
        description: 'Real-time brand logo detection and visual spoofing analysis with enhanced OCR pipeline.'
    },
    {
        icon: '🕸️',
        title: 'GNN Graph Analysis',
        description: 'Domain relationship mapping, WHOIS intelligence, and SSL fingerprint analysis for threat correlation.'
    },
    {
        icon: '🔄',
        title: '4-Source Fusion',
        description: 'Consensus voting across Scanner, HuggingFace, Graph, and OTX feeds with 2-of-4 agreement threshold.'
    }
];

const metrics = [
    { value: '99.6%', label: 'Detection Accuracy', sublabel: 'Multi-modal consensus' },
    { value: '<100ms', label: 'URL Analysis', sublabel: '4-source fusion' },
    { value: '24.7ms', label: 'Text Processing', sublabel: 'DistilBERT inference' },
    { value: '24/7', label: 'Protection', sublabel: 'Real-time monitoring' }
];

const YouTubeEmbed = ({ videoId }: { videoId: string }) => (
    <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
        <iframe
            className="absolute inset-0 h-full w-full rounded-2xl"
            src={`https://www.youtube.com/embed/${videoId}?rel=0`}
            title="PhishingLens Demo"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
        />
    </div>
);

const About = () => {
    return (
        <div className="space-y-24 px-4 pb-20 pt-10 sm:px-8 lg:px-10">
            {/* Hero Section */}
            <section className="mx-auto max-w-5xl text-center">
                <ScrollFade>

                    <h1 className="mt-2 text-5xl font-black leading-[1.1] tracking-tight text-slate-900 dark:text-white sm:text-6xl lg:text-7xl">
                        Defending the digital<br />
                        <span className="text-gradient-brand">frontier from phishing.</span>
                    </h1>

                    <p className="mx-auto mt-8 max-w-3xl text-lg leading-relaxed text-slate-600 dark:text-slate-300">
                        PhishingLens combines cutting-edge AI/ML models with real-time threat intelligence to detect and prevent 
                        sophisticated phishing attacks before they reach users. Built as a production-ready solution addressing 
                        the growing challenge of social engineering in cybersecurity.
                    </p>
                </ScrollFade>
            </section>

            {/* Video Section */}
            <section className="mx-auto max-w-6xl">
                <ScrollFade delay={0.1}>
                    <div className="space-y-6">
                        <div className="text-center">
                            <p className="text-xs uppercase tracking-[0.3em] text-brand-500 dark:text-brand-300">Watch Demo</p>
                            <h2 className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">See PhishingLens in Action</h2>
                        </div>

                        <div className="glass-surface relative overflow-hidden rounded-3xl p-4 shadow-2xl">
                            <div className="absolute -inset-20 bg-gradient-to-r from-brand-500/20 via-purple-500/20 to-brand-500/20 opacity-50 blur-3xl" />
                            <div className="relative">
                                <YouTubeEmbed videoId="w4bRimoG1mk" />
                            </div>
                        </div>

                        <p className="text-center text-sm text-slate-500 dark:text-slate-400">
                            Multi-modal AI detection combining text analysis, visual recognition, and threat intelligence fusion
                        </p>
                    </div>
                </ScrollFade>
            </section>

            {/* Technology Section */}
            <section className="mx-auto max-w-6xl">
                <ScrollFade>
                    <div className="mb-12 text-center">
                        <p className="text-xs uppercase tracking-[0.4em] text-brand-500 dark:text-brand-300">The Technology</p>
                        <h2 className="mt-3 text-3xl font-bold text-slate-900 dark:text-white sm:text-4xl">Multi-Modal AI Pipeline</h2>
                        <p className="mx-auto mt-4 max-w-2xl text-slate-600 dark:text-slate-300">
                            Four complementary detection systems working in harmony to achieve industry-leading accuracy
                        </p>
                    </div>
                </ScrollFade>

                <div className="grid gap-6 md:grid-cols-2">
                    {techStack.map((tech, idx) => (
                        <ScrollFade key={tech.title} delay={idx * 0.05}>
                            <div className="glass-surface group h-full rounded-3xl p-8 transition-all hover:-translate-y-1 hover:shadow-2xl dark:hover:bg-slate-900/60">
                                <div className="mb-4 text-5xl">{tech.icon}</div>
                                <h3 className="text-xl font-bold text-slate-900 transition-colors group-hover:text-brand-500 dark:text-white dark:group-hover:text-brand-300">
                                    {tech.title}
                                </h3>
                                <p className="mt-3 text-base leading-relaxed text-slate-600 dark:text-slate-400">
                                    {tech.description}
                                </p>
                            </div>
                        </ScrollFade>
                    ))}
                </div>
            </section>

            {/* Mission & Problem Section */}
            <section className="mx-auto max-w-6xl">
                <div className="grid gap-8 lg:grid-cols-2">
                    <ScrollFade>
                        <div className="glass-surface h-full rounded-3xl p-8 shadow-xl">
                            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-2xl text-white shadow-lg">
                                🎯
                            </div>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white">Our Mission</h3>
                            <p className="mt-4 leading-relaxed text-slate-600 dark:text-slate-300">
                                To democratize enterprise-grade phishing protection through open-source AI/ML technology. 
                                We believe everyone deserves real-time protection from social engineering attacks, 
                                regardless of technical expertise or budget.
                            </p>
                            <div className="mt-6 space-y-2">
                                {['Open Source', 'Privacy-First', 'Production-Ready', 'Continuously Learning'].map((item) => (
                                    <div key={item} className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                                        <div className="flex h-5 w-5 items-center justify-center rounded-full bg-brand-500/20 text-brand-500 dark:text-brand-400">
                                            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                            </svg>
                                        </div>
                                        {item}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </ScrollFade>

                    <ScrollFade delay={0.1}>
                        <div className="glass-surface h-full rounded-3xl p-8 shadow-xl">
                            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-rose-500 to-rose-700 text-2xl text-white shadow-lg">
                                ⚠️
                            </div>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-white">The Problem</h3>
                            <p className="mt-4 leading-relaxed text-slate-600 dark:text-slate-300">
                                Phishing attacks have evolved beyond simple email scams. Modern threats use AI-generated content, 
                                pixel-perfect brand spoofing, and sophisticated social engineering tactics that bypass traditional filters.
                            </p>
                            <div className="mt-6 grid grid-cols-2 gap-4">
                                <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4">
                                    <p className="text-2xl font-black text-rose-600 dark:text-rose-400">3.4B</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-400">Phishing emails daily</p>
                                </div>
                                <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4">
                                    <p className="text-2xl font-black text-rose-600 dark:text-rose-400">$10.3T</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-400">Annual cybercrime cost</p>
                                </div>
                            </div>
                        </div>
                    </ScrollFade>
                </div>
            </section>

            {/* Metrics Section */}
            <section className="mx-auto max-w-6xl">
                <ScrollFade>
                    <div className="glass-surface rounded-3xl p-8 shadow-xl md:p-12">
                        <div className="mb-8 text-center">
                            <p className="text-xs uppercase tracking-[0.3em] text-brand-500 dark:text-brand-300">Performance Metrics</p>
                            <h2 className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">Production-Grade Results</h2>
                        </div>

                        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                            {metrics.map((metric, idx) => (
                                <motion.div
                                    key={metric.label}
                                    initial={{ opacity: 0, y: 20 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.1 }}
                                    viewport={{ once: true }}
                                    className="text-center"
                                >
                                    <div className="mb-2 text-4xl font-black text-slate-900 dark:text-white lg:text-5xl">
                                        {metric.value}
                                    </div>
                                    <div className="text-sm font-semibold text-brand-600 dark:text-brand-300">{metric.label}</div>
                                    <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{metric.sublabel}</div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </ScrollFade>
            </section>

            {/* CTA Section */}
            <section className="mx-auto max-w-4xl">
                <ScrollFade>
                    <div className="glass-surface relative overflow-hidden rounded-3xl p-12 text-center shadow-2xl">
                        <div className="absolute inset-0 bg-gradient-to-r from-brand-500/10 via-purple-500/10 to-brand-500/10" />
                        <div className="relative">
                            <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Ready to test PhishingLens?</h2>
                            <p className="mx-auto mt-4 max-w-xl text-slate-600 dark:text-slate-300">
                                Try our multi-modal AI detection system or explore the open-source implementation on GitHub.
                            </p>
                            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
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
                                    className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white/80 px-6 py-3 text-base font-semibold text-slate-900 transition-all duration-200 hover:scale-105 hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
                                >
                                    <svg className="mr-2 h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                                        <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                                    </svg>
                                    View on GitHub
                                </a>
                            </div>
                        </div>
                    </div>
                </ScrollFade>
            </section>
        </div>
    );
};

export default About;
