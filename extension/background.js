// PhishingLens - MV3 service worker.
// Right-click a link or a text selection to scan it. Results are stored so the
// popup can show the last scan, and a notification summarizes the verdict.
importScripts("config.js");

const ICON = "icons/icon128.png";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "pl-scan",
    title: "🛡️ Scan with PhishingLens",
    contexts: ["selection", "link"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== "pl-scan") return;
  const content = (info.selectionText || info.linkUrl || "").trim();
  if (!content) return;
  const result = await analyze(content);
  await chrome.storage.local.set({ lastScan: { content, result, ts: Date.now() } });
  notify(content, result);
});

async function analyze(content) {
  try {
    const r = await fetch(`${API_URL}/analyze`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    return null;
  }
}

function notify(content, result) {
  if (!result) {
    chrome.notifications.create({
      type: "basic", iconUrl: ICON, title: "PhishingLens",
      message: "Couldn't reach the analysis engine. Is the backend running?",
    });
    return;
  }
  const title = result.is_phishing
    ? "🚨 Phishing detected"
    : result.verdict === "suspicious" ? "⚠️ Suspicious" : "✅ Looks safe";
  const reason = (result.signals && result.signals[0] && result.signals[0].name) || "";
  chrome.notifications.create({
    type: "basic", iconUrl: ICON, title,
    message: `Risk ${result.risk_score}/100 - ${reason}`.slice(0, 200),
  });
}

// Let the popup ask us to analyze arbitrary content too.
chrome.runtime.onMessage.addListener((req, _sender, sendResponse) => {
  if (req.action === "analyze") {
    analyze(req.content).then((result) => sendResponse({ result }));
    return true; // async
  }
});
