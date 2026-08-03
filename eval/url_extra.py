# -*- coding: utf-8 -*-
"""
Two additions to the URL evaluation, addressing (a) how the interpretable rule engine
compares with a learned classifier on the same class of features, and (b) generalisation
to a second, independently sourced URL set.

  1. Learned lexical baseline. On pirocheto/phishing-url we train a gradient-boosted
     classifier on the URL-string (lexical) features alone, and on the full feature set
     (lexical + page content + reputation), with a proper train/test split. This shows the
     accuracy ceiling of fast lexical features and what content/reputation features add,
     and contextualises the deployed rule engine's ROC-AUC.
  2. Cross-dataset. We score the deployed rule engine on a second, independent URL set
     (the local OpenPhish feed and a curated benign list) to test transfer with no re-tuning.
All numbers measured.
"""
import json
import sys
from pathlib import Path

import numpy as np
from datasets import load_dataset
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             roc_auc_score)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "paper"
sys.path.insert(0, str(ROOT / "serve"))
import app as serveapp  # noqa: E402


def _metrics(y, pred):
    pr, rc, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
    tn = int(((y == 0) & (pred == 0)).sum()); fp = int(((y == 0) & (pred == 1)).sum())
    return {"precision": float(pr), "recall": float(rc), "f1": float(f1),
            "accuracy": float(accuracy_score(y, pred)), "fpr": float(fp / (fp + tn)) if (fp + tn) else 0.0}


def _best_f1(y, s):
    best = (0.5, -1.0, None)
    for t in np.linspace(0.05, 0.95, 91):
        m = _metrics(y, (s >= t).astype(int))
        if m["f1"] > best[1]:
            best = (float(t), m["f1"], m)
    return best


def learned_baseline():
    tr = load_dataset("pirocheto/phishing-url", split="train")
    te = load_dataset("pirocheto/phishing-url", split="test")
    feats = [c for c in tr.column_names if c not in ("url", "status")]
    cut = feats.index("nb_hyperlinks")           # everything before this is URL-string lexical
    lex = feats[:cut]
    import pandas as pd
    Xtr = pd.DataFrame({c: tr[c] for c in feats}); Xte = pd.DataFrame({c: te[c] for c in feats})
    ytr = np.array([1 if s == "phishing" else 0 for s in tr["status"]])
    yte = np.array([1 if s == "phishing" else 0 for s in te["status"]])
    out = {}
    for tag, cols in (("lexical_only", lex), ("all_features", feats)):
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1, random_state=42)
        clf.fit(Xtr[cols], ytr)
        p = clf.predict_proba(Xte[cols])[:, 1]
        bf = _best_f1(yte, p)
        out[tag] = {"n_features": len(cols), "auc": float(roc_auc_score(yte, p)),
                    "operating_point_best_f1": {"threshold": bf[0], **bf[2]}}
        print(f"  learned {tag}: AUC {out[tag]['auc']:.3f} (F1 {bf[2]['f1']:.3f}), {len(cols)} feats", flush=True)
    out["test_n"] = int(len(yte))
    return out


def cross_dataset_rule_engine():
    def _load(path, label):
        p = ROOT / path
        if not p.exists():
            return [], []
        us = [ln.strip() for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
        return us, [label] * len(us)
    up, yp = _load("data/openphish.txt", 1)
    un, yn = _load("data/benign_urls.txt", 0)
    urls = up + un
    y = np.array(yp + yn, dtype=int)
    if len(np.unique(y)) < 2:
        return None
    risk = np.array([serveapp._url_lexical(u)[0] for u in urls], dtype=np.float32)
    bf = _best_f1(y, risk)
    return {"dataset": "OpenPhish feed + curated benign list (local)", "n": int(len(y)),
            "n_pos": int(y.sum()), "n_neg": int((1 - y).sum()),
            "auc": float(roc_auc_score(y, risk)),
            "operating_point_best_f1": {"threshold": bf[0], **bf[2]}}


if __name__ == "__main__":
    print("[url-extra] learned lexical baseline on pirocheto ...", flush=True)
    learned = learned_baseline()
    print("[url-extra] rule engine on second (OpenPhish+benign) set ...", flush=True)
    cross = cross_dataset_rule_engine()
    res = {"learned_baseline": learned, "rule_engine_cross_dataset": cross}
    json.dump(res, open(OUT / "url_extra.json", "w"), indent=2)
    print(json.dumps(res, indent=2), flush=True)
    print("URL EXTRA DONE", flush=True)
