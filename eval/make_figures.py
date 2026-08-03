# -*- coding: utf-8 -*-
"""Publication figures from the measured evaluation scores (reports/paper/*.npy, *.json)."""
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score
from sklearn.isotonic import IsotonicRegression

R = Path(__file__).resolve().parents[1] / "reports" / "paper"
plt.rcParams.update({"figure.dpi": 150, "font.size": 10, "axes.grid": True, "grid.alpha": 0.3})


def _roc(ax, y, s, label):
    if len(np.unique(y)) < 2:
        return
    fpr, tpr, _ = roc_curve(y, s)
    ax.plot(fpr, tpr, label=f"{label} (AUC {roc_auc_score(y, s):.2f})")


def roc_fig():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 4.0))
    # left: text detectors (email in-domain, SMS cross-domain), calibrated prob
    for f, name in (("text_ceas08_email_scores.npy", "Email (CEAS-08, in-domain)"),
                    ("text_sms_spam_scores.npy", "SMS (cross-domain)")):
        p = R / f
        if p.exists():
            A = np.load(p); _roc(a1, A[:, 2].astype(int), A[:, 1], name)
    a1.plot([0, 1], [0, 1], "k--", alpha=0.4)
    a1.set_xlabel("False positive rate"); a1.set_ylabel("True positive rate")
    a1.set_title("Text detector (DistilBERT)"); a1.legend(loc="lower right", fontsize=8)
    # right: URL lexical vs transformer-on-URLs
    p = R / "url_scores.npy"
    if p.exists():
        A = np.load(p); y = A[:, 2].astype(int)
        _roc(a2, y, A[:, 0], "Lexical engine")
        _roc(a2, y, A[:, 1], "Transformer on URLs")
    a2.plot([0, 1], [0, 1], "k--", alpha=0.4)
    a2.set_xlabel("False positive rate"); a2.set_ylabel("True positive rate")
    a2.set_title("URL detection"); a2.legend(loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(R / "roc_both.png"); plt.close(fig)


def calib_fig():
    p = R / "text_ceas08_email_scores.npy"
    if not p.exists():
        return
    A = np.load(p); y = A[:, 2].astype(int); raw = A[:, 0]; cal = A[:, 1]
    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    for probs, name in ((raw, "raw"), (cal, "temperature-scaled")):
        edges = np.linspace(0, 1, 11); xs, ys = [], []
        for i in range(10):
            m = (probs >= edges[i]) & (probs < edges[i + 1] if i < 9 else probs <= edges[i + 1])
            if m.sum():
                xs.append(probs[m].mean()); ys.append(y[m].mean())
        ax.plot(xs, ys, "o-", label=name)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("Predicted probability"); ax.set_ylabel("Empirical fraction phishing")
    ax.set_title("Calibration (email detector)"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(R / "calibration.png"); plt.close(fig)


def ablation_fig():
    p = R / "url_eval.json"
    if not p.exists():
        return
    d = json.load(open(p))["lexical_ablation_auc_drop"]
    names = {"structure": "Structure", "keywords": "Keywords", "https": "No HTTPS",
             "brand": "Brand", "ip_at": "IP / @", "tld": "TLD"}
    items = sorted(d.items(), key=lambda kv: -kv[1])
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.bar([names.get(k, k) for k, _ in items], [v for _, v in items], color="#4C72B0")
    ax.set_ylabel("ROC-AUC drop when removed")
    ax.set_title("URL lexical signal ablation")
    fig.tight_layout(); fig.savefig(R / "url_ablation.png"); plt.close(fig)


if __name__ == "__main__":
    roc_fig(); calib_fig(); ablation_fig()
    print("figures written to", R)
