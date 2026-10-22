"""Crop disease prediction (tomato and chilli), output in Marathi."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras import layers, models

MODEL_NAME = "EfficientNetB3"
IMG_SIZE = 300
MIN_CONF = 0.8
BASE_DIR = Path(__file__).resolve().parent
WEIGHTS = BASE_DIR / "crop_disease.weights.h5"
LABELS = BASE_DIR / "class_names.json"

with open(LABELS, encoding="utf-8") as f:
    _d = json.load(f)
CLASS_NAMES, MARATHI = _d["classes"], _d["marathi"]

def build_model():
    # identical structure to training, so the weights file loads cleanly
    augment = tf.keras.Sequential([
        layers.RandomFlip("horizontal_and_vertical"),
        layers.RandomRotation(0.25, fill_mode="reflect"),
        layers.RandomZoom((-0.3, 0.5), fill_mode="reflect"),
        layers.RandomTranslation(0.2, 0.2, fill_mode="reflect"),
        layers.RandomContrast(0.3),
        layers.RandomBrightness(0.3, value_range=(0, 255)),
    ], name="augment")
    base = getattr(tf.keras.applications, MODEL_NAME)(
        include_top=False, weights=None, input_shape=(IMG_SIZE, IMG_SIZE, 3))
    inputs = layers.Input((IMG_SIZE, IMG_SIZE, 3))
    x = augment(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(len(CLASS_NAMES), activation="softmax")(x)
    return models.Model(inputs, outputs)

_model = None
def get_model():
    global _model
    if _model is None:
        _model = build_model()
        _model.load_weights(str(WEIGHTS))
    return _model

def predict(image_path_or_file):
    """Returns: class (English), marathi, confidence (0-1), is_confident."""
    img = Image.open(image_path_or_file).convert("RGB")   # always 3 channels
    w, h = img.size
    crops = [img]
    for frac in (0.7, 0.5):                               # whole image + zoomed crops
        cw, ch = int(w * frac), int(h * frac)
        for (x, y) in [((w-cw)//2, (h-ch)//2), (0, 0), (w-cw, 0), (0, h-ch), (w-cw, h-ch)]:
            crops.append(img.crop((x, y, x + cw, y + ch)))
    # raw 0-255 pixels: NO /255 (EfficientNet rescales internally)
    batch = np.stack([np.asarray(c.resize((IMG_SIZE, IMG_SIZE)), dtype="float32") for c in crops])
    probs = get_model().predict(batch, verbose=0).mean(axis=0)
    best = int(probs.argmax())
    return {"class": CLASS_NAMES[best], "marathi": MARATHI[CLASS_NAMES[best]],
            "confidence": float(probs[best]), "is_confident": bool(probs[best] >= MIN_CONF)}

if __name__ == "__main__":
    r = predict(sys.argv[1])
    print(r["class"], "|", r["marathi"], f'({r["confidence"]*100:.1f}%)',
          "" if r["is_confident"] else "- not sure, retake photo")
