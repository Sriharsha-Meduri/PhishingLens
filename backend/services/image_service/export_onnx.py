from pathlib import Path
MODELS = Path(__file__).resolve().parents[3] / 'models'
(MODELS / 'image_demo_model.onnx').write_text('onnx-placeholder')
print('Wrote models/image_demo_model.onnx')
