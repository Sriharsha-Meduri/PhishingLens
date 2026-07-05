"""
URL extraction module using OCR.
Extracts URLs from images and validates domains.
"""

import os
import re
import logging
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse
import tldextract
from PIL import Image

# Feature flag
FEATURE_URL_EXTRACTION = os.getenv("FEATURE_URL_EXTRACTION", "false").lower() == "true"
OCR_ENGINE = os.getenv("OCR_ENGINE", "tesseract")

logger = logging.getLogger(__name__)

class URLExtractor:
    """URL extraction using OCR."""
    
    def __init__(self):
        self.enabled = FEATURE_URL_EXTRACTION
        self.ocr_engine = OCR_ENGINE
        self._setup_ocr()
    
    def _setup_ocr(self):
        """Setup OCR engine."""
        self.ocr_available = False
        self.ocr_error = None
        
        if not self.enabled:
            return
        
        try:
            if self.ocr_engine == "tesseract":
                import pytesseract
                self.ocr_available = True
                logger.info("Tesseract OCR available")
            elif self.ocr_engine == "easyocr":
                import easyocr
                self.reader = easyocr.Reader(['en'])
                self.ocr_available = True
                logger.info("EasyOCR available")
            elif self.ocr_engine == "paddleocr":
                from paddleocr import PaddleOCR
                self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
                self.ocr_available = True
                logger.info("PaddleOCR available")
        except ImportError as e:
            self.ocr_error = str(e)
            logger.warning(f"OCR engine {self.ocr_engine} not available: {e}")
        except Exception as e:
            self.ocr_error = str(e)
            logger.error(f"OCR setup failed: {e}")
    
    def extract_urls(self, image: Image.Image, text_regions: List[Tuple[int, int, int, int]] = None) -> Dict:
        """
        Extract URLs from image using OCR.
        
        Args:
            image: PIL Image to analyze
            text_regions: Optional list of text regions to focus on
            
        Returns:
            Dict with extracted URLs and metadata
        """
        if not self.enabled or not self.ocr_available:
            return {
                "urls": [],
                "ocr_text": "",
                "confidence_scores": [],
                "error": self.ocr_error or "OCR not available"
            }
        
        try:
            # Extract text from full image
            full_text = self._extract_text_from_image(image)
            
            # Extract text from text regions if provided
            region_texts = []
            if text_regions:
                for x, y, w, h in text_regions:
                    try:
                        # Crop region
                        region = image.crop((x, y, x + w, y + h))
                        region_text = self._extract_text_from_image(region)
                        if region_text.strip():
                            region_texts.append(region_text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from region {x, y, w, h}: {e}")
                        continue
            
            # Combine all text
            all_text = full_text
            if region_texts:
                all_text += "\n" + "\n".join(region_texts)
            
            # Extract URLs from text
            urls = self._extract_urls_from_text(all_text)
            
            # Validate and deduplicate URLs
            validated_urls = self._validate_urls(urls)
            
            # Get confidence scores
            confidence_scores = self._get_confidence_scores(validated_urls, all_text)
            
            return {
                "urls": validated_urls,
                "ocr_text": all_text,
                "confidence_scores": confidence_scores,
                "text_regions_processed": len(region_texts) if text_regions else 0
            }
            
        except Exception as e:
            logger.error(f"URL extraction failed: {e}")
            return {
                "urls": [],
                "ocr_text": "",
                "confidence_scores": [],
                "error": str(e)
            }
    
    def _extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from image using configured OCR engine."""
        try:
            if self.ocr_engine == "tesseract":
                return self._extract_text_tesseract(image)
            elif self.ocr_engine == "easyocr":
                return self._extract_text_easyocr(image)
            elif self.ocr_engine == "paddleocr":
                return self._extract_text_paddleocr(image)
            else:
                return ""
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""
    
    def _extract_text_tesseract(self, image: Image.Image) -> str:
        """Extract text using Tesseract."""
        import pytesseract
        
        # Configure tesseract for better text extraction
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)
        return (text or "").strip()
    
    def _extract_text_easyocr(self, image: Image.Image) -> str:
        """Extract text using EasyOCR."""
        import numpy as np
        
        img_array = np.array(image)
        results = self.reader.readtext(img_array)
        
        # Combine all detected text
        text_parts = []
        for (bbox, text, confidence) in results:
            if confidence > 0.5:  # Only include high-confidence text
                text_parts.append(text)
        
        return " ".join(text_parts)
    
    def _extract_text_paddleocr(self, image: Image.Image) -> str:
        """Extract text using PaddleOCR."""
        import numpy as np
        
        img_array = np.array(image)
        results = self.ocr.ocr(img_array, cls=True)
        
        # Combine all detected text
        text_parts = []
        if results and results[0]:
            for line in results[0]:
                if line and len(line) >= 2:
                    text = line[1][0]
                    confidence = line[1][1]
                    if confidence > 0.5:  # Only include high-confidence text
                        text_parts.append(text)
        
        return " ".join(text_parts)
    
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text using regex patterns."""
        if not text:
            return []
        
        urls = []
        
        # Pattern for URLs with protocol
        url_pattern_with_protocol = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls.extend(re.findall(url_pattern_with_protocol, text, re.IGNORECASE))
        
        # Pattern for URLs without protocol (domain.tld/path)
        url_pattern_without_protocol = r'(?:www\.)?[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?'
        urls_without_protocol = re.findall(url_pattern_without_protocol, text, re.IGNORECASE)
        
        # Add https:// prefix to URLs without protocol
        for url in urls_without_protocol:
            if not url.startswith(('http://', 'https://')):
                urls.append(f"https://{url}")
        
        return urls
    
    def _validate_urls(self, urls: List[str]) -> List[str]:
        """Validate and deduplicate URLs."""
        validated_urls = []
        seen_domains = set()
        
        for url in urls:
            try:
                # Parse URL
                parsed = urlparse(url)
                if not parsed.netloc:
                    continue
                
                # Extract domain
                domain = parsed.netloc.lower()
                
                # Skip if domain already seen
                if domain in seen_domains:
                    continue
                
                # Basic validation
                if self._is_valid_domain(domain):
                    validated_urls.append(url)
                    seen_domains.add(domain)
                
            except Exception as e:
                logger.warning(f"Invalid URL {url}: {e}")
                continue
        
        # Sort by length (longer URLs are often more specific)
        validated_urls.sort(key=len, reverse=True)
        
        # Return top 3 URLs
        return validated_urls[:3]
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Check if domain is valid."""
        try:
            # Extract TLD
            extracted = tldextract.extract(domain)
            
            # Must have domain and TLD
            if not extracted.domain or not extracted.suffix:
                return False
            
            # TLD must be at least 2 characters
            if len(extracted.suffix) < 2:
                return False
            
            # Domain must be at least 2 characters
            if len(extracted.domain) < 2:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _get_confidence_scores(self, urls: List[str], text: str) -> List[float]:
        """Get confidence scores for extracted URLs."""
        confidence_scores = []
        
        for url in urls:
            try:
                # Base confidence on URL length and structure
                confidence = 0.5
                
                # Longer URLs are often more specific
                if len(url) > 20:
                    confidence += 0.2
                
                # URLs with paths are more specific
                if '/' in url.split('://', 1)[-1]:
                    confidence += 0.1
                
                # URLs with subdomains are more specific
                domain = urlparse(url).netloc
                if domain.count('.') > 1:
                    confidence += 0.1
                
                # Check if URL appears in text multiple times (higher confidence)
                url_count = text.lower().count(url.lower())
                if url_count > 1:
                    confidence += min(0.2, url_count * 0.1)
                
                confidence_scores.append(min(1.0, confidence))
                
            except Exception:
                confidence_scores.append(0.5)
        
        return confidence_scores

# Global instance
url_extractor = URLExtractor()
