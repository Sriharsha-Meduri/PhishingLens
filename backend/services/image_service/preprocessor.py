"""
Image preprocessing module for OCR optimization.
Handles denoising, upscaling, grayscale conversion, and text region detection.
"""

import os
import logging
from typing import List, Tuple, Optional, Dict
import numpy as np
from PIL import Image
import cv2

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """Image preprocessing for OCR optimization."""
    
    def __init__(self):
        self.min_image_size = (100, 100)
        self.max_image_size = (2000, 2000)
    
    def preprocess_for_ocr(self, image: Image.Image) -> Dict:
        """
        Preprocess image for optimal OCR performance.
        
        Args:
            image: PIL Image to preprocess
            
        Returns:
            Dict with preprocessed image and metadata
        """
        try:
            # Convert to numpy array
            img_array = np.array(image)
            original_shape = img_array.shape
            
            # 1. Resize if too small or too large
            processed_img = self._resize_image(img_array)
            
            # 2. Denoise
            processed_img = self._denoise_image(processed_img)
            
            # 3. Convert to grayscale
            gray_img = self._to_grayscale(processed_img)
            
            # 4. Enhance contrast
            enhanced_img = self._enhance_contrast(gray_img)
            
            # 5. Binarize for OCR
            binary_img = self._binarize_image(enhanced_img)
            
            # 6. Detect text regions
            text_regions = self._detect_text_regions(binary_img)
            
            return {
                "processed_image": Image.fromarray(binary_img),
                "original_shape": original_shape,
                "processed_shape": processed_img.shape,
                "text_regions": text_regions,
                "preprocessing_applied": [
                    "resize",
                    "denoise", 
                    "grayscale",
                    "contrast_enhancement",
                    "binarization"
                ]
            }
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return {
                "processed_image": image,
                "original_shape": img_array.shape,
                "processed_shape": img_array.shape,
                "text_regions": [],
                "preprocessing_applied": [],
                "error": str(e)
            }
    
    def _resize_image(self, img_array: np.ndarray) -> np.ndarray:
        """Resize image if too small or too large."""
        h, w = img_array.shape[:2]
        
        # Upscale if too small
        if h < self.min_image_size[0] or w < self.min_image_size[1]:
            scale_factor = max(
                self.min_image_size[0] / h,
                self.min_image_size[1] / w
            )
            new_h, new_w = int(h * scale_factor), int(w * scale_factor)
            return cv2.resize(img_array, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Downscale if too large
        elif h > self.max_image_size[0] or w > self.max_image_size[1]:
            scale_factor = min(
                self.max_image_size[0] / h,
                self.max_image_size[1] / w
            )
            new_h, new_w = int(h * scale_factor), int(w * scale_factor)
            return cv2.resize(img_array, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return img_array
    
    def _denoise_image(self, img_array: np.ndarray) -> np.ndarray:
        """Apply denoising to reduce noise."""
        try:
            # Use Non-local Means Denoising for color images
            if len(img_array.shape) == 3:
                return cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)
            else:
                return cv2.fastNlMeansDenoising(img_array, None, 10, 7, 21)
        except Exception:
            # Fallback to bilateral filter
            return cv2.bilateralFilter(img_array, 9, 75, 75)
    
    def _to_grayscale(self, img_array: np.ndarray) -> np.ndarray:
        """Convert to grayscale."""
        if len(img_array.shape) == 3:
            return cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        return img_array
    
    def _enhance_contrast(self, gray_img: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(gray_img)
        except Exception:
            # Fallback to simple histogram equalization
            return cv2.equalizeHist(gray_img)
    
    def _binarize_image(self, gray_img: np.ndarray) -> np.ndarray:
        """Binarize image for OCR using adaptive thresholding."""
        try:
            # Use adaptive thresholding for better text detection
            binary = cv2.adaptiveThreshold(
                gray_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            return binary
        except Exception:
            # Fallback to Otsu's method
            _, binary = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
    
    def _detect_text_regions(self, binary_img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect text regions in the binary image."""
        try:
            # Find contours
            contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            text_regions = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # Minimum area for text
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h if h > 0 else 0
                    
                    # Filter for text-like regions
                    if 0.1 < aspect_ratio < 10 and h > 10 and w > 10:
                        text_regions.append((x, y, w, h))
            
            # Sort by area (largest first)
            text_regions.sort(key=lambda r: r[2] * r[3], reverse=True)
            
            return text_regions[:10]  # Return top 10 regions
            
        except Exception as e:
            logger.warning(f"Text region detection failed: {e}")
            return []
    
    def crop_text_regions(self, image: Image.Image, text_regions: List[Tuple[int, int, int, int]]) -> List[Image.Image]:
        """Crop text regions from the image."""
        cropped_regions = []
        
        for x, y, w, h in text_regions:
            try:
                # Add some padding
                padding = 5
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(image.width, x + w + padding)
                y2 = min(image.height, y + h + padding)
                
                cropped = image.crop((x1, y1, x2, y2))
                cropped_regions.append(cropped)
            except Exception as e:
                logger.warning(f"Failed to crop region {x, y, w, h}: {e}")
                continue
        
        return cropped_regions

# Global instance
preprocessor = ImagePreprocessor()
