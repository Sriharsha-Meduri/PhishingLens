import { lazy, Suspense, useEffect, useState } from 'react';
import { Route, Routes } from 'react-router-dom';
import NavBar from '@components/NavBar';
import Home from '@pages/Home';
import Documentation from '@pages/Documentation';
import { useTheme } from '@hooks/useTheme';

const Analyze = lazy(() => import('@pages/Analyze'));
const About = lazy(() => import('@pages/About'));

const LoadingFallback = () => (
  <div className="flex min-h-[40vh] items-center justify-center text-sm text-slate-400">
    Loading AI models…
  </div>
);

const FloatingCTA = () => {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setCollapsed(window.scrollY > 140);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <a
      href="#analyze"
      className={`fixed bottom-6 right-6 z-40 transition-all duration-300 ${
        collapsed ? 'scale-90 opacity-85' : 'scale-100'
      }`}
      aria-label="Jump to analyze tools"
    >
      <div className="group rounded-full border border-white/20 bg-gradient-to-r from-brand-600 to-brand-500 px-6 py-3 text-sm font-semibold text-white shadow-2xl shadow-brand-900/40 transition-all duration-300 hover:scale-105 hover:shadow-brand-700/60">
        Detect Phishing
        <span className="ml-2 inline-flex h-6 w-6 items-center justify-center rounded-full border border-white/30 text-xs transition-all duration-300 group-hover:w-8">
          →
        </span>
      </div>
    </a>
  );
};

const AppShell = () => {
  const { theme } = useTheme();
  const shellClasses = theme === 'dark' ? 'bg-slate-950 text-slate-50' : 'bg-slate-50 text-slate-900';

  return (
    <div className={`min-h-screen ${shellClasses}`}>
      <a
        href="#main"
        className="absolute left-4 top-4 z-50 -translate-y-20 rounded bg-brand-600 px-4 py-2 text-sm font-semibold text-white focus-visible:translate-y-0"
      >
        Skip to content
      </a>
      <NavBar />
      <main id="main" className="pt-24">
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/documentation" element={<Documentation />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </Suspense>
      </main>
      <FloatingCTA />
    </div>
  );
};

function App() {
  return <AppShell />;
}

export default App;
