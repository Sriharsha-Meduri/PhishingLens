"""
Model fetching utility for downloading and caching pre-trained weights.
Downloads YOLOv5/v8 models and other required assets.
"""

import os
import sys
import logging
import requests
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# Model configurations
MODELS_CONFIG = {
    "yolov5s": {
        "url": "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt",
        "filename": "yolov5s.pt",
        "size_mb": 14.4
    },
    "yolov5m": {
        "url": "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5m.pt", 
        "filename": "yolov5m.pt",
        "size_mb": 41.9
    },
    "yolov5l": {
        "url": "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5l.pt",
        "filename": "yolov5l.pt", 
        "size_mb": 89.7
    },
    "yolov8s": {
        "url": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt",
        "filename": "yolov8s.pt",
        "size_mb": 21.5
    },
    "yolov8m": {
        "url": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt",
        "filename": "yolov8m.pt",
        "size_mb": 49.7
    }
}

class ModelFetcher:
    """Utility for downloading and caching model weights."""
    
    def __init__(self, models_dir: str = "models/image"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_model(self, model_name: str, force_download: bool = False) -> Optional[Path]:
        """
        Download and cache a model.
        
        Args:
            model_name: Name of the model to fetch
            force_download: Force re-download even if file exists
            
        Returns:
            Path to the downloaded model file, or None if failed
        """
        if model_name not in MODELS_CONFIG:
            logger.error(f"Unknown model: {model_name}")
            return None
        
        config = MODELS_CONFIG[model_name]
        model_path = self.models_dir / config["filename"]
        
        # Check if model already exists
        if model_path.exists() and not force_download:
            logger.info(f"Model {model_name} already exists at {model_path}")
            return model_path
        
        # Download model
        logger.info(f"Downloading {model_name} ({config['size_mb']} MB)...")
        try:
            response = requests.get(config["url"], stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Progress indicator
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024) == 0:  # Every MB
                                logger.info(f"Downloaded {downloaded // (1024 * 1024)} MB ({progress:.1f}%)")
            
            logger.info(f"Successfully downloaded {model_name} to {model_path}")
            return model_path
            
        except Exception as e:
            logger.error(f"Failed to download {model_name}: {e}")
            if model_path.exists():
                model_path.unlink()  # Remove partial download
            return None
    
    def fetch_all_models(self, force_download: bool = False) -> Dict[str, Optional[Path]]:
        """Download all configured models."""
        results = {}
        
        for model_name in MODELS_CONFIG:
            logger.info(f"Fetching {model_name}...")
            results[model_name] = self.fetch_model(model_name, force_download)
        
        return results
    
    def list_available_models(self) -> List[str]:
        """List models that are available locally."""
        available = []
        
        for model_name, config in MODELS_CONFIG.items():
            model_path = self.models_dir / config["filename"]
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                available.append(f"{model_name} ({size_mb:.1f} MB)")
        
        return available
    
    def cleanup_models(self, keep_models: List[str] = None) -> int:
        """
        Clean up unused model files.
        
        Args:
            keep_models: List of model names to keep
            
        Returns:
            Number of files removed
        """
        if keep_models is None:
            keep_models = ["yolov5s"]  # Keep default model
        
        removed_count = 0
        
        for model_name, config in MODELS_CONFIG.items():
            if model_name not in keep_models:
                model_path = self.models_dir / config["filename"]
                if model_path.exists():
                    model_path.unlink()
                    removed_count += 1
                    logger.info(f"Removed {model_name}")
        
        return removed_count


def main():
    """CLI interface for model fetching."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch and manage model weights")
    parser.add_argument("--model", help="Specific model to fetch")
    parser.add_argument("--all", action="store_true", help="Fetch all models")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    parser.add_argument("--list", action="store_true", help="List available models")
    parser.add_argument("--cleanup", action="store_true", help="Clean up unused models")
    parser.add_argument("--models-dir", default="models/image", help="Models directory")
    
    args = parser.parse_args()
    
    fetcher = ModelFetcher(args.models_dir)
    
    if args.list:
        available = fetcher.list_available_models()
        if available:
            print("Available models:")
            for model in available:
                print(f"  - {model}")
        else:
            print("No models available locally")
        return
    
    if args.cleanup:
        removed = fetcher.cleanup_models()
        print(f"Removed {removed} model files")
        return
    
    if args.all:
        results = fetcher.fetch_all_models(args.force)
        for model_name, path in results.items():
            if path:
                print(f"✓ {model_name}: {path}")
            else:
                print(f"✗ {model_name}: Failed")
    elif args.model:
        path = fetcher.fetch_model(args.model, args.force)
        if path:
            print(f"✓ {args.model}: {path}")
        else:
            print(f"✗ {args.model}: Failed")
    else:
        # Default: fetch yolov5s
        path = fetcher.fetch_model("yolov5s", args.force)
        if path:
            print(f"✓ yolov5s: {path}")
        else:
            print("✗ yolov5s: Failed")


if __name__ == "__main__":
    main()
