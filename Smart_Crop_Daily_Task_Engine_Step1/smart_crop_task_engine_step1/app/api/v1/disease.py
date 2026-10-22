from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/disease", tags=["Disease Detection"])
MAX_IMAGE_SIZE = 10 * 1024 * 1024
DEFAULT_MODEL_DIR = (
    Path(__file__).resolve().parents[5]
    / "smart-crop-advisory"
    / "models"
    / "crop_disease"
)


def _model_dir() -> Path:
    configured = os.getenv("CROP_DISEASE_MODEL_DIR")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_MODEL_DIR


@lru_cache(maxsize=1)
def _load_predictor(model_dir: str):
    predict_file = Path(model_dir) / "predict.py"
    if not predict_file.is_file():
        raise FileNotFoundError(f"Disease predictor not found: {predict_file}")

    spec = spec_from_file_location("smartcrop_disease_predictor", predict_file)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load the disease predictor module")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.predict


def _predict_image(image_bytes: bytes) -> dict:
    predictor = _load_predictor(str(_model_dir()))
    return predictor(BytesIO(image_bytes))


@router.post("/predict")
async def predict_disease(file: UploadFile = File(...)):
    image_bytes = await file.read(MAX_IMAGE_SIZE + 1)
    await file.close()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB limit.")

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Upload a valid image file.")

    try:
        result = await run_in_threadpool(_predict_image, image_bytes)
    except Exception as exc:
        logger.exception("Disease prediction failed")
        raise HTTPException(
            status_code=503,
            detail="Disease prediction is unavailable. Check the model files and dependencies.",
        ) from exc

    return {
        "success": True,
        "disease": result["class"],
        "disease_marathi": result["marathi"],
        "confidence": result["confidence"],
        "is_confident": result["is_confident"],
    }
