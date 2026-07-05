import argparse
import csv
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any

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
            if not u or u in seen:
                continue
            seen.add(u)
            records.append(UrlRecord(url=u, label=label))
    return records


def call_v2(endpoint: str, url: str, timeout: float = 15.0) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(endpoint, json={"url": url})
            if r.status_code == 200:
                return r.json()
            return {"error": f"status_{r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


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


def main():
    ap = argparse.ArgumentParser(description="Evaluate v2 fusion endpoint (fixed K=2)")
    ap.add_argument("--openphish", default="data/openphish_100.txt")
    ap.add_argument("--benign", default="data/benign_100.txt")
    ap.add_argument("--endpoint", default="http://localhost:8002/analyze_url_v2")
    ap.add_argument("--outdir", default="reports/url")
    args = ap.parse_args()

    pos = read_urls(args.openphish, 1)
    neg = read_urls(args.benign, 0)
    dataset = pos + neg
    print(f"[INFO] Loaded {len(dataset)} URLs ({len(pos)} pos, {len(neg)} neg)")

    rows: List[Dict[str, Any]] = []
    y_true: List[int] = []
    y_pred_fused: List[int] = []
    for i, rec in enumerate(dataset, start=1):
        res = call_v2(args.endpoint, rec.url)
        if "error" in res:
            final = 0
            conf = 0.0
        else:
            final = 1 if bool(res.get("final_verdict", False)) else 0
            conf = float(res.get("confidence", 0.0))
        y_true.append(rec.label)
        y_pred_fused.append(final)
        rows.append({
            "url": rec.url,
            "label": rec.label,
            "final": final,
            "confidence": round(conf, 6),
        })
        if i % 50 == 0:
            print(f"[INFO] Scored {i}/{len(dataset)}")

    os.makedirs(args.outdir, exist_ok=True)
    per_url_path = os.path.join(args.outdir, "fusion_v2_eval_per_url.csv")
    with open(per_url_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["url", "label", "final", "confidence"])
        w.writeheader()
        w.writerows(rows)
    print(f"[WRITE] {per_url_path}")

    m = compute_metrics(y_true, y_pred_fused)
    summary_path = os.path.join(args.outdir, "fusion_v2_eval_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({k: (round(v, 6) if isinstance(v, float) else v) for k, v in m.items()}, f, indent=2)
    print(f"[WRITE] {summary_path}")

    print("\n[FUSION K=2 @ fixed thresholds]")
    print(
        f"acc={m['accuracy']:.3f} f1={m['f1']:.3f} prec={m['precision']:.3f} rec={m['recall']:.3f} fpr={m['fpr']:.3f} tpr={m['tpr']:.3f}"
    )


if __name__ == "__main__":
    main()

"""
Evaluation script for the 4-source URL fusion system (v2).
Evaluates Scanner, HF, Graph, OTX, and K=2 consensus fusion.
"""

import argparse
import csv
import json
import math
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

import httpx
import numpy as np


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


def call_fusion_v2(endpoint: str, url: str, timeout: float = 15.0) -> Dict[str, Any]:
    """Call the v2 fusion endpoint and extract individual source scores."""
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
        "risk_scanner",
        "risk_hf", 
        "risk_graph",
        "risk_otx",
        "final_verdict",
        "confidence",
        "fusion_mode",
        "sources_fired",
        "degraded_sources"
    ]
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compute_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    """Compute classification metrics."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    accuracy = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
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
        "n_neg": fp + tn
    }


def threshold_sweep(scores: List[float], labels: List[int], thresholds: List[float]) -> List[Dict[str, Any]]:
    """Perform threshold sweep and compute metrics."""
    results = []
    for threshold in thresholds:
        y_pred = [1 if score >= threshold else 0 for score in scores]
        metrics = compute_metrics(labels, y_pred)
        metrics["threshold"] = threshold
        results.append(metrics)
    return results


def find_optimal_thresholds(sweep_results: List[Dict[str, Any]]) -> Tuple[float, float]:
    """Find t_fpr2 (FPR ≤ 2%) and t_best_f1 thresholds."""
    t_fpr2 = None
    t_best_f1 = None
    best_f1 = -1
    
    for result in sweep_results:
        # Find best F1
        if result["f1"] > best_f1:
            best_f1 = result["f1"]
            t_best_f1 = result["threshold"]
        
        # Find t_fpr2 (smallest threshold with FPR ≤ 0.02)
        if result["fpr"] <= 0.02 and t_fpr2 is None:
            t_fpr2 = result["threshold"]
    
    return t_fpr2, t_best_f1


def write_threshold_sweep(path: str, mode: str, sweep_results: List[Dict[str, Any]]) -> None:
    """Write threshold sweep results to CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["mode", "threshold", "precision", "recall", "accuracy", "f1", "fpr", "tpr", "n_pos", "n_neg"]
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in sweep_results:
            row = {"mode": mode}
            row.update(result)
            writer.writerow(row)


def write_threshold_selection(path: str, results: Dict[str, Any]) -> None:
    """Write threshold selection results to JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Evaluate 4-source URL fusion system")
    parser.add_argument("--openphish", required=True, help="Path to OpenPhish URLs file")
    parser.add_argument("--benign", required=True, help="Path to benign URLs file")
    parser.add_argument("--endpoint", default="http://localhost:8002/analyze_url_v2", help="Fusion v2 endpoint")
    parser.add_argument("--outdir", default="reports/url", help="Output directory")
    parser.add_argument("--thresholds", type=int, default=201, help="Number of threshold points")
    
    args = parser.parse_args()
    
    # Load data
    print(f"[INFO] Loading URLs...")
    phishing_urls = read_urls(args.openphish, label=1)
    benign_urls = read_urls(args.benign, label=0)
    
    all_urls = phishing_urls + benign_urls
    print(f"[INFO] Loaded {len(all_urls)} URLs ({len(phishing_urls)} pos, {len(benign_urls)} neg)")
    
    # Score URLs (single pass - no duplication)
    print(f"[INFO] Scoring URLs with fusion v2...")
    eval_rows = []
    scanner_scores = []
    hf_scores = []
    graph_scores = []
    otx_scores = []
    fusion_verdicts = []
    labels = []
    
    # Cache results to avoid duplicate API calls
    url_results = {}
    
    for i, record in enumerate(all_urls):
        if i % 50 == 0:
            print(f"[INFO] Scored {i}/{len(all_urls)}")
        
        # Check if we already have results for this URL
        if record.url in url_results:
            result = url_results[record.url]
        else:
            result = call_fusion_v2(args.endpoint, record.url)
            url_results[record.url] = result
        
        if "error" in result:
            print(f"[WARN] Error for {record.url}: {result['error']}")
            # Use default values for failed requests
            scanner_score = 0.0
            hf_score = 0.0
            graph_score = 0.0
            otx_score = 0.0
            final_verdict = False
            confidence = 0.0
            sources_fired = []
            degraded_sources = []
        else:
            sources = result.get("sources", {})
            scanner_score = sources.get("scanner", {}).get("score", 0.0)
            hf_score = sources.get("hf", {}).get("score", 0.0)
            graph_score = sources.get("graph", {}).get("score", 0.0)
            otx_score = sources.get("otx", {}).get("score", 0.0)
            final_verdict = result.get("final_verdict", False)
            confidence = result.get("confidence", 0.0)
            
            # Count fired sources
            sources_fired = [k for k, v in sources.items() if v.get("fired", False)]
            degraded_sources = result.get("meta", {}).get("degraded_sources", [])
        
        eval_rows.append({
            "url": record.url,
            "label": record.label,
            "risk_scanner": scanner_score,
            "risk_hf": hf_score,
            "risk_graph": graph_score,
            "risk_otx": otx_score,
            "final_verdict": final_verdict,
            "confidence": confidence,
            "fusion_mode": "k-of-n",
            "sources_fired": ",".join(sources_fired),
            "degraded_sources": ",".join(degraded_sources)
        })
        
        scanner_scores.append(scanner_score)
        hf_scores.append(hf_score)
        graph_scores.append(graph_score)
        otx_scores.append(otx_score)
        fusion_verdicts.append(1 if final_verdict else 0)
        labels.append(record.label)
    
    # Write evaluation scores
    eval_path = os.path.join(args.outdir, "fusion_v2_eval_scores.csv")
    write_eval_scores(eval_path, eval_rows)
    print(f"[WRITE] {eval_path}")
    
    # Generate thresholds
    thresholds = np.linspace(0.00, 1.00, args.thresholds)
    
    # Threshold sweeps for individual sources
    modes = ["scanner", "hf", "graph", "otx"]
    all_scores = [scanner_scores, hf_scores, graph_scores, otx_scores]
    
    threshold_selection = {}
    sweep_path = os.path.join(args.outdir, "fusion_v2_threshold_sweep.csv")
    
    # Write header for sweep CSV
    with open(sweep_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["mode", "threshold", "precision", "recall", "accuracy", "f1", "fpr", "tpr", "n_pos", "n_neg"])
    
    for mode, scores in zip(modes, all_scores):
        print(f"[INFO] Computing threshold sweep for {mode}...")
        sweep_results = threshold_sweep(scores, labels, thresholds)
        
        # Append to sweep CSV
        with open(sweep_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for result in sweep_results:
                writer.writerow([mode, result["threshold"], result["precision"], result["recall"], 
                               result["accuracy"], result["f1"], result["fpr"], result["tpr"], 
                               result["n_pos"], result["n_neg"]])
        
        # Find optimal thresholds
        t_fpr2, t_best_f1 = find_optimal_thresholds(sweep_results)
        
        # Get metrics at optimal thresholds
        metrics_at_t_fpr2 = None
        metrics_at_t_best_f1 = None
        
        if t_fpr2 is not None:
            for result in sweep_results:
                if abs(result["threshold"] - t_fpr2) < 1e-6:
                    metrics_at_t_fpr2 = result
                    break
        
        if t_best_f1 is not None:
            for result in sweep_results:
                if abs(result["threshold"] - t_best_f1) < 1e-6:
                    metrics_at_t_best_f1 = result
                    break
        
        threshold_selection[mode] = {
            "t_fpr2": t_fpr2,
            "metrics_at_t_fpr2": metrics_at_t_fpr2,
            "t_best_f1": t_best_f1,
            "metrics_at_t_best_f1": metrics_at_t_best_f1
        }
    
    print(f"[WRITE] {sweep_path}")
    
    # Write threshold selection
    selection_path = os.path.join(args.outdir, "fusion_v2_threshold_selection.json")
    write_threshold_selection(selection_path, threshold_selection)
    print(f"[WRITE] {selection_path}")
    
    # Print summary
    print("\n[SUMMARY]")
    for mode in modes:
        t_fpr2 = threshold_selection[mode]["t_fpr2"]
        t_best_f1 = threshold_selection[mode]["t_best_f1"]
        metrics_fpr2 = threshold_selection[mode]["metrics_at_t_fpr2"]
        metrics_f1 = threshold_selection[mode]["metrics_at_t_best_f1"]
        
        if t_fpr2 is not None and metrics_fpr2:
            print(f"{mode.upper()} t_fpr2={t_fpr2:.3f} -> "
                  f"acc={metrics_fpr2['accuracy']:.3f} f1={metrics_fpr2['f1']:.3f} "
                  f"prec={metrics_fpr2['precision']:.3f} rec={metrics_fpr2['recall']:.3f} "
                  f"fpr={metrics_fpr2['fpr']:.3f} tpr={metrics_fpr2['tpr']:.3f}")
        else:
            print(f"{mode.upper()} t_fpr2=None -> FPR > 2% not achievable")
        
        if t_best_f1 is not None and metrics_f1:
            print(f"{mode.upper()} t_best_f1={t_best_f1:.3f} -> "
                  f"acc={metrics_f1['accuracy']:.3f} f1={metrics_f1['f1']:.3f} "
                  f"prec={metrics_f1['precision']:.3f} rec={metrics_f1['recall']:.3f} "
                  f"fpr={metrics_f1['fpr']:.3f} tpr={metrics_f1['tpr']:.3f}")

    # Print single fusion line (fixed rule, no sweep)
    fusion_metrics = compute_metrics(labels, fusion_verdicts)
    print(f"FUSION (fixed K=2 with Scanner requirement) -> "
          f"acc={fusion_metrics['accuracy']:.3f} f1={fusion_metrics['f1']:.3f} "
          f"prec={fusion_metrics['precision']:.3f} rec={fusion_metrics['recall']:.3f} "
          f"fpr={fusion_metrics['fpr']:.3f} tpr={fusion_metrics['tpr']:.3f}")


if __name__ == "__main__":
    main()
