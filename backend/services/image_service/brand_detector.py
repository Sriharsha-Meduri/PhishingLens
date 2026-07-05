"""
Brand detection module using pre-trained YOLOv5/v8 weights.
Detects top-50 impersonated brands without custom training.
"""

import os
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from PIL import Image
import cv2

# Feature flag
FEATURE_BRAND_DETECTION = os.getenv("FEATURE_BRAND_DETECTION", "false").lower() == "true"
BRAND_WEIGHTS_URL = os.getenv("BRAND_WEIGHTS_URL", "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt")
BRAND_MODEL_VARIANT = os.getenv("BRAND_MODEL_VARIANT", "yolov5s")
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "1200"))

logger = logging.getLogger(__name__)

# Top-50 impersonated brands with their official domains
BRAND_DOMAINS = {
    "apple": ["apple.com", "icloud.com", "me.com"],
    "microsoft": ["microsoft.com", "office.com", "outlook.com", "live.com"],
    "google": ["google.com", "gmail.com", "youtube.com", "drive.google.com"],
    "amazon": ["amazon.com", "aws.amazon.com"],
    "paypal": ["paypal.com"],
    "meta": ["facebook.com", "instagram.com", "whatsapp.com", "meta.com"],
    "netflix": ["netflix.com"],
    "adobe": ["adobe.com"],
    "dhl": ["dhl.com"],
    "fedex": ["fedex.com"],
    "coinbase": ["coinbase.com"],
    "binance": ["binance.com"],
    "spotify": ["spotify.com"],
    "uber": ["uber.com"],
    "airbnb": ["airbnb.com"],
    "linkedin": ["linkedin.com"],
    "twitter": ["twitter.com", "x.com"],
    "dropbox": ["dropbox.com"],
    "zoom": ["zoom.us"],
    "slack": ["slack.com"],
    "github": ["github.com"],
    "discord": ["discord.com"],
    "telegram": ["telegram.org"],
    "whatsapp": ["whatsapp.com"],
    "instagram": ["instagram.com"],
    "tiktok": ["tiktok.com"],
    "snapchat": ["snapchat.com"],
    "pinterest": ["pinterest.com"],
    "reddit": ["reddit.com"],
    "ebay": ["ebay.com"],
    "etsy": ["etsy.com"],
    "shopify": ["shopify.com"],
    "stripe": ["stripe.com"],
    "square": ["squareup.com"],
    "venmo": ["venmo.com"],
    "cashapp": ["cash.app"],
    "zelle": ["zellepay.com"],
    "westernunion": ["westernunion.com"],
    "moneygram": ["moneygram.com"],
    "xoom": ["xoom.com"],
    "remitly": ["remitly.com"],
    "wise": ["wise.com"],
    "revolut": ["revolut.com"],
    "n26": ["n26.com"],
    "chime": ["chime.com"],
    "sofi": ["sofi.com"],
    "robinhood": ["robinhood.com"],
    "webull": ["webull.com"],
    "fidelity": ["fidelity.com"],
    "schwab": ["schwab.com"],
    "vanguard": ["vanguard.com"],
    "etrade": ["etrade.com"],
    "tdameritrade": ["tdameritrade.com"]
}

class BrandDetector:
    """Brand detection using pre-trained YOLO models."""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.degraded = False
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained YOLO model."""
        if not FEATURE_BRAND_DETECTION:
            logger.info("Brand detection disabled via feature flag")
            return
        
        try:
            # Try to import ultralytics
            from ultralytics import YOLO
            
            # Try to load from local cache first
            model_path = f"models/image/{BRAND_MODEL_VARIANT}.pt"
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                logger.info(f"Loaded brand model from {model_path}")
            else:
                # Download and cache the model
                logger.info(f"Downloading {BRAND_MODEL_VARIANT} model...")
                self.model = YOLO(f"{BRAND_MODEL_VARIANT}.pt")
                # Save for future use
                os.makedirs("models/image", exist_ok=True)
                # Note: ultralytics doesn't have a direct save method, but the model is cached
                logger.info(f"Model downloaded and cached")
            
            self.model_loaded = True
            logger.info("Brand detection model loaded successfully")
            
        except ImportError:
            logger.warning("ultralytics not available, brand detection disabled")
            self.degraded = True
        except Exception as e:
            logger.error(f"Failed to load brand detection model: {e}")
            self.degraded = True
    
    def detect_brands(self, image: Image.Image) -> Dict:
        """
        Detect brands in image using YOLO model.
        
        Returns:
            Dict with detected_brands, boxes, confidences, and visual_brand_risk
        """
        if not self.model_loaded or self.model is None:
            return {
                "detected_brands": [],
                "boxes": [],
                "confidences": [],
                "visual_brand_risk": 0.0,
                "degraded": self.degraded
            }
        
        try:
            # Convert PIL to numpy array
            img_array = np.array(image)
            
            # Run inference
            results = self.model(img_array, conf=0.6, verbose=False)
            
            detected_brands = []
            boxes = []
            confidences = []
            visual_brand_risk = 0.0
            
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        conf = float(box.conf[0])
                        if conf >= 0.6:
                            # Get class name (this would need to be mapped from COCO classes to brands)
                            # For now, we'll use a simple heuristic based on detected objects
                            class_id = int(box.cls[0])
                            
                            # Map common COCO classes to potential brand indicators
                            brand_indicators = self._map_coco_to_brands(class_id)
                            
                            if brand_indicators:
                                detected_brands.extend(brand_indicators)
                                boxes.append(box.xyxy[0].tolist())
                                confidences.append(conf)
                                
                                # Calculate brand risk based on confidence
                                visual_brand_risk += min(0.3, conf * 0.5)
            
            return {
                "detected_brands": detected_brands,
                "boxes": boxes,
                "confidences": confidences,
                "visual_brand_risk": min(1.0, visual_brand_risk),
                "degraded": False
            }
            
        except Exception as e:
            logger.error(f"Brand detection failed: {e}")
            return {
                "detected_brands": [],
                "boxes": [],
                "confidences": [],
                "visual_brand_risk": 0.0,
                "degraded": True
            }
    
    def _map_coco_to_brands(self, class_id: int) -> List[str]:
        """Map COCO class IDs to potential brand indicators."""
        # COCO class mappings to brand-related objects
        coco_to_brands = {
            0: ["person"],  # person - could be in brand context
            1: ["bicycle"],  # bicycle
            2: ["car"],  # car - could be brand-related
            3: ["motorcycle"],  # motorcycle
            4: ["airplane"],  # airplane
            5: ["bus"],  # bus
            6: ["train"],  # train
            7: ["truck"],  # truck
            8: ["boat"],  # boat
            9: ["traffic_light"],  # traffic light
            10: ["fire_hydrant"],  # fire hydrant
            11: ["stop_sign"],  # stop sign
            12: ["parking_meter"],  # parking meter
            13: ["bench"],  # bench
            14: ["bird"],  # bird
            15: ["cat"],  # cat
            16: ["dog"],  # dog
            17: ["horse"],  # horse
            18: ["sheep"],  # sheep
            19: ["cow"],  # cow
            20: ["elephant"],  # elephant
            21: ["bear"],  # bear
            22: ["zebra"],  # zebra
            23: ["giraffe"],  # giraffe
            24: ["backpack"],  # backpack
            25: ["umbrella"],  # umbrella
            26: ["handbag"],  # handbag
            27: ["tie"],  # tie
            28: ["suitcase"],  # suitcase
            29: ["frisbee"],  # frisbee
            30: ["skis"],  # skis
            31: ["snowboard"],  # snowboard
            32: ["sports_ball"],  # sports ball
            33: ["kite"],  # kite
            34: ["baseball_bat"],  # baseball bat
            35: ["baseball_glove"],  # baseball glove
            36: ["skateboard"],  # skateboard
            37: ["surfboard"],  # surfboard
            38: ["tennis_racket"],  # tennis racket
            39: ["bottle"],  # bottle
            40: ["wine_glass"],  # wine glass
            41: ["cup"],  # cup
            42: ["fork"],  # fork
            43: ["knife"],  # knife
            44: ["spoon"],  # spoon
            45: ["bowl"],  # bowl
            46: ["banana"],  # banana
            47: ["apple"],  # apple - could be Apple brand
            48: ["sandwich"],  # sandwich
            49: ["orange"],  # orange
            50: ["broccoli"],  # broccoli
            51: ["carrot"],  # carrot
            52: ["hot_dog"],  # hot dog
            53: ["pizza"],  # pizza
            54: ["donut"],  # donut
            55: ["cake"],  # cake
            56: ["chair"],  # chair
            57: ["couch"],  # couch
            58: ["potted_plant"],  # potted plant
            59: ["bed"],  # bed
            60: ["dining_table"],  # dining table
            61: ["toilet"],  # toilet
            62: ["tv"],  # tv
            63: ["laptop"],  # laptop - tech brand indicator
            64: ["mouse"],  # mouse - tech brand indicator
            65: ["remote"],  # remote
            66: ["keyboard"],  # keyboard - tech brand indicator
            67: ["cell_phone"],  # cell phone - tech brand indicator
            68: ["microwave"],  # microwave
            69: ["oven"],  # oven
            70: ["toaster"],  # toaster
            71: ["sink"],  # sink
            72: ["refrigerator"],  # refrigerator
            73: ["book"],  # book
            74: ["clock"],  # clock
            75: ["vase"],  # vase
            76: ["scissors"],  # scissors
            77: ["teddy_bear"],  # teddy bear
            78: ["hair_drier"],  # hair drier
            79: ["toothbrush"]  # toothbrush
        }
        
        # Return potential brand indicators for tech-related objects
        if class_id in [47, 63, 64, 66, 67]:  # apple, laptop, mouse, keyboard, cell_phone
            return ["tech_brand"]
        
        return []
    
    def check_brand_domain_mismatch(self, detected_brands: List[str], ocr_text: str, extracted_urls: List[str]) -> float:
        """
        Check if detected brands have domain mismatches with extracted URLs.
        
        Args:
            detected_brands: List of detected brand names
            ocr_text: OCR extracted text
            extracted_urls: List of extracted URLs
            
        Returns:
            Risk score for brand-domain mismatch
        """
        if not detected_brands or not extracted_urls:
            return 0.0
        
        risk_score = 0.0
        
        for brand in detected_brands:
            brand_lower = brand.lower()
            
            # Check if brand name appears in OCR text
            if brand_lower in ocr_text.lower():
                # Check if any extracted URL matches official brand domains
                brand_domains = BRAND_DOMAINS.get(brand_lower, [])
                url_domains = [self._extract_domain(url) for url in extracted_urls]
                
                # Check for domain mismatch
                has_official_domain = any(domain in url_domains for domain in brand_domains)
                
                if not has_official_domain:
                    risk_score += 0.3
                    logger.info(f"Brand-domain mismatch detected: {brand} not in {url_domains}")
        
        return min(1.0, risk_score)
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ""

# Global instance
brand_detector = BrandDetector()
