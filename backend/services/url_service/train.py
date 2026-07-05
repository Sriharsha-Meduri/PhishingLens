import pandas as pd
from sklearn.ensemble import IsolationForest
from pathlib import Path
import joblib

DATA = Path(__file__).resolve().parents[3] / 'data' / 'processed' / 'text_demo.csv'
MODELS = Path(__file__).resolve().parents[3] / 'models'
MODELS.mkdir(parents=True, exist_ok=True)

# Demo: train IsolationForest on character counts of text field as placeholder
if not DATA.exists():
	raise SystemExit(f"Dataset not found: {DATA}")

df = pd.read_csv(DATA)
X = df['text'].fillna('').str.len().to_numpy().reshape(-1,1)
model = IsolationForest(n_estimators=50, random_state=42).fit(X)
joblib.dump(model, MODELS / 'url_iso_demo.joblib')
print('Saved models/url_iso_demo.joblib')
