from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from backend.common.schemas import GraphCheckRequest, GraphCheckResponse, Neighbor
import networkx as nx
from typing import List, Tuple
import socket, ssl, datetime
import sys
import os

app = FastAPI(title="Graph Analysis Service", version="0.3.0")

# Ensure the project root is in PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Base graph with a few seeded risky nodes
G = nx.Graph()
known_bad = {"login-security-update.com", "paypal-verify-alert.xyz", "bank-urgent-update.top"}
for bad in known_bad:
	G.add_node(bad, type="domain", risk=0.95)


def _resolve_ips(domain: str) -> List[str]:
	try:
		addrs = sorted({ai[4][0] for ai in socket.getaddrinfo(domain, 80)})
		return addrs
	except Exception:
		return []


def _ssl_days(domain: str) -> int | None:
	try:
		ctx = ssl.create_default_context()
		with socket.create_connection((domain, 443), timeout=3) as sock:
			with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
				cert = ssock.getpeercertificate()
				exp = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
				return (exp - datetime.datetime.utcnow()).days
	except Exception:
		return None


def _augment_graph(domain: str) -> None:
	# Add domain node
	if domain not in G:
		G.add_node(domain, type="domain", risk=0.2)
	# Link to IPs
	for ip in _resolve_ips(domain):
		if ip not in G:
			G.add_node(ip, type="ip", risk=0.25)
		G.add_edge(domain, ip, rel="resolves_to", weight=1.0)
	# SSL recency as risk factor on domain
	days = _ssl_days(domain)
	if isinstance(days, int) and days < 14:
		G.nodes[domain]["risk"] = max(G.nodes[domain].get("risk", 0.2), 0.45)


def _neighbor_risk(domain: str) -> Tuple[float, List[Neighbor], List[str]]:
	if domain not in G:
		return 0.15, [], ["Domain unseen"]
	neis = list(G.neighbors(domain))
	if not neis:
		return G.nodes[domain].get("risk", 0.2), [], ["Isolated node"]
	max_r = max(G.nodes[n].get("risk", 0.2) * 0.6 for n in neis)
	neighbors = [Neighbor(domain=n, risk=float(G.nodes[n].get("risk", 0.2))) for n in neis]
	return float(max_r), neighbors, ["Risk propagated from neighbors"]


def compute_risk(domain: str) -> tuple[float, List[Neighbor], List[str]]:
	# Seeded bad list overrides
	if domain in known_bad:
		neighbors = [Neighbor(domain=n, risk=0.6) for n in G.neighbors(domain)]
		return 0.95, neighbors, ["Seeded known-bad domain"]
	# Build local neighborhood
	_augment_graph(domain)
	return _neighbor_risk(domain)


@app.post("/graph_check", response_model=GraphCheckResponse)
async def graph_check(req: GraphCheckRequest) -> GraphCheckResponse:
	risk, neighbors, reasons = compute_risk(req.domain.lower())
	return GraphCheckResponse(risk_score=float(round(risk, 3)), neighbors=neighbors[:6], reasons=reasons)


@app.get("/health")
async def health():
	return {"status": "ok", "service": "graph", "version": app.version}


@app.post("/graph_check/human", response_class=PlainTextResponse)
async def graph_check_human(req: GraphCheckRequest) -> PlainTextResponse:
	"""Human-friendly output without JSON for graph analysis."""
	res = await graph_check(req)
	confidence_pct = int(round(res.risk_score * 100))
	lines: list[str] = []
	if res.risk_score >= 0.5:
		lines.append(f"\u26a0\ufe0f  Network risk detected — Confidence: {confidence_pct}%")
		if res.reasons:
			lines.append("")
			lines.append("Why we think it's risky:")
			for reason in res.reasons[:5]:
				lines.append(f" - {reason}")
	else:
		lines.append(f"\u2705  Network context looks safe — Confidence: {confidence_pct}%")
		if res.reasons:
			lines.append("")
			lines.append("Notes:")
			for reason in res.reasons[:5]:
				lines.append(f" - {reason}")

	if res.neighbors:
		lines.append("")
		lines.append(f"Details:\n - Related nodes inspected: {len(res.neighbors)}")

	return PlainTextResponse("\n".join(lines))
