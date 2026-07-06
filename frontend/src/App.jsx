import React, { useState, useRef, useEffect } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/* ---------------- helpers ---------------- */
const VERDICT = {
  phishing:  { color: '#f43f5e', ring: 'rgba(244,63,94,0.15)', icon: '🚨', label: 'Phishing detected', tone: 'danger' },
  suspicious:{ color: '#f59e0b', ring: 'rgba(245,158,11,0.15)', icon: '⚠️', label: 'Suspicious', tone: 'warn' },
  safe:      { color: '#10b981', ring: 'rgba(16,185,129,0.15)', icon: '🛡️', label: 'Looks safe', tone: 'safe' },
};
const SEV = { high: '#f43f5e', medium: '#f59e0b', low: '#64748b' };

const EXAMPLES = [
  { label: 'Phishing email', kind: 'text',
    value: "Dear Customer, your account has been suspended due to unusual activity. Verify your identity immediately at http://secure-paypal.account-verify.xyz/login to avoid permanent closure within 24 hours." },
  { label: 'Phishing URL', kind: 'url',
    value: "http://paypal.com.account-secure.xyz/webscr?cmd=login&verify=now" },
  { label: 'Safe message', kind: 'text',
    value: "Hi team, attaching the notes from today's standup. Let's sync tomorrow at 10am to finalize the release checklist. Thanks!" },
  { label: 'Safe URL', kind: 'url', value: "https://github.com/Sriharsha-Meduri" },
];

/* ---------------- risk ring ---------------- */
function RiskRing({ score, color }) {
  const r = 52, c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="relative shrink-0" style={{ width: 132, height: 132 }}>
      <svg width="132" height="132" className="-rotate-90">
        <circle cx="66" cy="66" r={r} fill="none" stroke="#1e2b45" strokeWidth="10" />
        <circle cx="66" cy="66" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c - (pct / 100) * c}
          style={{ transition: 'stroke-dashoffset 0.9s cubic-bezier(0.22,1,0.36,1)' }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-extrabold" style={{ color }}>{Math.round(pct)}</span>
        <span className="text-[10px] uppercase tracking-widest text-slate-500">Risk</span>
      </div>
    </div>
  );
}

/* ---------------- result panel ---------------- */
function ResultPanel({ data }) {
  if (!data) return null;
  const v = VERDICT[data.verdict] || VERDICT.suspicious;
  return (
    <div className="mt-6 rounded-2xl border border-line glass overflow-hidden animate-[floaty_0s]">
      <div className="p-5 sm:p-7 flex flex-col sm:flex-row items-center gap-6"
           style={{ background: `linear-gradient(180deg, ${v.ring}, transparent)` }}>
        <RiskRing score={data.risk_score} color={v.color} />
        <div className="text-center sm:text-left flex-1">
          <div className="flex items-center gap-2 justify-center sm:justify-start">
            <span className="text-2xl">{v.icon}</span>
            <h3 className="font-display text-2xl font-bold" style={{ color: v.color }}>{v.label}</h3>
          </div>
          <p className="mt-1 text-slate-400 text-sm">
            {({ url: 'URL analysis', domain: 'Domain intelligence', image: 'Image (OCR) analysis' }[data.type]) || 'Message analysis'} ·
            confidence {(data.confidence * 100).toFixed(0)}% ·
            <span className="font-mono text-slate-500"> {data.model || 'model'}</span>
          </p>
          <div className="mt-3 inline-block max-w-full truncate rounded-lg bg-black/30 border border-line px-3 py-1.5 font-mono text-xs text-slate-400">
            {data.input}
          </div>
        </div>
      </div>

      <div className="border-t border-line p-5 sm:p-7">
        <h4 className="text-xs uppercase tracking-widest text-slate-500 mb-3">Signals</h4>
        <ul className="space-y-2">
          {(data.signals || []).map((s, i) => (
            <li key={i} className="flex items-start gap-3 text-sm">
              <span className="mt-1.5 h-2 w-2 rounded-full shrink-0" style={{ background: SEV[s.severity] || SEV.low }} />
              <span className="text-slate-300">{s.name}</span>
            </li>
          ))}
        </ul>

        {data.features && (
          <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {Object.entries(data.features).map(([k, val]) => (
              <div key={k} className="rounded-lg bg-black/20 border border-line px-3 py-2">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">{k.replace(/_/g, ' ')}</div>
                <div className="font-mono text-sm text-slate-200 truncate">{String(val)}</div>
              </div>
            ))}
          </div>
        )}

        {data.urls && data.urls.length > 0 && (
          <div className="mt-5">
            <h4 className="text-xs uppercase tracking-widest text-slate-500 mb-2">Links found ({data.urls.length})</h4>
            <div className="space-y-2">
              {data.urls.map((u, i) => {
                const uv = VERDICT[u.verdict] || VERDICT.suspicious;
                return (
                  <div key={i} className="flex items-center gap-3 rounded-lg bg-black/20 border border-line px-3 py-2">
                    <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: uv.color }} />
                    <span className="font-mono text-xs text-slate-400 truncate flex-1">{u.input}</span>
                    <span className="text-xs font-semibold shrink-0" style={{ color: uv.color }}>{u.risk_score}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------------- analyzer ---------------- */
function Analyzer() {
  const [content, setContent] = useState('');
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState('auto');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const canRun = mode === 'image' ? !!file : !!content.trim();

  const run = async () => {
    if (!canRun) return;
    setLoading(true); setErr(''); setData(null);
    try {
      let url, body;
      if (mode === 'image') {
        const b64 = await new Promise((res, rej) => {
          const r = new FileReader();
          r.onload = () => res(String(r.result).split(',')[1]);
          r.onerror = rej;
          r.readAsDataURL(file);
        });
        url = `${API}/analyze_image`; body = { image_base64: b64 };
      } else if (mode === 'domain') {
        url = `${API}/analyze_domain`; body = { domain: content.trim() };
      } else {
        url = `${API}/analyze`; body = { content: content.trim(), mode };
      }
      const res = await fetch(url, {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setErr('Could not reach the analysis engine. Please try again in a moment.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div id="analyzer" className="w-full max-w-2xl mx-auto">
      <div className="rounded-2xl border border-line glass p-5 sm:p-6 shadow-2xl shadow-black/40">
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {[['auto', 'Auto'], ['text', 'Email / SMS'], ['url', 'URL'], ['domain', 'Domain'], ['image', 'Image']].map(([m, label]) => (
            <button key={m} onClick={() => { setMode(m); setData(null); }}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition ${
                mode === m ? 'bg-brand text-ink' : 'bg-white/5 text-slate-400 hover:text-slate-200'}`}>
              {label}
            </button>
          ))}
        </div>
        {mode === 'image' ? (
          <label className="flex flex-col items-center justify-center h-32 rounded-xl bg-black/30 border border-dashed border-line cursor-pointer hover:border-brand transition text-center px-4">
            <input type="file" accept="image/*" className="hidden" onChange={(e) => setFile(e.target.files[0] || null)} />
            <span className="text-2xl mb-1">🖼️</span>
            <span className="text-sm text-slate-400">{file ? file.name : 'Upload a screenshot — login page, email, or scam SMS'}</span>
          </label>
        ) : (
          <textarea value={content} onChange={(e) => setContent(e.target.value)}
            placeholder={mode === 'domain' ? 'Enter a domain, e.g. paypal-secure-login.com' : 'Paste a suspicious email, SMS, or URL…'}
            className="w-full h-32 resize-y rounded-xl bg-black/30 border border-line px-4 py-3 text-sm text-slate-100 placeholder-slate-600 outline-none focus:border-brand transition" />
        )}
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <button onClick={run} disabled={loading || !canRun}
            className="px-5 py-2.5 rounded-xl bg-brand hover:bg-brand-deep text-ink font-bold text-sm transition disabled:opacity-40 disabled:cursor-not-allowed">
            {loading ? 'Analyzing…' : 'Analyze'}
          </button>
          {mode !== 'image' && (
            <>
              <span className="text-xs text-slate-600 mr-1">or try:</span>
              {EXAMPLES.map((ex) => (
                <button key={ex.label} onClick={() => { setContent(ex.value); setMode(ex.kind); setData(null); }}
                  className="px-2.5 py-1 rounded-full border border-line text-xs text-slate-400 hover:border-brand hover:text-brand transition">
                  {ex.label}
                </button>
              ))}
            </>
          )}
        </div>
        {err && <p className="mt-3 text-sm text-danger">{err}</p>}
      </div>
      {loading && (
        <div className="mt-6 rounded-2xl border border-line glass p-10 flex items-center justify-center">
          <div className="relative h-16 w-16">
            <div className="absolute inset-0 rounded-full border-2 border-brand/40 animate-pulseRing" />
            <div className="absolute inset-0 rounded-full border-2 border-brand/40 animate-pulseRing" style={{ animationDelay: '1s' }} />
            <div className="absolute inset-0 flex items-center justify-center text-2xl">🛡️</div>
          </div>
        </div>
      )}
      {!loading && <ResultPanel data={data} />}
    </div>
  );
}

/* ---------------- sections ---------------- */
const DETECTORS = [
  { icon: '✉️', title: 'Text & email', desc: 'A fine-tuned DistilBERT transformer reads the language of the message: urgency, credential lures, and impersonation, the way a wary human would.' },
  { icon: '🔗', title: 'URL & domain', desc: 'Lexical forensics (look-alike domains, brand tokens, suspicious TLDs, entropy) plus live DNS and WHOIS-age intelligence to catch cloaked and freshly-registered links.' },
  { icon: '🖼️', title: 'Image OCR', desc: 'Upload a screenshot of a login page or scam SMS; it reads the text, extracts any links, and runs them through the full pipeline.' },
];
const FEATURES = [
  ['⚡', 'Real-time', 'Sub-second verdicts on a single API call - fast enough for a browser extension on every page load.'],
  ['🧠', 'Multi-modal', 'Text, URLs, and embedded links analyzed together, so a clean-looking email with a poisoned link is still caught.'],
  ['🧭', 'Calibrated', 'Risk scores are probability-calibrated and thresholded from evaluation, not raw model logits.'],
  ['🔌', 'Everywhere', 'One API powering a web dashboard and a Chrome MV3 extension - same engine, same verdict.'],
  ['🛡️', 'Privacy-first', 'Stateless analysis - content is scored and discarded, never stored or used for training.'],
  ['📖', 'Open', 'Fully open-source: microservices, models, extension, and deployment configs in one repo.'],
];

function App() {
  const [scrolled, setScrolled] = useState(false);
  const [menu, setMenu] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  const nav = [['Analyzer', '#analyzer'], ['How it works', '#how'], ['Features', '#features'], ['About', '#about']];

  return (
    <div className="min-h-screen bg-ink text-slate-200">
      {/* NAV */}
      <header className={`fixed top-0 inset-x-0 z-50 transition ${scrolled ? 'glass border-b border-line' : ''}`}>
        <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between">
          <a href="#top" className="flex items-center gap-2 font-display font-extrabold text-lg">
            <span className="text-xl">🛡️</span> Phishing<span className="text-brand">Lens</span>
          </a>
          <nav className="hidden md:flex items-center gap-7 text-sm text-slate-300">
            {nav.map(([l, h]) => <a key={h} href={h} className="hover:text-brand transition">{l}</a>)}
            <a href="https://github.com/Sriharsha-Meduri/PhishingLens" target="_blank" rel="noreferrer"
               className="px-4 py-1.5 rounded-lg bg-white/5 border border-line hover:border-brand hover:text-brand transition">GitHub</a>
          </nav>
          <button className="md:hidden text-2xl" onClick={() => setMenu(!menu)}>{menu ? '✕' : '☰'}</button>
        </div>
        {menu && (
          <div className="md:hidden glass border-b border-line px-5 py-4 flex flex-col gap-3 text-sm">
            {nav.map(([l, h]) => <a key={h} href={h} onClick={() => setMenu(false)} className="py-1 hover:text-brand">{l}</a>)}
          </div>
        )}
      </header>

      {/* HERO */}
      <section id="top" className="relative grid-bg pt-32 pb-20 px-5 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 h-96 w-[42rem] rounded-full bg-brand/10 blur-3xl pointer-events-none" />
        <div className="relative max-w-3xl mx-auto text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-white/5 px-3 py-1 text-xs text-slate-400 mb-6">
            <span className="h-2 w-2 rounded-full bg-safe animate-pulse" /> Multi-modal · DistilBERT + URL forensics
          </span>
          <h1 className="hero-h1 font-display text-5xl sm:text-6xl font-extrabold tracking-tight leading-[1.05]">
            See through <span className="text-brand">phishing.</span>
          </h1>
          <p className="mt-5 text-lg text-slate-400 max-w-xl mx-auto">
            Paste an email, SMS, or link. PhishingLens returns a calibrated risk score and the exact reasons behind it - in real time.
          </p>
        </div>
        <div className="relative mt-12">
          <Analyzer />
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="max-w-6xl mx-auto px-5 py-20">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="font-display text-3xl sm:text-4xl font-bold">Three lenses, one verdict</h2>
          <p className="mt-3 text-slate-400">PhishingLens fuses independent detectors so an attack that slips past one is caught by another.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-5">
          {DETECTORS.map((d) => (
            <div key={d.title} className="rounded-2xl border border-line bg-panel p-6 hover:border-brand/50 transition">
              <div className="text-3xl mb-3">{d.icon}</div>
              <h3 className="font-display text-xl font-bold mb-2">{d.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{d.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="max-w-6xl mx-auto px-5 py-20">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="font-display text-3xl sm:text-4xl font-bold">Built to actually ship</h2>
          <p className="mt-3 text-slate-400">Not a notebook demo - a deployable API, a web app, and a browser extension.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map(([icon, title, desc]) => (
            <div key={title} className="rounded-2xl border border-line bg-panel p-5">
              <div className="text-2xl mb-2">{icon}</div>
              <h3 className="font-semibold mb-1">{title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ABOUT */}
      <section id="about" className="max-w-4xl mx-auto px-5 py-20">
        <div className="rounded-2xl border border-line bg-gradient-to-b from-panel2 to-panel p-8 sm:p-10 text-center">
          <h2 className="font-display text-3xl font-bold mb-4">About PhishingLens</h2>
          <p className="text-slate-400 leading-relaxed max-w-2xl mx-auto">
            PhishingLens is a multi-modal phishing detection system built to catch attacks across the surfaces people
            actually get hit on - email, SMS, and links. It pairs a fine-tuned DistilBERT classifier with a lexical
            URL scanner behind one explainable API, and ships as both a web app and a Chrome extension.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <a href="https://github.com/Sriharsha-Meduri/PhishingLens" target="_blank" rel="noreferrer"
               className="px-5 py-2.5 rounded-xl bg-brand hover:bg-brand-deep text-ink font-bold text-sm transition">View on GitHub</a>
            <a href="#analyzer" className="px-5 py-2.5 rounded-xl border border-line hover:border-brand hover:text-brand font-semibold text-sm transition">Try the analyzer</a>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-line">
        <div className="max-w-6xl mx-auto px-5 py-10 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
          <div className="flex items-center gap-2 font-display font-bold text-slate-300">
            <span>🛡️</span> PhishingLens
          </div>
          <p>Multi-modal AI phishing detection · Text · URL · Extension</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
