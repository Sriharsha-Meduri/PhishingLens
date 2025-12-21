import { useState, useEffect } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { useTheme } from '@hooks/useTheme';

const primaryLinks = [
    { label: 'Home', to: '/' },
    { label: 'Features', to: '/#features' },
    { label: 'Documentation', to: '/documentation' },
    { label: 'About', to: '/about' },
    { label: 'Analyze', to: '/analyze' }
];

const prefetchAnalyze = () => {
    import('@pages/Analyze');
};

const prefetchAbout = () => {
    import('@pages/About');
};

const prefetchDocumentation = () => {
    import('@pages/Documentation');
};

const NavBar = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [open, setOpen] = useState(false);
    const location = useLocation();
    const { theme, toggleTheme } = useTheme();

    useEffect(() => {
        const handleScroll = () => {
            const currentY = window.scrollY;
            setIsScrolled(currentY > 50);
        };

        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    useEffect(() => {
        setOpen(false);
    }, [location]);

    const linkClasses = () => 'relative px-4 py-2 text-sm font-medium text-white';

    const highlightActive = () => false;

    return (
        <header className="fixed left-0 right-0 top-0 z-40 px-4">

            <motion.nav
                initial={false}
                animate={{
                    marginTop: isScrolled ? 12 : 24,
                    borderRadius: isScrolled ? 9999 : 0,
                    paddingLeft: isScrolled ? 24 : 0,
                    paddingRight: isScrolled ? 24 : 0,
                    backgroundColor: isScrolled ? (theme === 'light' ? 'rgba(255, 255, 255, 0.9)' : 'rgba(15, 23, 42, 0.8)') : 'rgba(15, 23, 42, 0)',
                    borderColor: isScrolled ? (theme === 'light' ? 'rgba(148, 163, 184, 0.25)' : 'rgba(255, 255, 255, 0.1)') : 'rgba(255, 255, 255, 0)',
                    borderWidth: 1,
                }}
                transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
                className={`mx-auto flex max-w-7xl items-center justify-between py-3 ${
                    isScrolled 
                        ? (theme === 'light' ? 'shadow-2xl shadow-slate-900/10 backdrop-blur-xl' : 'shadow-2xl shadow-black/50 backdrop-blur-xl')
                        : ''
                }`}
                style={{ border: '1px solid transparent' }}
                aria-label="Primary"
            >
                <motion.div
                    initial={false}
                    animate={{
                        scale: isScrolled ? 0.9 : 1,
                    }}
                    transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
                >
                    <Link to="/" className="group flex items-center gap-3" aria-label="PhishingLens home">
                        <motion.div 
                            className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-lg font-black text-white shadow-lg shadow-brand-500/20 transition-transform duration-300 group-hover:scale-105"
                            animate={{
                                boxShadow: isScrolled 
                                    ? '0 10px 15px -3px rgba(59, 130, 246, 0.3)' 
                                    : '0 10px 15px -3px rgba(59, 130, 246, 0.1)'
                            }}
                            transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
                        >
                            <span className="relative z-10 text-2xl">🛡️</span>
                        </motion.div>
                        <div className="hidden sm:block">
                            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-500 dark:text-brand-300">PhishingLens</p>
                            <p className="text-sm font-bold text-slate-900 dark:text-white">Intelligence</p>
                        </div>
                    </Link>
                </motion.div>

                <motion.div 
                    className="hidden items-center gap-1 md:flex"
                    initial={false}
                    animate={{
                        scale: isScrolled ? 1 : 1.05,
                        opacity: isScrolled ? 1 : 0.95,
                    }}
                    transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1], delay: 0.05 }}
                >
                    {primaryLinks.map(({ label, to }) =>
                        to.startsWith('/#') ? (
                            <Link
                                key={label}
                                to={to}
                                className="relative px-4 py-2 text-sm font-medium text-white"
                            >
                                {label}
                            </Link>
                        ) : (
                            <NavLink
                                key={label}
                                to={to}
                                className={linkClasses}
                                onMouseEnter={() => {
                                    if (label === 'Analyze') prefetchAnalyze();
                                    if (label === 'About') prefetchAbout();
                                    if (label === 'Documentation') prefetchDocumentation();
                                }}
                            >
                                {label}
                            </NavLink>
                        )
                    )}
                </motion.div>

                <motion.div 
                    className="hidden items-center gap-4 md:flex"
                    initial={false}
                    animate={{
                        scale: isScrolled ? 0.95 : 1,
                        opacity: isScrolled ? 1 : 0.95,
                    }}
                    transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1], delay: 0.1 }}
                >
                    <button
                        onClick={toggleTheme}
                        className="group relative flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-slate-400 transition-all hover:bg-white/10 hover:text-white dark:border-white/10 dark:bg-white/5"
                        aria-label="Toggle theme"
                    >
                        {theme === 'light' ? (
                            <svg className="h-5 w-5 transition-transform group-hover:-rotate-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                            </svg>
                        ) : (
                            <svg className="h-5 w-5 transition-transform group-hover:rotate-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        )}
                    </button>
                    <Link
                        to="/analyze"
                        className="btn-primary !py-2 !px-5 !text-sm"
                        onMouseEnter={prefetchAnalyze}
                    >
                        Launch Console
                    </Link>
                </motion.div>

                <button
                    type="button"
                    className="group relative z-50 flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 text-white transition-colors hover:bg-white/10 md:hidden"
                    aria-expanded={open}
                    aria-controls="mobile-menu"
                    onClick={() => setOpen((prev) => !prev)}
                >
                    <span className="sr-only">Toggle navigation</span>
                    <div className="flex flex-col gap-1.5">
                        <motion.span
                            animate={{ rotate: open ? 45 : 0, y: open ? 6 : 0 }}
                            className="block h-0.5 w-5 bg-white origin-center"
                        />
                        <motion.span
                            animate={{ opacity: open ? 0 : 1 }}
                            className="block h-0.5 w-5 bg-white"
                        />
                        <motion.span
                            animate={{ rotate: open ? -45 : 0, y: open ? -6 : 0 }}
                            className="block h-0.5 w-5 bg-white origin-center"
                        />
                    </div>
                </button>
            </motion.nav>

            <AnimatePresence>
                {open && (
                    <motion.div
                        id="mobile-menu"
                        initial={{ opacity: 0, scale: 0.95, y: -20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: -20 }}
                        transition={{ duration: 0.2 }}
                        className="absolute inset-x-4 top-full mt-2 overflow-hidden rounded-3xl border border-slate-200 bg-white/90 p-2 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/90 md:hidden"
                    >
                        <div className="flex flex-col gap-1 p-2">
                            {primaryLinks.map(({ label, to }) =>
                                to.startsWith('/#') ? (
                                    <a
                                        key={label}
                                        href={to.replace('/#', '#')}
                                        className="rounded-xl px-4 py-3 text-base font-medium text-slate-700 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white"
                                        onClick={() => setOpen(false)}
                                    >
                                        {label}
                                    </a>
                                ) : (
                                    <NavLink
                                        key={label}
                                        to={to}
                                        className={({ isActive }) =>
                                            `rounded-xl px-4 py-3 text-base font-medium transition-colors ${isActive ? 'bg-brand-500/10 text-brand-600 dark:text-brand-300' : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/5 dark:hover:text-white'
                                            }`
                                        }
                                        onClick={() => setOpen(false)}
                                    >
                                        {label}
                                    </NavLink>
                                )
                            )}
                            <div className="my-2 h-px bg-slate-200 dark:bg-white/5" />
                            <button
                                onClick={toggleTheme}
                                className="flex items-center justify-center gap-2 rounded-xl bg-slate-100 px-4 py-3 text-base font-medium text-slate-900 transition-colors hover:bg-slate-200 dark:bg-white/5 dark:text-white dark:hover:bg-white/10"
                            >
                                {theme === 'light' ? (
                                    <>
                                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                                        </svg>
                                        <span>Dark Mode</span>
                                    </>
                                ) : (
                                    <>
                                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                                        </svg>
                                        <span>Light Mode</span>
                                    </>
                                )}
                            </button>
                            <Link
                                to="/analyze"
                                className="btn-primary mt-2 w-full justify-center"
                                onClick={() => setOpen(false)}
                            >
                                Launch Console
                            </Link>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </header>
    );
};

export default NavBar;
