"""
Whitelist management for benign URLs
Automatically marks known safe URLs as non-phishing
"""

import os
import re
from typing import Set, List
from urllib.parse import urlparse

class URLWhitelist:
    def __init__(self, whitelist_file: str = None):
        self.whitelist_file = whitelist_file or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            '..', 'data', 'benign_urls.txt'
        )
        self._whitelist_domains: Set[str] = set()
        self._whitelist_urls: Set[str] = set()
        self._load_whitelist()
    
    def _load_whitelist(self):
        """Load whitelist from file"""
        try:
            if os.path.exists(self.whitelist_file):
                with open(self.whitelist_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        url = line.strip()
                        if url and not url.startswith('#'):
                            self._add_to_whitelist(url)
                print(f"✅ Loaded {len(self._whitelist_domains)} domains and {len(self._whitelist_urls)} URLs from whitelist")
            else:
                print(f"⚠️ Whitelist file not found: {self.whitelist_file}")
        except Exception as e:
            print(f"❌ Error loading whitelist: {e}")
    
    def _add_to_whitelist(self, url: str):
        """Add URL to whitelist"""
        try:
            # Normalize URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Add full URL
            self._whitelist_urls.add(url.lower())
            
            # Extract domain
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Add only the exact domain. We deliberately do NOT auto-add parent
            # domains: whitelisting foo.herokuapp.com must not trust every
            # *.herokuapp.com (attacker-controllable shared hosting).
            self._whitelist_domains.add(domain)
        except Exception as e:
            print(f"⚠️ Error adding URL to whitelist: {url} - {e}")
    
    def is_whitelisted(self, url: str) -> bool:
        """Check if URL is whitelisted"""
        try:
            # Normalize URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            url_lower = url.lower()
            
            # Check exact URL match
            if url_lower in self._whitelist_urls:
                return True
            
            # Check wildcard patterns
            for whitelist_url in self._whitelist_urls:
                if '*' in whitelist_url:
                    # Convert wildcard to an anchored, escaped regex (no injection).
                    pattern = "^" + re.escape(whitelist_url).replace(r"\*", ".*") + "$"
                    if re.match(pattern, url_lower):
                        return True

            # Extract domain
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check domain match
            if domain in self._whitelist_domains:
                return True
            
            # Check subdomain match
            for whitelist_domain in self._whitelist_domains:
                if domain.endswith('.' + whitelist_domain) or domain == whitelist_domain:
                    return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error checking whitelist for URL: {url} - {e}")
            return False
    
    def get_whitelist_stats(self) -> dict:
        """Get whitelist statistics"""
        return {
            'total_domains': len(self._whitelist_domains),
            'total_urls': len(self._whitelist_urls),
            'file_path': self.whitelist_file
        }
    
    def reload_whitelist(self):
        """Reload whitelist from file"""
        self._whitelist_domains.clear()
        self._whitelist_urls.clear()
        self._load_whitelist()

# Global whitelist instance
_whitelist_instance = None

def get_whitelist() -> URLWhitelist:
    """Get global whitelist instance"""
    global _whitelist_instance
    if _whitelist_instance is None:
        _whitelist_instance = URLWhitelist()
    return _whitelist_instance

def is_url_whitelisted(url: str) -> bool:
    """Quick check if URL is whitelisted"""
    return get_whitelist().is_whitelisted(url)
