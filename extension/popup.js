// PhishingLens popup logic.
const VERDICT = {
  phishing:  { color: "#f43f5e", icon: "🚨", label: "Phishing detected" },
  suspicious:{ color: "#f59e0b", icon: "⚠️", label: "Suspicious" },
  safe:      { color: "#10b981", icon: "🛡️", label: "Looks safe" },
};

const $ = (id) => document.getElementById(id);
let currentUrl = "";

async function analyze(content) {
  // Delegate to the service worker (keeps host permissions + CORS simple).
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: "analyze", content }, (resp) => {
      resolve(resp && resp.result);
    });
  });
}

function render(data) {
  $("spin").style.display = "none";
  const box = $("result");
  if (!data) {
    box.className = "result show";
    box.innerHTML = `<div class="verdict"><span class="badge">⚠️</span>
      <span class="vtext" style="color:#f59e0b">Engine unreachable</span></div>
      <div class="sub">Start the backend or set API_URL in config.js.</div>`;
    return;
  }
  const v = VERDICT[data.verdict] || VERDICT.suspicious;
  const sigs = (data.signals || []).slice(0, 4).map((s) => {
    const c = s.severity === "high" ? "#f43f5e" : s.severity === "medium" ? "#f59e0b" : "#64748b";
    return `<div class="sig"><span class="dot" style="background:${c}"></span><span>${escapeHtml(s.name)}</span></div>`;
  }).join("");
  box.className = "result show";
  box.innerHTML = `
    <div class="verdict">
      <span class="badge">${v.icon}</span>
      <span class="vtext" style="color:${v.color}">${v.label}</span>
      <span class="risk" style="color:${v.color}">${Math.round(data.risk_score)}</span>
    </div>
    <div class="sub">${escapeHtml(data.input || "")}</div>
    ${sigs ? `<div class="signals">${sigs}</div>` : ""}`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

async function scan(content) {
  if (!content) return;
  $("result").className = "result";
  $("spin").style.display = "block";
  render(await analyze(content));
}

document.addEventListener("DOMContentLoaded", async () => {
  // show current tab url
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentUrl = tab && tab.url && /^https?:/i.test(tab.url) ? tab.url : "";
    $("pageUrl").textContent = currentUrl || "This page can't be scanned.";
    $("scanPage").disabled = !currentUrl;
  } catch {
    $("pageUrl").textContent = "-";
  }

  // show the most recent context-menu scan, if any
  try {
    const { lastScan } = await chrome.storage.local.get(["lastScan"]);
    if (lastScan && lastScan.result) render(lastScan.result);
  } catch (e) {}

  $("scanPage").addEventListener("click", () => scan(currentUrl));
  $("scanText").addEventListener("click", () => scan($("text").value.trim()));
});
