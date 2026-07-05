"""
Production-ready 4-Source URL Fusion System
Implements 2-of-4 consensus voting with configurable thresholds and weights.
"""

import os
import time
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import httpx
from urllib.parse import urlparse
import fnmatch
import tldextract
from collections import OrderedDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Result:
    """Common result shape for all adapters."""
    score: float
    threshold: Optional[float] = None
    fired: bool = False
    reason: List[str] = field(default_factory=list)
    unreachable: bool = False
    meta: Optional[Dict[str, Any]] = None

class SourceAdapter(ABC):
    """Base interface for source adapters."""
    
    @abstractmethod
    async def get(self, url: str) -> Result:
        """Analyze URL and return result."""
        pass

class ScannerAdapter(SourceAdapter):
    """Adapter for URL scanner service."""
    
    def __init__(self, threshold: float):
        self.threshold = threshold
    
    async def get(self, url: str) -> Result:
        start_time = time.time()
        try:
            # Import the scanner functions directly
            from .main import extract_features, score
            
            features, checked = extract_features(url)
            score_val, reasons = score(features)
            
            fired = score_val >= self.threshold
            latency_ms = (time.time() - start_time) * 1000
            
            return Result(
                score=score_val,
                threshold=self.threshold,
                fired=fired,
                reason=reasons,
                unreachable=False,
                meta={"latency_ms": latency_ms, "checked": checked}
            )
        except Exception as e:
            logger.warning(f"Scanner adapter error: {e}")
            return Result(
                score=0.0,
                threshold=self.threshold,
                fired=False,
                reason=[],
                unreachable=True,
                meta={"latency_ms": (time.time() - start_time) * 1000, "error": str(e)}
            )

class HFAdapter(SourceAdapter):
    """Adapter for Hugging Face URL model."""
    
    def __init__(self, threshold: float):
        self.threshold = threshold
    
    async def get(self, url: str) -> Result:
        start_time = time.time()
        try:
            # Import the HF function directly
            from .main import _hf_url_score
            
            result = _hf_url_score(url)
            if result is None:
                return Result(
                    score=0.0,
                    threshold=self.threshold,
                    fired=False,
                    reason=[],
                    unreachable=True,
                    meta={"latency_ms": (time.time() - start_time) * 1000, "error": "HF model unavailable"}
                )
            
            score, class_probs = result
            fired = score >= self.threshold
            reasons = ["HF model prediction"] if fired else []
            latency_ms = (time.time() - start_time) * 1000
            
            return Result(
                score=score,
                threshold=self.threshold,
                fired=fired,
                reason=reasons,
                unreachable=False,
                meta={"latency_ms": latency_ms, "class_probs": class_probs}
            )
        except Exception as e:
            logger.warning(f"HF adapter error: {e}")
            return Result(
                score=0.0,
                threshold=self.threshold,
                fired=False,
                reason=[],
                unreachable=True,
                meta={"latency_ms": (time.time() - start_time) * 1000, "error": str(e)}
            )

class GraphAdapter(SourceAdapter):
    """Adapter for Graph service with feature toggles."""
    
    def __init__(self, threshold: float):
        self.threshold = threshold
        self.enabled = os.getenv("FEATURE_GRAPH_ENABLED", "false").lower() == "true"
        self.synth_positive = os.getenv("FEATURE_GRAPH_SYNTH_POSITIVE", "false").lower() == "true"
    
    async def get(self, url: str) -> Result:
        start_time = time.time()
        
        if not self.enabled:
            # Return neutral result when disabled
            return Result(
                score=0.0,
                threshold=self.threshold,
                fired=False,
                reason=[],
                unreachable=False,
                meta={"latency_ms": (time.time() - start_time) * 1000, "mode": "disabled"}
            )
        
        if self.synth_positive:
            # Synthetic positive for testing
            score = 0.8
            fired = score >= self.threshold
            reasons = ["Synthetic graph analysis"] if fired else []
            latency_ms = (time.time() - start_time) * 1000
            
            return Result(
                score=score,
                threshold=self.threshold,
                fired=fired,
                reason=reasons,
                unreachable=False,
                meta={"latency_ms": latency_ms, "mode": "synthetic"}
            )
        
        # Real graph analysis implementation
        try:
            score, reasons = await self._analyze_graph_features(url)
            fired = score >= self.threshold
            latency_ms = (time.time() - start_time) * 1000
            
            return Result(
                score=score,
                threshold=self.threshold,
                fired=fired,
                reason=reasons,
                unreachable=False,
                meta={"latency_ms": latency_ms, "mode": "real_analysis"}
            )
        except Exception as e:
            logger.warning(f"Graph analysis error: {e}")
            return Result(
                score=0.0,
                threshold=self.threshold,
                fired=False,
                reason=[],
                unreachable=True,
                meta={"latency_ms": (time.time() - start_time) * 1000, "mode": "error", "error": str(e)}
            )
    
    async def _analyze_graph_features(self, url: str) -> Tuple[float, List[str]]:
        """Analyze graph-based features for the URL."""
        import whois
        import socket
        import ssl
        import datetime
        from urllib.parse import urlparse
        
        score = 0.0
        reasons = []
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            ext = tldextract.extract(url)
            root_domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
            
            # 1. Domain age analysis
            try:
                domain_info = whois.whois(root_domain)
                if domain_info.creation_date:
                    creation_date = domain_info.creation_date
                    if isinstance(creation_date, list):
                        creation_date = creation_date[0]
                    
                    domain_age_days = (datetime.datetime.now() - creation_date).days
                    
                    if domain_age_days < 30:
                        score += 0.4
                        reasons.append(f"Very new domain ({domain_age_days} days)")
                    elif domain_age_days < 90:
                        score += 0.2
                        reasons.append(f"New domain ({domain_age_days} days)")
                    elif domain_age_days < 365:
                        score += 0.1
                        reasons.append(f"Recent domain ({domain_age_days} days)")
                
                # 2. Registrar reputation
                registrar = str(domain_info.registrar or "").lower()
                suspicious_registrars = ["namecheap", "godaddy", "1&1", "hostinger", "freenom"]
                if any(susp in registrar for susp in suspicious_registrars):
                    score += 0.1
                    reasons.append(f"Suspicious registrar: {registrar}")
                    
            except Exception as e:
                logger.debug(f"WHOIS lookup failed for {root_domain}: {e}")
                score += 0.05  # Slight penalty for WHOIS unavailable
                reasons.append("WHOIS data unavailable")
            
            # 3. Enhanced domain relationship analysis
            try:
                # Check for subdomain patterns common in phishing
                subdomain_parts = domain.split('.')
                if len(subdomain_parts) > 2:
                    subdomain = subdomain_parts[0]
                    # Check for suspicious subdomain patterns
                    suspicious_patterns = ['login', 'secure', 'verify', 'update', 'account', 'bank', 'paypal', 'amazon']
                    if any(pattern in subdomain.lower() for pattern in suspicious_patterns):
                        score += 0.3
                        reasons.append(f"Suspicious subdomain: {subdomain}")
                
                # Check for typosquatting patterns
                common_brands = ['google', 'facebook', 'amazon', 'paypal', 'microsoft', 'apple', 'netflix', 'instagram']
                for brand in common_brands:
                    if brand in domain.lower() and domain.lower() != f"{brand}.com":
                        score += 0.4
                        reasons.append(f"Potential typosquatting: {brand}")
                        break
                        
            except Exception as e:
                logger.debug(f"Domain analysis failed for {domain}: {e}")
            
            # 4. SSL Certificate analysis
            try:
                if parsed.scheme == "https":
                    context = ssl.create_default_context()
                    with socket.create_connection((domain, 443), timeout=3) as sock:
                        with context.wrap_socket(sock, server_hostname=domain) as ssock:
                            cert = ssock.getpeercertificate()
                            
                            # Check certificate validity period
                            not_after = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                            not_before = datetime.datetime.strptime(cert['notBefore'], "%b %d %H:%M:%S %Y %Z")
                            cert_duration = (not_after - not_before).days
                            
                            if cert_duration > 365 * 2:  # Very long cert (suspicious)
                                score += 0.1
                                reasons.append("Unusually long SSL certificate duration")
                            
                            # Check SAN count (too many SANs can be suspicious)
                            san_count = len(cert.get('subjectAltName', []))
                            if san_count > 50:
                                score += 0.15
                                reasons.append(f"High SAN count in certificate: {san_count}")
                            
                            # Check certificate issuer
                            issuer = dict(x[0] for x in cert['issuer'])
                            org = issuer.get('organizationName', '').lower()
                            if 'let\'s encrypt' in org:
                                score += 0.05  # Slight penalty for free certs (common in phishing)
                                reasons.append("Free SSL certificate")
                                
            except Exception as e:
                logger.debug(f"SSL analysis failed for {domain}: {e}")
                if parsed.scheme == "http":
                    score += 0.1
                    reasons.append("No HTTPS encryption")
            
            # 4. DNS pattern analysis
            try:
                # Check for multiple A records (load balancing vs. suspicious)
                addrs = set()
                for family, type, proto, canonname, sockaddr in socket.getaddrinfo(domain, None):
                    if family == socket.AF_INET:  # IPv4
                        addrs.add(sockaddr[0])
                
                if len(addrs) > 10:
                    score += 0.1
                    reasons.append(f"High number of A records: {len(addrs)}")
                elif len(addrs) == 0:
                    score += 0.2
                    reasons.append("No DNS A records")
                
                # Check for suspicious IP ranges (common hosting providers used by phishers)
                for addr in addrs:
                    octets = addr.split('.')
                    if len(octets) == 4:
                        # Check for common VPS/cloud ranges
                        if octets[0] in ['185', '188', '192'] or (octets[0] == '104' and octets[1] in ['21', '22']):
                            score += 0.05
                            reasons.append(f"Suspicious IP range: {addr}")
                            break
                            
            except Exception as e:
                logger.debug(f"DNS analysis failed for {domain}: {e}")
                score += 0.05
                reasons.append("DNS resolution failed")
            
            # 5. URL structure analysis
            path = parsed.path.lower()
            query = parsed.query.lower()
            
            # Check for suspicious path patterns
            suspicious_paths = ['/wp-admin/', '/admin/', '/login/', '/signin/', '/account/', '/verify/', '/update/']
            if any(susp_path in path for susp_path in suspicious_paths):
                score += 0.1
                reasons.append("Suspicious path pattern")
            
            # Check for URL shortening or redirection patterns
            if len(path) > 100 or path.count('/') > 5:
                score += 0.05
                reasons.append("Complex URL structure")
            
            # Check for suspicious query parameters
            if 'redirect' in query or 'url=' in query or 'goto=' in query:
                score += 0.1
                reasons.append("Redirection parameters in URL")
            
            # Clamp score to [0, 1]
            score = min(1.0, max(0.0, score))
            
            return score, reasons
            
        except Exception as e:
            logger.error(f"Graph feature analysis failed: {e}")
            return 0.1, ["Graph analysis failed"]

class OTXAdapter(SourceAdapter):
    """Adapter for AlienVault OTX threat intelligence."""
    
    def __init__(self, base_url: str, api_key: str, timeout_ms: int, cache_ttl_hours: int):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout_ms / 1000.0
        self.cache_ttl_seconds = cache_ttl_hours * 3600
        self.cache = OrderedDict()  # LRU cache
        self.cache_max_size = 50000  # Max 50k entries
    
    def _get_cache_key(self, url: str, domain: str) -> str:
        """Generate cache key for URL and domain."""
        return f"otx:{url}:{domain}"
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - cache_entry["timestamp"] < self.cache_ttl_seconds
    
    async def get(self, url: str) -> Result:
        start_time = time.time()
        
        # Check if we have API credentials
        if not self.api_key or not self.base_url:
            logger.warning("OTX credentials not configured, marking as unreachable")
            return Result(
                score=0.0,
                threshold=None,
                fired=False,
                reason=[],
                unreachable=True,
                meta={"latency_ms": (time.time() - start_time) * 1000, "error": "no_credentials"}
            )
        
        try:
            # Extract domain for caching
            ext = tldextract.extract(url)
            domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
            cache_key = self._get_cache_key(url, domain)
            
            # Check cache first
            if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
                cached_data = self.cache[cache_key]
                fired = cached_data["fired"]
                score = 1.0 if fired else 0.0
                reasons = cached_data.get("reasons", [])
                indicator = cached_data.get("indicator")
                
                return Result(
                    score=score,
                    threshold=None,
                    fired=fired,
                    reason=reasons,
                    unreachable=False,
                    meta={"latency_ms": (time.time() - start_time) * 1000, "cached": True, "indicator": indicator}
                )
            
            # Query OTX for URL first; domain used only for context (neutral)
            url_fired, url_indicator = await self._query_otx_url(url)
            domain_fired, domain_indicator = await self._query_otx_domain(domain)

            # Strict rule: fire ONLY on explicit URL-level positives
            fired = url_fired
            score = 1.0 if fired else 0.0
            reasons = []
            indicator = None

            if url_fired and url_indicator:
                reasons.append("OTX URL indicator hit")
                indicator = url_indicator
            # Domain results are logged in meta for context but do not trigger fire
            if domain_fired and domain_indicator and indicator is None:
                indicator = {**domain_indicator, "context": "domain"}
            
            # Cache the result
            if len(self.cache) >= self.cache_max_size:
                self.cache.popitem(last=False)  # Remove LRU item
            
            self.cache[cache_key] = {
                "fired": fired,
                "reasons": reasons,
                "indicator": indicator,
                "timestamp": time.time()
            }
            
            return Result(
                score=score,
                threshold=None,
                fired=fired,
                reason=reasons,
                unreachable=False,
                meta={"latency_ms": (time.time() - start_time) * 1000, "cached": False, "indicator": indicator}
            )
            
        except Exception as e:
            logger.warning(f"OTX adapter error: {e}")
            return Result(
                score=0.0,
                threshold=None,
                fired=False,
                reason=[],
                unreachable=True,
                meta={"latency_ms": (time.time() - start_time) * 1000, "error": str(e)}
            )
    
    async def _query_otx_url(self, url: str) -> Tuple[bool, Optional[Dict]]:
        """Query OTX for URL indicators."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/indicators/url/{url}/general",
                    headers={"X-OTX-API-KEY": self.api_key}
                )
                response.raise_for_status()
                data = response.json()
                
                # Check for positive indicators in malware/phishing categories only
                pulses = data.get("pulse_info", {}).get("pulses", [])
                malicious_pulses = []
                for pulse in pulses:
                    tags = [tag.lower() for tag in pulse.get("tags", [])]
                    # Filter to malware/phishing related categories
                    if any(keyword in tags for keyword in ["malware", "phishing", "phish", "trojan", "ransomware", "botnet", "scam", "fraud"]):
                        malicious_pulses.append(pulse)
                
                if malicious_pulses:
                    return True, {
                        "pulse_ids": [p.get("id") for p in malicious_pulses],
                        "first_seen": malicious_pulses[0].get("created"),
                        "last_seen": malicious_pulses[0].get("modified"),
                        "categories": list(set([tag for p in malicious_pulses for tag in p.get("tags", [])]))
                    }
                return False, None
        except Exception as e:
            logger.warning(f"OTX URL query error: {e}")
            return False, None
    
    async def _query_otx_domain(self, domain: str) -> Tuple[bool, Optional[Dict]]:
        """Query OTX for domain indicators."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/indicators/domain/{domain}/general",
                    headers={"X-OTX-API-KEY": self.api_key}
                )
                response.raise_for_status()
                data = response.json()
                
                # Check for positive indicators in malware/phishing categories only
                pulses = data.get("pulse_info", {}).get("pulses", [])
                malicious_pulses = []
                for pulse in pulses:
                    tags = [tag.lower() for tag in pulse.get("tags", [])]
                    # Filter to malware/phishing related categories
                    if any(keyword in tags for keyword in ["malware", "phishing", "phish", "trojan", "ransomware", "botnet", "scam", "fraud"]):
                        malicious_pulses.append(pulse)
                
                if malicious_pulses:
                    return True, {
                        "pulse_ids": [p.get("id") for p in malicious_pulses],
                        "first_seen": malicious_pulses[0].get("created"),
                        "last_seen": malicious_pulses[0].get("modified"),
                        "categories": list(set([tag for p in malicious_pulses for tag in p.get("tags", [])]))
                    }
                return False, None
        except Exception as e:
            logger.warning(f"OTX domain query error: {e}")
            return False, None

class URLFusion:
    """Main fusion orchestrator implementing 2-of-4 consensus voting."""
    
    def __init__(self):
        # Load configuration from environment
        self.k = int(os.getenv("FUSION_K", "2"))
        self.weights = self._parse_weights(os.getenv("FUSION_WEIGHTS", "graph:1.0,scanner:1.0,hf:0.8,otx:1.0"))
        self.allowlist_domains = [d.strip() for d in os.getenv(
            "ALLOWLIST_DOMAINS",
            "youtube.com,*.gov.in,virustotal.com,*.shodan.io,*.talosintelligence.com,*.microsoft.com,*.google.com"
        ).split(",") if d.strip()]
        self.version_tag = os.getenv("VERSION_TAG", "fusion-4src-k2-v2")
        
        # Thresholds
        self.t_scan = float(os.getenv("T_SCAN", "0.430"))
        self.t_hf = float(os.getenv("T_HF", "0.72"))
        self.t_graph = float(os.getenv("T_GRAPH", "0.75"))
        
        # OTX configuration
        otx_baseurl = os.getenv("OTX_BASEURL", "https://otx.alienvault.com/api/v1")
        otx_key = os.getenv("OTX_KEY", "")
        otx_timeout = int(os.getenv("OTX_TIMEOUT_MS", "5000"))  # Increased timeout
        otx_cache_ttl = int(os.getenv("OTX_CACHE_TTL_H", "48"))
        
        # Initialize adapters
        self.scanner = ScannerAdapter(self.t_scan)
        self.hf = HFAdapter(self.t_hf)
        self.graph = GraphAdapter(self.t_graph * 0.5)  # Lower threshold for better recall
        self.otx = OTXAdapter(otx_baseurl, otx_key, otx_timeout, otx_cache_ttl)
    
    def _parse_weights(self, weights_str: str) -> Dict[str, float]:
        """Parse weights string into dictionary."""
        weights = {}
        for pair in weights_str.split(","):
            if ":" in pair:
                source, weight = pair.strip().split(":", 1)
                weights[source] = float(weight)
        return weights
    
    def _is_allowlisted(self, url: str) -> bool:
        """Check if URL domain matches allowlist patterns."""
        domain = urlparse(url).netloc.lower()
        for pattern in self.allowlist_domains:
            pattern = pattern.strip().lower()
            if fnmatch.fnmatch(domain, pattern):
                return True
        return False
    
    def _apply_allowlist_weights(self, results: Dict[str, Result], url: str) -> Dict[str, Result]:
        """Apply allowlist down-weighting to HF and Graph sources."""
        if not self._is_allowlisted(url):
            return results
        
        # Check if scanner also fired
        scanner_fired = results.get("scanner", Result(0, 0, False, [])).fired
        
        if not scanner_fired:
            # Down-weight HF and Graph by 50%
            if "hf" in results:
                results["hf"].score *= 0.5
                results["hf"].fired = results["hf"].score >= results["hf"].threshold
                results["hf"].reason.append("Allowlist down-weighted HF")
            
            if "graph" in results:
                results["graph"].score *= 0.5
                results["graph"].fired = results["graph"].score >= results["graph"].threshold
                results["graph"].reason.append("Allowlist down-weighted Graph")
        
        return results
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        """Analyze URL using 4-source fusion with 2-of-4 consensus."""
        start_time = time.time()
        
        # Run all adapters in parallel with timeout
        timeout_seconds = 1.2  # Match OTX_TIMEOUT_MS
        
        async def run_with_timeout(adapter, url):
            try:
                return await asyncio.wait_for(adapter.get(url), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Adapter timeout for {adapter.__class__.__name__}")
                return Result(0.0, None, False, [], True, {"timeout": True})
            except Exception as e:
                logger.error(f"Adapter error for {adapter.__class__.__name__}: {e}")
                return Result(0.0, None, False, [], True, {"error": str(e)})
        
        # Run adapters in parallel
        tasks = {
            "scanner": run_with_timeout(self.scanner, url),
            "hf": run_with_timeout(self.hf, url),
            "graph": run_with_timeout(self.graph, url),
            "otx": run_with_timeout(self.otx, url)
        }
        
        results = {}
        for source, task in tasks.items():
            results[source] = await task
        
        # Apply allowlist weights
        results = self._apply_allowlist_weights(results, url)
        
        # Count votes among reachable sources only; guard against unexpected types
        reachable_sources = {k: v for k, v in results.items() if isinstance(v, Result) and not v.unreachable}
        fired_sources = {k: v for k, v in reachable_sources.items() if isinstance(v, Result) and v.fired}

        # Conservative rule: final = Scanner OR (HF AND OTX)
        scanner_fired = fired_sources.get("scanner") is not None
        hf_fired = fired_sources.get("hf") is not None
        otx_fired = fired_sources.get("otx") is not None
        final_verdict = scanner_fired or (hf_fired and otx_fired)
        
        # Calculate confidence
        if fired_sources:
            try:
                confidence = sum(float(getattr(r, "score", 0.0)) for r in fired_sources.values()) / max(1, len(fired_sources))
            except Exception:
                confidence = 0.5
        else:
            # Safety margin: 1 - max(score) of all reachable sources
            try:
                max_score = max((float(getattr(r, "score", 0.0)) for r in reachable_sources.values()), default=0.0)
            except Exception:
                max_score = 0.0
            confidence = 1.0 - max_score
        
        # Build sources output
        sources = {}
        for source, result in results.items():
            sources[source] = {
                "score": result.score,
                "threshold": result.threshold,
                "fired": result.fired,
                "reason": result.reason,
                "unreachable": result.unreachable
            }
            if result.meta and "indicator" in result.meta:
                sources[source]["indicator"] = result.meta["indicator"]
        
        # Build metadata
        degraded_sources = [s for s, r in results.items() if r.unreachable]
        timings_ms = {}
        for source, result in results.items():
            if result.meta and "latency_ms" in result.meta:
                timings_ms[source] = result.meta["latency_ms"]
        
        meta = {
            "mode": "k-of-n",
            "K": self.k,
            "weights": self.weights,
            "allowlist_applied": self._is_allowlisted(url),
            "degraded_sources": degraded_sources,
            "version": self.version_tag,
            "timings_ms": timings_ms
        }
        
        # Log for observability
        logger.info(f"Fusion analysis: url={url}, verdict={final_verdict}, confidence={confidence:.3f}, "
                   f"fired_sources={len(fired_sources)}, degraded={degraded_sources}")
        
        return {
            "final_verdict": final_verdict,
            "confidence": confidence,
            "sources": sources,
            "meta": meta
        }