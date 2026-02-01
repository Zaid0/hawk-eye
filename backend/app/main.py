# backend/app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .broadcaster import Broadcaster
from .models import TelemetryIn, AIResult
from .ai_worker import process_frame_async, process_video_frame, load_model
from .storage import telemetry_history

import asyncio
import csv
import io
import cv2
import base64
import time
from pathlib import Path
import tempfile
import requests
import numpy as np

# In-memory history:
telemetry_history = []

# WebSocket broadcaster:
broadcaster = Broadcaster()

# Camera feed mode - default is camera feed, switches to upload when video uploaded
camera_feed_active = True
camera_feed_task = None

app = FastAPI(title="HawkEye Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------
# Startup: Load YOLO model
# -------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Load YOLO model on startup and start camera feed"""
    global camera_feed_task
    try:
        load_model()
        print("✓ Server startup complete - YOLO model ready")
        # Start camera feed processing
        camera_feed_task = asyncio.create_task(process_camera_feed())
        print("✓ Camera feed processing started")
    except Exception as e:
        print(f"✗ WARNING: Failed to load YOLO model on startup: {e}")
        print("  Video processing will not work until model is available")

# -------------------------------------------------------
# POST /telemetry
# -------------------------------------------------------


@app.post("/telemetry")
async def receive_telemetry(request: Request):
    """
    Receive telemetry POSTed by drone.
    If image_base64 is present, AI worker will process it asynchronously.
    """
    payload = await request.json()

    try:
        t = TelemetryIn(**payload)
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=400
        )

    telemetry_history.append(t.dict())

    # Broadcast telemetry to WebSocket clients
    await broadcaster.broadcast_json(
        {"type": "telemetry", "data": t.dict()}
    )

    # If frame present → async AI evaluation
    if t.image_base64:
        asyncio.create_task(_handle_ai(t.dict()))

    return JSONResponse({"status": "ok"})


# -------------------------------------------------------
# Background AI processing
# -------------------------------------------------------
async def _handle_ai(telemetry_item: dict):
    ai_res = await process_frame_async(
        telemetry_item.get("image_base64")
    )

    telemetry_item["ai"] = ai_res

    telemetry_history.append({
        "time": telemetry_item.get("time"),
        "ai": ai_res
    })

    await broadcaster.broadcast_json({
        "type": "ai",
        "data": {"time": telemetry_item.get("time"), "ai": ai_res}
    })


# -------------------------------------------------------
# GET latest telemetry
# -------------------------------------------------------
@app.get("/telemetry/latest")
async def latest():
    return telemetry_history[-1] if telemetry_history else {}


# -------------------------------------------------------
# GET filtered telemetry
# -------------------------------------------------------
@app.get("/telemetry")
async def all_telemetry(
    limit: int = 1000,
    from_time: float = None,
    to_time: float = None,
    label: str = None
):
    def keep(item):
        if not isinstance(item, dict):
            return False
        if from_time is not None and item.get("time") and item.get("time") < from_time:
            return False
        if to_time is not None and item.get("time") and item.get("time") > to_time:
            return False
        if label and item.get("label") != label:
            return False
        return True

    filtered = [r for r in telemetry_history if keep(r)]
    return filtered[-limit:]


# -------------------------------------------------------
# Export CSV
# -------------------------------------------------------
@app.get("/telemetry/export")
async def export_csv():
    headers = ["time", "lat", "lng", "alt", "speed", "battery", "gps", "label"]

    stream = io.StringIO()
    writer = csv.writer(stream)

    writer.writerow(headers)
    for item in telemetry_history:
        row = [item.get(h, "") for h in headers]
        writer.writerow(row)

    stream.seek(0)

    return StreamingResponse(
        iter([stream.read()]),
        media_type="text/csv"
    )


# -------------------------------------------------------
# WebSocket endpoint
# -------------------------------------------------------
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = await broadcaster.connect(websocket)
    print(f"✓ WebSocket client {client_id} connected")

    try:
        while True:
            try:
                await websocket.receive_text()  # optional: handle commands
            except Exception:
                await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        print(f"✗ WebSocket client {client_id} disconnected")
        await broadcaster.disconnect(client_id)


# -------------------------------------------------------
# POST /upload-video - Upload video file for processing
# -------------------------------------------------------
@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file to simulate drone feed.
    The video will be processed frame by frame and results streamed via WebSocket.
    """
    global camera_feed_active, camera_feed_task

    try:
        # Stop camera feed mode
        camera_feed_active = False
        if camera_feed_task and not camera_feed_task.done():
            camera_feed_task.cancel()
            try:
                await camera_feed_task
            except asyncio.CancelledError:
                pass
        print("✓ Camera feed stopped for video upload")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        # Start background task to process video
        asyncio.create_task(process_uploaded_video(tmp_path))

        return JSONResponse({
            "status": "ok",
            "message": "Video upload successful. Processing started.",
            "filename": file.filename
        })

    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


async def process_uploaded_video(video_path: str):
    """
    Process uploaded video frame by frame and broadcast results via WebSocket.
    Simulates real-time drone feed.
    """
    try:
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"Error: Could not open video {video_path}")
            return

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_delay = 1.0 / fps  # Delay between frames to maintain original FPS

        frame_number = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"Processing video: {total_frames} frames at {fps} FPS")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_number += 1

            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            # Process frame with YOLO
            detection_result = await process_video_frame(frame_bytes)

            # Create frame data with detections
            frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')

            # Broadcast frame and detections to WebSocket clients
            await broadcaster.broadcast_json({
                "type": "video_frame",
                "data": {
                    "frame": f"data:image/jpeg;base64,{frame_base64}",
                    "frame_number": frame_number,
                    "total_frames": total_frames,
                    "detections": detection_result.get("objects", []),
                    "count": detection_result.get("count", 0),
                    "annotated_frame": detection_result.get("annotated_image"),
                    "timestamp": time.time()
                }
            })

            # Also broadcast as AI detection event
            if detection_result.get("count", 0) > 0:
                await broadcaster.broadcast_json({
                    "type": "ai",
                    "data": {
                        "time": time.time(),
                        "ai": {
                            "objects": [obj["class"] for obj in detection_result.get("objects", [])],
                            "detections": detection_result.get("objects", [])
                        }
                    }
                })

            # Maintain original video FPS
            await asyncio.sleep(frame_delay)

        cap.release()

        # Clean up temporary file
        Path(video_path).unlink(missing_ok=True)

        # Broadcast completion
        await broadcaster.broadcast_json({
            "type": "video_complete",
            "data": {
                "message": "Video processing complete",
                "total_frames": frame_number
            }
        })

        print(f"✓ Video processing complete: {frame_number} frames")

        # Return to camera feed mode
        global camera_feed_active, camera_feed_task
        camera_feed_active = True
        if not camera_feed_task or camera_feed_task.done():
            camera_feed_task = asyncio.create_task(process_camera_feed())
            print("✓ Returning to camera feed mode")

    except Exception as e:
        print(f"Error processing video: {e}")
        import traceback
        traceback.print_exc()


async def process_camera_feed():
    """
    Process camera feed from ESP32-CAM (like camfeed.py).
    Continuously captures frames from the camera and broadcasts them via WebSocket.
    """
    global camera_feed_active
    camera_url = "https://568f9790e762.ngrok-free.app/capture"

    print(f"Starting camera feed from {camera_url}")

    frame_count = 0

    while camera_feed_active:
        try:
            # Capture frame from ESP32-CAM
            img_resp = requests.get(camera_url, timeout=2)

            if img_resp.status_code != 200:
                await asyncio.sleep(0.1)
                continue

            img_arr = np.frombuffer(img_resp.content, np.uint8)
            frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)

            if frame is None:
                await asyncio.sleep(0.1)
                continue

            frame_count += 1

            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            # Process frame with YOLO
            detection_result = await process_video_frame(frame_bytes)

            # Create frame data with detections
            frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')

            # Broadcast frame and detections to WebSocket clients
            await broadcaster.broadcast_json({
                "type": "video_frame",
                "data": {
                    "frame": f"data:image/jpeg;base64,{frame_base64}",
                    "frame_number": frame_count,
                    "detections": detection_result.get("objects", []),
                    "count": detection_result.get("count", 0),
                    "annotated_frame": detection_result.get("annotated_image"),
                    "timestamp": time.time(),
                    "source": "camera"
                }
            })

            # Also broadcast as AI detection event if objects detected
            if detection_result.get("count", 0) > 0:
                await broadcaster.broadcast_json({
                    "type": "ai",
                    "data": {
                        "time": time.time(),
                        "ai": {
                            "objects": [obj["class"] for obj in detection_result.get("objects", [])],
                            "detections": detection_result.get("objects", [])
                        }
                    }
                })

            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.033)  # ~30 FPS

        except requests.RequestException as e:
            # Camera connection error - wait before retry
            print(f"Camera connection error: {e}")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error processing camera feed: {e}")
            await asyncio.sleep(0.5)

    print("Camera feed processing stopped")


# -------------------------------------------------------
# POST /refresh-feed - Return to camera feed mode
# -------------------------------------------------------
@app.post("/refresh-feed")
async def refresh_feed():
    """
    Stop any uploaded video processing and return to camera feed mode.
    """
    global camera_feed_active, camera_feed_task

    camera_feed_active = True

    # Start camera feed if not already running
    if not camera_feed_task or camera_feed_task.done():
        camera_feed_task = asyncio.create_task(process_camera_feed())
        print("✓ Camera feed restarted")

    # Clear recorded frames on the client side
    await broadcaster.broadcast_json({
        "type": "feed_refresh",
        "data": {
            "message": "Returning to camera feed",
            "source": "camera"
        }
    })

    return JSONResponse({
        "status": "ok",
        "message": "Camera feed activated"
    })


# -------------------------------------------------------
# POST /process-frame - Process single frame
# -------------------------------------------------------
@app.post("/process-frame")
async def process_single_frame(request: Request):
    """
    Process a single frame with YOLO detection.
    Expects JSON with base64 encoded image.
    """
    try:
        data = await request.json()
        image_base64 = data.get("image")

        if not image_base64:
            return JSONResponse(
                {"status": "error", "message": "No image provided"},
                status_code=400
            )

        result = await process_frame_async(image_base64)

        return JSONResponse({
            "status": "ok",
            "result": result
        })

    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )
