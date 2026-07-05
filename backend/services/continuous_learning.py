#!/usr/bin/env python3
"""
Continuous Learning Pipeline for Phishing Detection System.
Automatically retrains models with new data and deploys updated models.
"""

import os
import sys
import json
import time
import schedule
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import requests
import subprocess
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

# Import training modules
from services.text_service.train import PhishingTrainer
from services.text_service.export_onnx import export_model_to_onnx
from data.scripts.fetch_demo_data import ThreatIntelligenceFetcher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('continuous_learning.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContinuousLearningPipeline:
    """Continuous learning pipeline for phishing detection."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self.load_config(config_path)
        self.data_dir = PROJECT_ROOT / 'data'
        self.models_dir = PROJECT_ROOT / 'models'
        self.backup_dir = PROJECT_ROOT / 'model_backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.fetcher = ThreatIntelligenceFetcher()
        self.trainer = None
        
        # Performance tracking
        self.performance_history = []
        self.model_versions = []
        
    def load_config(self, config_path: Optional[Path] = None) -> Dict:
        """Load configuration for continuous learning."""
        default_config = {
            "retrain_interval_hours": 24,
            "min_new_samples": 100,
            "performance_threshold": 0.85,
            "model_retention_days": 30,
            "data_sources": {
                "phishtank": True,
                "otx": True,
                "misp": False
            },
            "notification_webhook": None,
            "auto_deploy": True,
            "backup_models": True
        }
        
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def fetch_new_data(self) -> Dict[str, int]:
        """Fetch new data from threat intelligence sources."""
        logger.info("Fetching new data from threat intelligence sources...")
        
        new_data_counts = {
            "phishtank": 0,
            "otx": 0,
            "legitimate": 0,
            "total": 0
        }
        
        try:
            # Fetch from PhishTank
            if self.config["data_sources"]["phishtank"]:
                phish_data = self.fetcher.fetch_phishtank_data(
                    os.getenv('PHISHTANK_API_KEY')
                )
                new_data_counts["phishtank"] = len(phish_data)
                
                # Save new phishing data
                if phish_data:
                    self.save_new_data(phish_data, "phishtank")
            
            # Fetch from OTX
            if self.config["data_sources"]["otx"]:
                otx_data = self.fetcher.fetch_otx_data(
                    os.getenv('OTX_API_KEY')
                )
                new_data_counts["otx"] = len(otx_data)
                
                # Save new OTX data
                if otx_data:
                    self.save_new_data(otx_data, "otx")
            
            # Generate legitimate samples
            legitimate_data = self.fetcher.fetch_legitimate_urls()
            new_data_counts["legitimate"] = len(legitimate_data)
            
            if legitimate_data:
                self.save_new_data(legitimate_data, "legitimate")
            
            new_data_counts["total"] = sum(new_data_counts.values())
            
            logger.info(f"Fetched {new_data_counts['total']} new samples")
            return new_data_counts
            
        except Exception as e:
            logger.error(f"Error fetching new data: {e}")
            return new_data_counts
    
    def save_new_data(self, data: List[Dict], source: str):
        """Save new data to the appropriate location."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_new_{timestamp}.json"
        filepath = self.data_dir / "raw" / filename
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(data)} samples from {source} to {filepath}")
    
    def check_retrain_conditions(self, new_data_counts: Dict[str, int]) -> bool:
        """Check if retraining conditions are met."""
        total_new = new_data_counts["total"]
        min_samples = self.config["min_new_samples"]
        
        if total_new < min_samples:
            logger.info(f"Not enough new data for retraining: {total_new} < {min_samples}")
            return False
        
        # Check if enough time has passed since last training
        last_training_file = self.models_dir / "text" / "last_training.json"
        if last_training_file.exists():
            with open(last_training_file, 'r') as f:
                last_training = json.load(f)
                last_time = datetime.fromisoformat(last_training["timestamp"])
                hours_since = (datetime.now() - last_time).total_seconds() / 3600
                
                if hours_since < self.config["retrain_interval_hours"]:
                    logger.info(f"Too soon for retraining: {hours_since:.1f}h < {self.config['retrain_interval_hours']}h")
                    return False
        
        return True
    
    def prepare_training_data(self) -> pd.DataFrame:
        """Prepare combined training data from all sources."""
        logger.info("Preparing training data...")
        
        all_data = []
        
        # Load existing datasets
        processed_dir = self.data_dir / "processed"
        for file_path in processed_dir.glob("*.csv"):
            try:
                df = pd.read_csv(file_path)
                if 'text' in df.columns and 'label' in df.columns:
                    all_data.append(df)
                    logger.info(f"Loaded {len(df)} samples from {file_path.name}")
            except Exception as e:
                logger.warning(f"Error loading {file_path}: {e}")
        
        # Load new data
        raw_dir = self.data_dir / "raw"
        for file_path in raw_dir.glob("*_new_*.json"):
            try:
                with open(file_path, 'r') as f:
                    new_data = json.load(f)
                
                # Convert to DataFrame format
                if isinstance(new_data, list):
                    df = pd.DataFrame(new_data)
                    if 'url' in df.columns:
                        df['text'] = df['url']
                        df['label'] = 1  # Assume phishing for new data
                    all_data.append(df)
                    logger.info(f"Loaded {len(df)} new samples from {file_path.name}")
            except Exception as e:
                logger.warning(f"Error loading new data {file_path}: {e}")
        
        if not all_data:
            raise ValueError("No training data found")
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Clean and deduplicate
        combined_df = combined_df.dropna(subset=['text', 'label'])
        combined_df = combined_df.drop_duplicates(subset=['text'])
        
        logger.info(f"Prepared {len(combined_df)} total samples for training")
        return combined_df
    
    def train_new_model(self, training_data: pd.DataFrame) -> Dict[str, Any]:
        """Train a new model with the latest data."""
        logger.info("Starting model training...")
        
        try:
            # Initialize trainer
            self.trainer = PhishingTrainer()
            
            # Prepare datasets
            train_dataset, val_dataset, test_dataset = self.trainer.prepare_datasets(training_data)
            
            # Train model
            history = self.trainer.train(train_dataset, val_dataset, epochs=3)
            
            # Evaluate on test set
            from torch.utils.data import DataLoader
            test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)
            test_loss, test_metrics = self.trainer.evaluate(test_loader)
            
            # Save training results
            training_results = {
                "timestamp": datetime.now().isoformat(),
                "samples_used": len(training_data),
                "test_accuracy": test_metrics["accuracy"],
                "test_f1": test_metrics["f1"],
                "test_precision": test_metrics["precision"],
                "test_recall": test_metrics["recall"],
                "training_history": history
            }
            
            # Save training metadata
            with open(self.models_dir / "text" / "last_training.json", 'w') as f:
                json.dump(training_results, f, indent=2)
            
            logger.info(f"Training complete - Accuracy: {test_metrics['accuracy']:.4f}, F1: {test_metrics['f1']:.4f}")
            return training_results
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
    
    def evaluate_model_performance(self, training_results: Dict[str, Any]) -> bool:
        """Evaluate if the new model meets performance requirements."""
        accuracy = training_results["test_accuracy"]
        f1_score = training_results["test_f1"]
        threshold = self.config["performance_threshold"]
        
        meets_threshold = accuracy >= threshold and f1_score >= threshold
        
        logger.info(f"Model performance - Accuracy: {accuracy:.4f}, F1: {f1_score:.4f}, Threshold: {threshold}")
        
        if meets_threshold:
            logger.info("✅ Model meets performance requirements")
        else:
            logger.warning("⚠️ Model does not meet performance requirements")
        
        return meets_threshold
    
    def backup_current_model(self):
        """Backup the current model before deploying new one."""
        if not self.config["backup_models"]:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"model_backup_{timestamp}"
        
        try:
            # Copy current model
            current_model_path = self.models_dir / "text"
            if current_model_path.exists():
                shutil.copytree(current_model_path, backup_path)
                logger.info(f"Model backed up to {backup_path}")
                
                # Clean old backups
                self.cleanup_old_backups()
                
        except Exception as e:
            logger.error(f"Error backing up model: {e}")
    
    def cleanup_old_backups(self):
        """Remove old model backups."""
        retention_days = self.config["model_retention_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                try:
                    # Extract timestamp from directory name
                    timestamp_str = backup_dir.name.split("_")[-1]
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if backup_date < cutoff_date:
                        shutil.rmtree(backup_dir)
                        logger.info(f"Removed old backup: {backup_dir}")
                except Exception as e:
                    logger.warning(f"Error cleaning up backup {backup_dir}: {e}")
    
    def deploy_new_model(self):
        """Deploy the new model to production."""
        if not self.config["auto_deploy"]:
            logger.info("Auto-deploy disabled, skipping deployment")
            return
        
        logger.info("Deploying new model...")
        
        try:
            # Export to ONNX
            export_model_to_onnx()
            
            # Restart services (if using Docker)
            if self.is_docker_environment():
                self.restart_docker_services()
            
            logger.info("✅ Model deployed successfully")
            
        except Exception as e:
            logger.error(f"Error deploying model: {e}")
            # Rollback to previous model if deployment fails
            self.rollback_model()
    
    def is_docker_environment(self) -> bool:
        """Check if running in Docker environment."""
        return os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "true"
    
    def restart_docker_services(self):
        """Restart Docker services to load new model."""
        try:
            # Restart text service
            subprocess.run([
                "docker", "compose", "-f", "deployment/docker-compose.yml",
                "restart", "text"
            ], check=True)
            logger.info("Text service restarted")
            
        except Exception as e:
            logger.error(f"Error restarting services: {e}")
    
    def rollback_model(self):
        """Rollback to previous model if deployment fails."""
        logger.warning("Rolling back to previous model...")
        
        try:
            # Find most recent backup
            backups = sorted(self.backup_dir.glob("model_backup_*"), reverse=True)
            if backups:
                latest_backup = backups[0]
                
                # Restore from backup
                current_model_path = self.models_dir / "text"
                if current_model_path.exists():
                    shutil.rmtree(current_model_path)
                
                shutil.copytree(latest_backup, current_model_path)
                logger.info(f"Rolled back to {latest_backup}")
                
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
    
    def send_notification(self, message: str, success: bool = True):
        """Send notification about training results."""
        webhook_url = self.config.get("notification_webhook")
        if not webhook_url:
            return
        
        try:
            payload = {
                "text": f"🤖 Phishing Detection Model Update",
                "attachments": [{
                    "color": "good" if success else "danger",
                    "fields": [{
                        "title": "Status",
                        "value": message,
                        "short": False
                    }]
                }]
            }
            
            requests.post(webhook_url, json=payload, timeout=10)
            logger.info("Notification sent")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def run_continuous_learning_cycle(self):
        """Run one complete continuous learning cycle."""
        logger.info("🔄 Starting continuous learning cycle...")
        
        try:
            # Fetch new data
            new_data_counts = self.fetch_new_data()
            
            # Check if retraining is needed
            if not self.check_retrain_conditions(new_data_counts):
                logger.info("No retraining needed at this time")
                return
            
            # Prepare training data
            training_data = self.prepare_training_data()
            
            # Backup current model
            self.backup_current_model()
            
            # Train new model
            training_results = self.train_new_model(training_data)
            
            # Evaluate performance
            if self.evaluate_model_performance(training_results):
                # Deploy new model
                self.deploy_new_model()
                
                # Send success notification
                message = f"Model retrained successfully! Accuracy: {training_results['test_accuracy']:.4f}"
                self.send_notification(message, success=True)
                
                # Update performance history
                self.performance_history.append(training_results)
                
            else:
                # Send warning notification
                message = f"Model retrained but performance below threshold. Accuracy: {training_results['test_accuracy']:.4f}"
                self.send_notification(message, success=False)
            
            logger.info("✅ Continuous learning cycle completed")
            
        except Exception as e:
            logger.error(f"❌ Continuous learning cycle failed: {e}")
            self.send_notification(f"Continuous learning failed: {str(e)}", success=False)
    
    def start_scheduler(self):
        """Start the continuous learning scheduler."""
        logger.info("🚀 Starting continuous learning scheduler...")
        
        # Schedule retraining
        schedule.every(self.config["retrain_interval_hours"]).hours.do(
            self.run_continuous_learning_cycle
        )
        
        # Run initial cycle
        self.run_continuous_learning_cycle()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main function to start continuous learning."""
    print("🚀 Starting Continuous Learning Pipeline...")
    print("=" * 60)
    
    try:
        # Initialize pipeline
        pipeline = ContinuousLearningPipeline()
        
        # Start scheduler
        pipeline.start_scheduler()
        
    except KeyboardInterrupt:
        logger.info("Continuous learning stopped by user")
    except Exception as e:
        logger.error(f"Continuous learning failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
