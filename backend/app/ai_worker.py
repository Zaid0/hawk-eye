# app/ai_worker.py
import asyncio
import base64
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from ultralytics import YOLO

# Global YOLO model instance
_model: Optional[YOLO] = None
_model_path = Path(__file__).parent / "best.pt"


def load_model():
    """Load the YOLO model. Called once at startup."""
    global _model
    if _model is None:
        try:
            _model = YOLO(str(_model_path))
            print(f"✓ YOLO model loaded successfully from {_model_path}")
            print(f"  Model classes: {_model.names}")
        except Exception as e:
            print(f"✗ ERROR loading YOLO model: {e}")
            print(f"  Model path: {_model_path}")
            raise
    return _model


def decode_base64_image(image_base64: str) -> np.ndarray:
    """Decode base64 string to OpenCV image."""
    # Remove data URL prefix if present
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]

    # Decode base64 to bytes
    image_bytes = base64.b64decode(image_base64)

    # Convert to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)

    # Decode to OpenCV image
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    return img


def encode_image_to_base64(img: np.ndarray) -> str:
    """Encode OpenCV image to base64 string."""
    _, buffer = cv2.imencode('.jpg', img)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{img_base64}"


async def process_frame_async(image_base64: str) -> Dict:
    """
    Process a single frame with YOLO model.

    Args:
        image_base64: Base64 encoded image string

    Returns:
        Dict containing detection results with format:
        {
            "objects": [
                {
                    "class": "human",
                    "confidence": 0.95,
                    "bbox": [x1, y1, x2, y2]
                },
                ...
            ],
            "count": 2,
            "annotated_image": "base64_encoded_image_with_boxes"
        }
    """
    try:
        # Ensure model is loaded
        model = load_model()

        # Decode image
        img = decode_base64_image(image_base64)

        if img is None:
            return {
                "objects": [],
                "count": 0,
                "error": "Failed to decode image"
            }

        # Run inference (run in thread pool to avoid blocking)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: model(img, verbose=False)
        )

        result = results[0]
        detections = result.boxes

        # Parse detections
        detected_objects = []
        for det in detections:
            cls_id = int(det.cls[0])
            conf = float(det.conf[0])
            bbox = det.xyxy[0].cpu().numpy().tolist()

            # Get class name and replace "human" with "soldier"
            class_name = model.names[cls_id]
            if class_name.lower() == "human":
                class_name = "soldier"

            detected_objects.append({
                "class": class_name,
                "confidence": round(conf, 4),
                "bbox": [round(x, 2) for x in bbox]  # [x1, y1, x2, y2]
            })

        # Generate annotated image
        annotated_img = result.plot()
        annotated_base64 = encode_image_to_base64(annotated_img)

        return {
            "objects": detected_objects,
            "count": len(detected_objects),
            "annotated_image": annotated_base64
        }

    except Exception as e:
        print(f"Error processing frame: {e}")
        import traceback
        traceback.print_exc()
        return {
            "objects": [],
            "count": 0,
            "error": str(e)
        }


async def process_video_frame(frame_data: bytes) -> Dict:
    """
    Process a video frame (raw bytes) with YOLO model.

    Args:
        frame_data: Raw frame bytes (JPEG/PNG)

    Returns:
        Detection results dictionary
    """
    try:
        # Convert bytes to base64
        frame_base64 = base64.b64encode(frame_data).decode('utf-8')

        # Process with existing function
        return await process_frame_async(frame_base64)

    except Exception as e:
        print(f"Error processing video frame: {e}")
        return {
            "objects": [],
            "count": 0,
            "error": str(e)
        }
