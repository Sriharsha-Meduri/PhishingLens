import argparse
import csv
import json
import math
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

import httpx


@dataclass
class UrlRecord:
    url: str
    label: int


def read_urls(path: str, label: int) -> List[UrlRecord]:
    records: List[UrlRecord] = []
    if not path or not os.path.exists(path):
        return records
    seen = set()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            u = line.strip()
            if not u:
                continue
            if u in seen:
                continue
            seen.add(u)
            records.append(UrlRecord(url=u, label=label))
    return records


def call_url_analyze(endpoint: str, url: str, timeout: float = 10.0) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(endpoint, json={"url": url})
            if r.status_code == 200:
                return r.json()
            return {"error": f"status_{r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def write_eval_scores(path: str, rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "url",
        "label",
        "risk_hf",
        "risk_scanner",
        "risk_fused",
        "url_checked",
        "fusion_mode",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fieldnames})


def compute_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, Any]:
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    accuracy = (tp + tn) / max(1, (tp + tn + fp + fn))
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    tpr = recall
    return {
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "f1": f1,
        "fpr": fpr,
        "tpr": tpr,
        "n_pos": tp + fn,
        "n_neg": tn + fp,
    }


def sweep_thresholds(scores: List[Dict[str, Any]], out_path: str) -> Dict[str, Any]:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    modes = ["hf", "scanner", "fused"]
    thresholds = [i / 200.0 for i in range(0, 201)]  # 0.00..1.00 step 0.005
    summary: Dict[str, Any] = {}
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "mode",
            "threshold",
            "precision",
            "recall",
            "accuracy",
            "f1",
            "fpr",
            "tpr",
            "n_pos",
            "n_neg",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for mode in modes:
            # Build y_true and per-threshold preds
            y_true = [int(r["label"]) for r in scores]
            risks = [float(r[f"risk_{mode}"]) for r in scores]
            best_f1 = -1.0
            best_t = None
            best_f1_metrics = None
            best_fpr_close = (None, None)  # (fpr, t)
            met_at_fpr2 = None
            for t in thresholds:
                y_pred = [1 if r >= t else 0 for r in risks]
                m = compute_metrics(y_true, y_pred)
                w.writerow({
                    "mode": mode,
                    "threshold": round(t, 3),
                    **{k: (round(m[k], 6) if isinstance(m[k], float) else m[k]) for k in ("precision","recall","accuracy","f1","fpr","tpr","n_pos","n_neg")},
                })
                # Best F1
                if m["f1"] > best_f1:
                    best_f1 = m["f1"]
                    best_t = t
                    best_f1_metrics = m
                # FPR <= 2%
                if m["fpr"] <= 0.02 and met_at_fpr2 is None:
                    met_at_fpr2 = (t, m)
                # Track closest FPR to 2% if not achievable
                if best_fpr_close[0] is None or abs(m["fpr"] - 0.02) < abs(best_fpr_close[0] - 0.02):
                    best_fpr_close = (m["fpr"], t)
            if met_at_fpr2 is not None:
                t_fpr2, m_fpr2 = met_at_fpr2
            else:
                # Fallback to closest
                t_fpr2 = best_fpr_close[1]
                # Recompute metrics at fallback
                y_pred = [1 if r >= t_fpr2 else 0 for r in risks]
                m_fpr2 = compute_metrics(y_true, y_pred)
            summary[mode] = {
                "t_fpr2": round(t_fpr2, 3) if t_fpr2 is not None else None,
                "metrics_at_t_fpr2": {k: (round(m_fpr2[k], 6) if isinstance(m_fpr2[k], float) else m_fpr2[k]) for k in m_fpr2},
                "t_best_f1": round(best_t, 3) if best_t is not None else None,
                "metrics_at_t_best_f1": {k: (round(best_f1_metrics[k], 6) if isinstance(best_f1_metrics[k], float) else best_f1_metrics[k]) for k in best_f1_metrics},
            }
    return summary


def main():
    ap = argparse.ArgumentParser(description="Evaluate URL pipeline via url_service")
    ap.add_argument("--openphish", default="data/openphish.txt")
    ap.add_argument("--benign", default="data/benign_urls.txt")
    ap.add_argument("--endpoint", default="http://localhost:8002/analyze_url")
    ap.add_argument("--outdir", default="reports/url")
    args = ap.parse_args()

    pos = read_urls(args.openphish, 1)
    neg = read_urls(args.benign, 0)
    dataset = pos + neg
    print(f"[INFO] Loaded {len(dataset)} URLs ({len(pos)} pos, {len(neg)} neg)")

    scores: List[Dict[str, Any]] = []
    for i, rec in enumerate(dataset, start=1):
        res = call_url_analyze(args.endpoint, rec.url)
        fused = res.get("fused") or {}
        scanner = res.get("scanner") or {}
        hf = res.get("hf") or {}
        row = {
            "url": rec.url,
            "label": rec.label,
            "risk_hf": float(hf.get("risk_hf", 0.0)) if isinstance(hf.get("risk_hf", 0.0), (float, int)) else 0.0,
            "risk_scanner": float(scanner.get("risk_scanner", 0.0)) if isinstance(scanner.get("risk_scanner", 0.0), (float, int)) else 0.0,
            "risk_fused": float(fused.get("risk_fused", 0.0)) if isinstance(fused.get("risk_fused", 0.0), (float, int)) else 0.0,
            "url_checked": bool(scanner.get("url_checked", False)),
            "fusion_mode": fused.get("mode"),
        }
        scores.append(row)
        if i % 50 == 0:
            print(f"[INFO] Scored {i}/{len(dataset)}")

    os.makedirs(args.outdir, exist_ok=True)
    eval_scores_path = os.path.join(args.outdir, "url_eval_scores.csv")
    write_eval_scores(eval_scores_path, scores)
    print(f"[WRITE] {eval_scores_path}")

    sweep_path = os.path.join(args.outdir, "url_threshold_sweep.csv")
    summary = sweep_thresholds(scores, sweep_path)
    print(f"[WRITE] {sweep_path}")

    select_path = os.path.join(args.outdir, "url_threshold_selection.json")
    with open(select_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[WRITE] {select_path}")

    # Console summary
    def fmt(m: Dict[str, Any]) -> str:
        return (
            f"acc={m['accuracy']:.3f} f1={m['f1']:.3f} prec={m['precision']:.3f} rec={m['recall']:.3f} "
            f"fpr={m['fpr']:.3f} tpr={m['tpr']:.3f}"
        )
    print("\n[SUMMARY]")
    for mode in ("hf", "scanner", "fused"):
        b = summary[mode]
        print(f"{mode.upper()} t_fpr2={b['t_fpr2']} -> {fmt(b['metrics_at_t_fpr2'])}")
        print(f"{mode.upper()} t_best_f1={b['t_best_f1']} -> {fmt(b['metrics_at_t_best_f1'])}")


if __name__ == "__main__":
    main()


