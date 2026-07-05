#!/usr/bin/env python3
"""
Real text classification training script using DistilBERT.
Trains a phishing detection model on text data.
"""

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    DistilBertTokenizer, DistilBertForSequenceClassification,
    AdamW, get_linear_schedule_with_warmup
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import os

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
MODELS_DIR = PROJECT_ROOT / 'models' / 'text'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

class PhishingDataset(Dataset):
    """Dataset class for phishing text classification."""
    
    def __init__(self, texts, labels, tokenizer, max_length=256):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = int(self.labels[idx])
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

class PhishingTrainer:
    """Trainer class for phishing detection model."""
    
    def __init__(self, model_name='distilbert-base-uncased', num_labels=2):
        self.model_name = model_name
        self.num_labels = num_labels
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        # Load tokenizer and model
        self.tokenizer = DistilBertTokenizer.from_pretrained(model_name)
        self.model = DistilBertForSequenceClassification.from_pretrained(
            model_name, num_labels=num_labels
        )
        self.model.to(self.device)
    
    def load_data(self, data_path):
        """Load and preprocess training data."""
        print(f"Loading data from {data_path}")
        
        # Try to load from different possible files
        possible_files = [
            data_path / 'text_dataset.csv',
            data_path / 'combined_dataset.csv',
            data_path / 'text_demo.csv'
        ]
        
        df = None
        for file_path in possible_files:
            if file_path.exists():
                df = pd.read_csv(file_path)
                print(f"Loaded {len(df)} samples from {file_path}")
                break
        
        if df is None:
            raise FileNotFoundError(f"No dataset found in {data_path}")
        
        # Ensure we have the required columns
        if 'text' not in df.columns or 'label' not in df.columns:
            raise ValueError("Dataset must contain 'text' and 'label' columns")
        
        # Filter out any rows with missing data
        df = df.dropna(subset=['text', 'label'])
        
        # Convert labels to integers if needed
        df['label'] = df['label'].astype(int)
        
        print(f"Dataset info:")
        print(f"  Total samples: {len(df)}")
        print(f"  Phishing samples: {len(df[df['label'] == 1])}")
        print(f"  Legitimate samples: {len(df[df['label'] == 0])}")
        
        return df
    
    def prepare_datasets(self, df, test_size=0.2, val_size=0.1):
        """Split data into train/validation/test sets."""
        # First split: train+val vs test
        train_val_df, test_df = train_test_split(
            df, test_size=test_size, random_state=42, stratify=df['label']
        )
        
        # Second split: train vs val
        train_df, val_df = train_test_split(
            train_val_df, test_size=val_size/(1-test_size), random_state=42, stratify=train_val_df['label']
        )
        
        print(f"Data split:")
        print(f"  Train: {len(train_df)} samples")
        print(f"  Validation: {len(val_df)} samples")
        print(f"  Test: {len(test_df)} samples")
        
        # Create datasets
        train_dataset = PhishingDataset(
            train_df['text'].tolist(),
            train_df['label'].tolist(),
            self.tokenizer
        )
        
        val_dataset = PhishingDataset(
            val_df['text'].tolist(),
            val_df['label'].tolist(),
            self.tokenizer
        )
        
        test_dataset = PhishingDataset(
            test_df['text'].tolist(),
            test_df['label'].tolist(),
            self.tokenizer
        )
        
        return train_dataset, val_dataset, test_dataset
    
    def train(self, train_dataset, val_dataset, epochs=3, batch_size=16, learning_rate=2e-5):
        """Train the model."""
        print("Starting training...")
        
        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        # Setup optimizer and scheduler
        optimizer = AdamW(self.model.parameters(), lr=learning_rate)
        total_steps = len(train_loader) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=0, num_training_steps=total_steps
        )
        
        # Training loop
        self.model.train()
        best_val_loss = float('inf')
        training_history = []
        
        for epoch in range(epochs):
            print(f"\nEpoch {epoch + 1}/{epochs}")
            
            total_loss = 0
            for batch_idx, batch in enumerate(train_loader):
                # Move batch to device
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                # Forward pass
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                loss = outputs.loss
                total_loss += loss.item()
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                scheduler.step()
                
                if batch_idx % 10 == 0:
                    print(f"  Batch {batch_idx}/{len(train_loader)}, Loss: {loss.item():.4f}")
            
            avg_train_loss = total_loss / len(train_loader)
            
            # Validation
            val_loss, val_metrics = self.evaluate(val_loader)
            
            print(f"  Train Loss: {avg_train_loss:.4f}")
            print(f"  Val Loss: {val_loss:.4f}")
            print(f"  Val Accuracy: {val_metrics['accuracy']:.4f}")
            print(f"  Val F1: {val_metrics['f1']:.4f}")
            
            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_model()
                print("  New best model saved!")
            
            training_history.append({
                'epoch': epoch + 1,
                'train_loss': avg_train_loss,
                'val_loss': val_loss,
                'val_accuracy': val_metrics['accuracy'],
                'val_f1': val_metrics['f1']
            })
        
        return training_history
    
    def evaluate(self, data_loader):
        """Evaluate the model."""
        self.model.eval()
        total_loss = 0
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for batch in data_loader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
                
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                total_loss += outputs.loss.item()
                
                # Get predictions
                predictions = torch.argmax(outputs.logits, dim=-1)
                all_predictions.extend(predictions.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        avg_loss = total_loss / len(data_loader)
        
        # Calculate metrics
        accuracy = accuracy_score(all_labels, all_predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            all_labels, all_predictions, average='weighted'
        )
        
        metrics = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1
        }
        
        return avg_loss, metrics
    
    def save_model(self):
        """Save the trained model and tokenizer."""
        print("Saving model...")
        
        # Save model and tokenizer
        self.model.save_pretrained(MODELS_DIR)
        self.tokenizer.save_pretrained(MODELS_DIR)
        
        # Save training metadata
        metadata = {
            'model_name': self.model_name,
            'num_labels': self.num_labels,
            'trained_at': datetime.now().isoformat(),
            'device': str(self.device)
        }
        
        with open(MODELS_DIR / 'training_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Model saved to {MODELS_DIR}")

def main():
    """Main training function."""
    print("🚀 Starting text classification training...")
    print("=" * 60)
    
    try:
        # Initialize trainer
        trainer = PhishingTrainer()
        
        # Load data
        df = trainer.load_data(DATA_DIR)
        
        # Prepare datasets
        train_dataset, val_dataset, test_dataset = trainer.prepare_datasets(df)
        
        # Train model
        history = trainer.train(train_dataset, val_dataset, epochs=3)
        
        # Final evaluation on test set
        test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)
        test_loss, test_metrics = trainer.evaluate(test_loader)
        
        print("\n" + "=" * 60)
        print("🎯 Training Complete!")
        print(f"📊 Test Accuracy: {test_metrics['accuracy']:.4f}")
        print(f"📊 Test F1 Score: {test_metrics['f1']:.4f}")
        print(f"💾 Model saved to: {MODELS_DIR}")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        raise

if __name__ == "__main__":
    main()
