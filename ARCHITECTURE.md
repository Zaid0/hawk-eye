# System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                      (Browser - Frontend)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Dashboard   │  │   Mission    │  │  Simulator   │  ...   │
│  │              │  │   Planner    │  │  (NEW!)      │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                           │                     │
│                          ┌────────────────┴──────────┐         │
│                          │ Video Upload Handler      │         │
│                          │ - Drag & Drop             │         │
│                          │ - Progress Tracking       │         │
│                          └────────────────┬──────────┘         │
│                                           │                     │
└───────────────────────────────────────────┼─────────────────────┘
                                            │
                    ┌───────────────────────┴──────────────────┐
                    │                                          │
                    ▼ HTTP POST                        WebSocket
            /upload-video                                 /ws
                    │                                          │
┌───────────────────┼──────────────────────────────────────────┼────┐
│                   │        BACKEND SERVER (FastAPI)          │    │
│                   │                                          │    │
│  ┌────────────────▼────────────┐        ┌──────────────────▼──┐ │
│  │  Video Upload Endpoint      │        │  WebSocket Manager  │ │
│  │  - Receive file             │        │  - Broadcast msgs   │ │
│  │  - Save to temp             │        │  - Handle clients   │ │
│  │  - Start background task    │        │  - Reconnection     │ │
│  └────────────────┬────────────┘        └──────────────────▲──┘ │
│                   │                                          │    │
│                   ▼                                          │    │
│  ┌──────────────────────────────────────────────────────────┼──┐ │
│  │        Background Video Processor                        │  │ │
│  │                                                           │  │ │
│  │  1. Open video with cv2.VideoCapture()                   │  │ │
│  │  2. Loop through frames:                                 │  │ │
│  │     ┌─────────────────────────────────────┐              │  │ │
│  │     │ Read frame                          │              │  │ │
│  │     │ Encode to JPEG                      │              │  │ │
│  │     │      ▼                               │              │  │ │
│  │     │ ┌─────────────────────────────────┐ │              │  │ │
│  │     │ │   AI Worker (ai_worker.py)      │ │              │  │ │
│  │     │ │                                 │ │              │  │ │
│  │     │ │ ┌─────────────────────────────┐ │ │              │  │ │
│  │     │ │ │  YOLO Model (best.pt)       │ │ │              │  │ │
│  │     │ │ │  - Load model singleton     │ │ │              │  │ │
│  │     │ │ │  - Decode base64 image      │ │ │              │  │ │
│  │     │ │ │  - Run inference (async)    │ │ │              │  │ │
│  │     │ │ │  - Detect: human, vehicle,  │ │ │              │  │ │
│  │     │ │ │           drone             │ │ │              │  │ │
│  │     │ │ │  - Draw bounding boxes      │ │ │              │  │ │
│  │     │ │ │  - Return detections        │ │ │              │  │ │
│  │     │ │ └─────────────────────────────┘ │ │              │  │ │
│  │     │ │              ▼                  │ │              │  │ │
│  │     │ │  Return: {                      │ │              │  │ │
│  │     │ │    objects: [...],              │ │              │  │ │
│  │     │ │    count: 2,                    │ │              │  │ │
│  │     │ │    annotated_image: "..."       │ │              │  │ │
│  │     │ │  }                              │ │              │  │ │
│  │     │ └─────────────────────────────────┘ │              │  │ │
│  │     │      ▼                               │              │  │ │
│  │     │ Create WebSocket message            │              │  │ │
│  │     │ Broadcast to all clients ───────────┼──────────────┘  │ │
│  │     └─────────────────────────────────────┘                 │ │
│  │  3. Wait frame_delay (maintain FPS)                         │ │
│  │  4. Repeat until video ends                                 │ │
│  │  5. Cleanup temp file                                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼ WebSocket Message
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND RECEIVES                          │
│                                                                 │
│  WebSocket Handler (app.js)                                    │
│  - Receives: { type: "video_frame", data: {...} }              │
│  - Updates:                                                     │
│    ✓ Frame image (annotated with boxes)                        │
│    ✓ Frame counter (123 / 2859)                                │
│    ✓ Detection count (2 objects)                               │
│    ✓ Detection list (class, confidence, bbox)                  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  DISPLAY                                                │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  [Annotated Video Frame with Bounding Boxes]     │   │   │
│  │  │  ┌────────────┐  ┌────────────┐                  │   │   │
│  │  │  │  human 95% │  │ vehicle    │                  │   │   │
│  │  │  └────────────┘  │    87%     │                  │   │   │
│  │  │                  └────────────┘                  │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  │                                                          │   │
│  │  Frame: 123 / 2859          Detections: 2               │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │ Detection Details:                                 │ │   │
│  │  │ • human - 95.2% - [100, 200, 300, 400]             │ │   │
│  │  │ • vehicle - 87.3% - [450, 150, 650, 350]           │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Interactions

### 1. Upload Flow

```
User Action → Upload Video
    ↓
Frontend: handleVideoUpload()
    ↓
POST /upload-video (multipart/form-data)
    ↓
Backend: save to /tmp/xxx.mp4
    ↓
Backend: asyncio.create_task(process_uploaded_video)
    ↓
Return: {"status": "ok", "message": "Processing started"}
```

### 2. Processing Flow (per frame)

```
Read frame from video (cv2.VideoCapture)
    ↓
Encode to JPEG bytes
    ↓
await process_video_frame(bytes)
    ↓
Convert bytes → base64
    ↓
await process_frame_async(base64)
    ↓
Decode base64 → numpy array
    ↓
YOLO inference (async, thread pool)
    ↓
Parse detections (bbox, class, confidence)
    ↓
Draw boxes on image
    ↓
Encode annotated image → base64
    ↓
Return {objects, count, annotated_image}
    ↓
Create WebSocket message
    ↓
Broadcast to all connected clients
    ↓
await asyncio.sleep(1/fps)  # Maintain timing
```

### 3. WebSocket Message Flow

```
Backend: broadcaster.broadcast_json({...})
    ↓
All connected WebSocket clients receive
    ↓
Frontend: ws.onmessage(event)
    ↓
Parse JSON: JSON.parse(event.data)
    ↓
Route by message.type:
    - "video_frame" → updateSimulatorFrame()
    - "video_complete" → showUploadStatus()
    - "ai" → updateDetectionDisplay()
    ↓
Update DOM elements:
    - Frame image
    - Counters
    - Detection list
```

---

## Technology Stack

### Backend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | FastAPI | Async HTTP server + WebSocket |
| AI Model | Ultralytics YOLO | Object detection |
| Video Processing | OpenCV (cv2) | Frame extraction, encoding |
| Image Processing | NumPy, Pillow | Array manipulation |
| Async Runtime | asyncio | Non-blocking operations |
| Data Validation | Pydantic | Request/response models |

### Frontend

| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI Framework | Vanilla JS | No dependencies, fast |
| Real-time Comm | WebSocket API | Live updates |
| File Upload | Fetch API | HTTP requests |
| Canvas Drawing | Canvas API | Bounding boxes |
| Drag & Drop | HTML5 Drag/Drop | File upload UX |
| Routing | Hash-based SPA | View switching |

---

## Data Models

### Detection Object
```javascript
{
  class: "human",          // Object class name
  confidence: 0.952,       // 0.0 to 1.0
  bbox: [x1, y1, x2, y2]  // Bounding box coordinates
}
```

### WebSocket Message (video_frame)
```javascript
{
  type: "video_frame",
  data: {
    frame: "data:image/jpeg;base64,...",           // Original frame
    frame_number: 123,                              // Current frame
    total_frames: 2859,                             // Total in video
    detections: [Detection, ...],                   // Array of detections
    count: 2,                                       // Number of detections
    annotated_frame: "data:image/jpeg;base64,...", // With boxes drawn
    timestamp: 1234567890.123                       // Server timestamp
  }
}
```

### WebSocket Message (video_complete)
```javascript
{
  type: "video_complete",
  data: {
    message: "Video processing complete",
    total_frames: 2859
  }
}
```

---

## Performance Characteristics

### Latency Breakdown

| Stage | Time | Notes |
|-------|------|-------|
| Frame decode | ~2ms | cv2.VideoCapture |
| JPEG encode | ~3ms | cv2.imencode |
| YOLO inference | ~33ms | Your model |
| Box annotation | ~5ms | result.plot() |
| Base64 encode | ~2ms | Python base64 |
| WebSocket send | ~1ms | Local network |
| JSON parse | ~1ms | Frontend |
| DOM update | ~3ms | Browser render |
| **TOTAL** | **~50ms** | **~20 FPS** |

### Throughput

- **Video FPS**: 25 (maintained via frame_delay)
- **Processing FPS**: 30 (YOLO capability)
- **Effective FPS**: 25 (limited by video source)
- **Latency**: ~50ms end-to-end

### Resource Usage

- **CPU**: ~40% (single core, during processing)
- **Memory**: ~500MB (model + video buffer)
- **Network**: ~5Mbps (WebSocket @ 1920x1080, 25fps)
- **Disk**: Temporary (auto-cleanup)

---

## Scalability Considerations

### Current (Single Video)
- ✅ Real-time processing (25-30 FPS)
- ✅ Low latency (<100ms)
- ✅ Efficient memory usage

### Multi-Stream (Future)
To handle multiple videos simultaneously:
1. Use video queue system
2. Implement worker pool pattern
3. Add GPU acceleration (CUDA)
4. Stream-specific WebSocket channels
5. Distributed processing (celery/redis)

---

## Security Considerations

### Current Implementation
- ⚠️ CORS: Allow all origins (dev only)
- ⚠️ File size: No hard limit enforced
- ⚠️ File type: Client-side validation only
- ⚠️ Authentication: None

### Production Recommendations
1. Add authentication (JWT tokens)
2. Validate file types server-side
3. Limit file size (e.g., 100MB max)
4. Rate limiting on uploads
5. Restrict CORS to known origins
6. Input sanitization
7. HTTPS/WSS encryption

---

## Error Handling

### Backend
- Model loading errors → Logged, server won't start
- Frame processing errors → Logged, skip frame, continue
- WebSocket errors → Auto-reconnect logic
- File upload errors → Return 500 with message
- Video decode errors → Return error, cleanup

### Frontend
- Upload errors → Show error status to user
- WebSocket disconnect → Auto-reconnect (3s delay)
- Invalid message → Log, ignore
- Browser compatibility → Graceful degradation

---

This architecture provides a solid foundation for real-time drone surveillance with AI detection!
