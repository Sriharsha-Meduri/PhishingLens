"""
Heuristic visual phishing checks without custom training.
Detects form-like layouts, color mismatches, warning overlays, and compression artifacts.
"""

import os
import logging
from typing import List, Dict, Tuple
import numpy as np
from PIL import Image
import cv2
import re

# Feature flag
FEATURE_VISUAL_CHECKS = os.getenv("FEATURE_VISUAL_CHECKS", "false").lower() == "true"

logger = logging.getLogger(__name__)

# Known brand color palettes (HSV ranges)
BRAND_COLORS = {
    "apple": [(0, 0, 0), (360, 100, 100)],  # Black to white (minimalist)
    "microsoft": [(200, 100, 100), (220, 100, 100)],  # Blue
    "google": [(0, 100, 100), (60, 100, 100), (120, 100, 100), (240, 100, 100)],  # RGB
    "amazon": [(30, 100, 100), (40, 100, 100)],  # Orange
    "paypal": [(200, 100, 100), (220, 100, 100)],  # Blue
    "meta": [(200, 100, 100), (220, 100, 100)],  # Blue
    "netflix": [(0, 100, 100), (10, 100, 100)],  # Red
    "adobe": [(0, 100, 100), (10, 100, 100)],  # Red
    "spotify": [(120, 100, 100), (140, 100, 100)],  # Green
    "uber": [(0, 0, 0), (10, 100, 100)],  # Black to red
}

# Warning phrases commonly used in phishing
WARNING_PHRASES = [
    r"verify\s+your\s+account",
    r"security\s+alert",
    r"update\s+payment",
    r"account\s+suspended",
    r"urgent\s+action\s+required",
    r"confirm\s+your\s+identity",
    r"verify\s+your\s+email",
    r"update\s+your\s+information",
    r"security\s+breach",
    r"immediate\s+attention",
    r"click\s+here\s+to\s+verify",
    r"confirm\s+now",
    r"act\s+fast",
    r"limited\s+time",
    r"expires\s+soon"
]

class VisualChecker:
    """Heuristic visual phishing detection."""
    
    def __init__(self):
        self.enabled = FEATURE_VISUAL_CHECKS
    
    def check_visual_indicators(self, image: Image.Image, detected_brands: List[str] = None, ocr_text: str = "") -> Dict:
        """
        Perform heuristic visual phishing checks.
        
        Args:
            image: PIL Image to analyze
            detected_brands: List of detected brands
            ocr_text: OCR extracted text
            
        Returns:
            Dict with visual_score, reasons, and detailed breakdown
        """
        if not self.enabled:
            return {
                "visual_score": 0.0,
                "reasons": [],
                "breakdown": {}
            }
        
        try:
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            visual_score = 0.0
            reasons = []
            breakdown = {}
            
            # 1. Form-like layout detection
            form_score, form_reasons = self._detect_form_layout(img_array, gray)
            visual_score += form_score
            if form_reasons:
                reasons.extend(form_reasons)
            breakdown["form_layout"] = form_score
            
            # 2. Color mismatch detection
            color_score, color_reasons = self._detect_color_mismatch(img_array, detected_brands or [])
            visual_score += color_score
            if color_reasons:
                reasons.extend(color_reasons)
            breakdown["color_mismatch"] = color_score
            
            # 3. Warning overlay detection
            warning_score, warning_reasons = self._detect_warning_overlays(ocr_text)
            visual_score += warning_score
            if warning_reasons:
                reasons.extend(warning_reasons)
            breakdown["warning_overlays"] = warning_score
            
            # 4. Compression artifacts detection
            compression_score, compression_reasons = self._detect_compression_artifacts(img_array, gray)
            visual_score += compression_score
            if compression_reasons:
                reasons.extend(compression_reasons)
            breakdown["compression_artifacts"] = compression_score
            
            # Cap visual score at 1.0
            visual_score = min(1.0, visual_score)
            
            return {
                "visual_score": round(visual_score, 3),
                "reasons": reasons,
                "breakdown": breakdown
            }
            
        except Exception as e:
            logger.error(f"Visual checks failed: {e}")
            return {
                "visual_score": 0.0,
                "reasons": [f"Visual analysis failed: {str(e)}"],
                "breakdown": {}
            }
    
    def _detect_form_layout(self, img_array: np.ndarray, gray: np.ndarray) -> Tuple[float, List[str]]:
        """Detect form-like layout with text fields and buttons."""
        score = 0.0
        reasons = []
        
        try:
            # Detect text fields using contour detection
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter for rectangular contours (potential form fields)
            rectangular_contours = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h if h > 0 else 0
                    if 2 < aspect_ratio < 10:  # Text field-like aspect ratio
                        rectangular_contours.append((x, y, w, h))
            
            # Count potential form fields
            form_fields = len(rectangular_contours)
            if form_fields >= 2:
                score += 0.2
                reasons.append(f"Form-like layout detected ({form_fields} text fields)")
            
            # Detect buttons (look for filled rectangles)
            button_contours = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if 500 < area < 5000:  # Button size range
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h if h > 0 else 0
                    if 1.5 < aspect_ratio < 5:  # Button-like aspect ratio
                        button_contours.append((x, y, w, h))
            
            if button_contours:
                score += 0.1
                reasons.append(f"Button-like elements detected ({len(button_contours)} buttons)")
            
        except Exception as e:
            logger.warning(f"Form layout detection failed: {e}")
        
        return score, reasons
    
    def _detect_color_mismatch(self, img_array: np.ndarray, detected_brands: List[str]) -> Tuple[float, List[str]]:
        """Detect color palette mismatches with detected brands."""
        score = 0.0
        reasons = []
        
        if not detected_brands:
            return score, reasons
        
        try:
            # Convert to HSV for better color analysis
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            
            # Get dominant colors
            pixels = hsv.reshape(-1, 3)
            
            # Sample colors (to avoid processing all pixels)
            sample_size = min(1000, len(pixels))
            sample_indices = np.random.choice(len(pixels), sample_size, replace=False)
            sample_colors = pixels[sample_indices]
            
            # Check for brand color mismatches
            for brand in detected_brands:
                brand_lower = brand.lower()
                if brand_lower in BRAND_COLORS:
                    expected_colors = BRAND_COLORS[brand_lower]
                    
                    # Calculate color distance
                    color_distance = self._calculate_color_distance(sample_colors, expected_colors)
                    
                    if color_distance > 0.3:  # Significant color mismatch
                        score += 0.1
                        reasons.append(f"Color mismatch with {brand} brand palette")
            
        except Exception as e:
            logger.warning(f"Color mismatch detection failed: {e}")
        
        return score, reasons
    
    def _calculate_color_distance(self, sample_colors: np.ndarray, expected_colors: List[Tuple]) -> float:
        """Calculate color distance between sample and expected colors."""
        try:
            # Convert expected colors to numpy array
            expected_array = np.array(expected_colors)
            
            # Calculate minimum distance for each sample color
            distances = []
            for sample_color in sample_colors:
                min_dist = float('inf')
                for expected_color in expected_array:
                    # Euclidean distance in HSV space
                    dist = np.sqrt(np.sum((sample_color - expected_color) ** 2))
                    min_dist = min(min_dist, dist)
                distances.append(min_dist)
            
            # Return average distance
            return np.mean(distances) / 255.0  # Normalize
            
        except Exception:
            return 0.0
    
    def _detect_warning_overlays(self, ocr_text: str) -> Tuple[float, List[str]]:
        """Detect warning phrases in OCR text."""
        score = 0.0
        reasons = []
        
        if not ocr_text:
            return score, reasons
        
        text_lower = ocr_text.lower()
        warning_count = 0
        
        for phrase_pattern in WARNING_PHRASES:
            if re.search(phrase_pattern, text_lower):
                warning_count += 1
                reasons.append(f"Warning phrase detected: {phrase_pattern}")
        
        if warning_count > 0:
            score += min(0.2, warning_count * 0.1)  # Cap at 0.2
        
        return score, reasons
    
    def _detect_compression_artifacts(self, img_array: np.ndarray, gray: np.ndarray) -> Tuple[float, List[str]]:
        """Detect compression artifacts that might indicate low-quality phishing images."""
        score = 0.0
        reasons = []
        
        try:
            # Detect blur (high frequency content)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < 100:  # Low variance indicates blur
                score += 0.05
                reasons.append("Blurry image detected")
            
            # Detect blockiness (JPEG compression artifacts)
            # Look for 8x8 block patterns
            h, w = gray.shape
            block_artifacts = 0
            
            for i in range(0, h-8, 8):
                for j in range(0, w-8, 8):
                    block = gray[i:i+8, j:j+8]
                    if block.shape == (8, 8):
                        # Check for uniform blocks (compression artifact)
                        block_std = np.std(block)
                        if block_std < 10:  # Very uniform block
                            block_artifacts += 1
            
            if block_artifacts > (h * w) / (8 * 8) * 0.1:  # More than 10% uniform blocks
                score += 0.05
                reasons.append("Compression artifacts detected")
            
        except Exception as e:
            logger.warning(f"Compression artifact detection failed: {e}")
        
        return score, reasons

# Global instance
visual_checker = VisualChecker()
