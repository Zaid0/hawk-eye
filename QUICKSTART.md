# Quick Start Guide

## Fix Virtual Environment (IMPORTANT!)

There's an architecture mismatch in your virtual environment. Run these commands first:

```bash
# Remove old virtual environment
rm -rf .venv

# Create new virtual environment with correct architecture
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r backend/app/requirements.txt
```

## Start the Server

```bash
# Make sure you're in the project root directory
cd /Users/zaidrjoub/college/hawk-eye2

# Activate virtual environment
source .venv/bin/activate

# Start the backend server
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
✓ YOLO model loaded successfully
  Model classes: {0: 'human', 1: 'vehicle', 2: 'drone'}
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Open the Frontend

**Option 1: Simple (may have CORS issues)**
```bash
open frontend/index.html
```

**Option 2: Recommended (with local server)**
```bash
# In a new terminal
cd frontend
python3 -m http.server 8080
# Then visit http://localhost:8080
```

## Test the Integration

1. Open browser to http://localhost:8080 (or open index.html directly)
2. You should see a sidebar on the left
3. Click **"Drone Simulator"** (highlighted in blue)
4. Upload `backend/app/vid.mp4` (or any video)
5. Watch real-time AI detection!

## What You'll See

- Frame-by-frame processing at ~25 FPS
- Bounding boxes around detected objects
- Real-time detection stats:
  - human (green boxes)
  - vehicle (orange boxes)
  - drone (red boxes)
- Confidence scores for each detection

## Troubleshooting

### "Module not found" errors
```bash
# Reinstall all dependencies
pip install fastapi uvicorn ultralytics opencv-python python-multipart pydantic websockets
```

### "Port 8000 already in use"
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --reload --port 8001
# Then update frontend/app.js line 736 and line 884
```

### WebSocket not connecting
- Make sure backend is running (check terminal)
- Check browser console for errors (F12)
- Verify port 8000 is correct

## Architecture Overview

```
Frontend (Browser)
    ↓ Upload Video
Backend FastAPI Server
    ↓ Process frame-by-frame
YOLO Model (best.pt)
    ↓ Detect objects
WebSocket Broadcast
    ↓ Stream results
Frontend Display
    → Real-time bounding boxes
    → Detection statistics
```

## File Changes Summary

**Backend:**
- `backend/app/ai_worker.py` - YOLO integration (replaced mock)
- `backend/app/main.py` - Added video upload & WebSocket streaming
- `backend/app/requirements.txt` - Added dependencies

**Frontend:**
- `frontend/index.html` - Added sidebar nav + simulator view
- `frontend/app.js` - Added video upload + WebSocket handling

## Performance

Your model performance:
- **Inference time**: ~33ms per frame
- **FPS**: ~30 frames/second
- **Status**: ✅ Excellent for real-time!

Detection classes:
- human
- vehicle
- drone

## Next Steps

After testing locally, you can:
1. Deploy to a server for remote access
2. Add authentication/user management
3. Store videos and detections in a database
4. Add live drone connection (replace video upload with RTSP/WebRTC)
5. Export detection reports with timestamps

Good luck with your presentation! 🎓
