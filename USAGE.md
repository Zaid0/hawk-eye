# How to Use HawkEye2

## Quick Start

### 1. Start Backend
```bash
cd backend
source ../.venv/bin/activate
uvicorn app.main:app --reload --host localhost --port 8000
```

### 2. Start Frontend
```bash
cd frontend
python3 -m http.server 8080
```

### 3. Upload Video (Admin/Operator)
Open: **http://localhost:8080/upload.html**
- Drag & drop or click to upload a video
- System processes it with YOLO AI detection
- Click "Open Dashboard" when done

### 4. View Dashboard (All Users)
Open: **http://localhost:8080** or **http://localhost:8080/index.html**

## What You'll See

### On Upload Page (`upload.html`)
- Simple drag & drop interface
- Upload progress indicator
- Success message with link to dashboard

### On Main Dashboard (`index.html`)
When someone uploads a video, **ALL connected users** see:

1. **"HawkEye Live Drone Camera"** (top left)
   - Shows **original video frames** (no boxes)
   - Simulates live drone feed

2. **"Recorded Footage & AI Detection"** (top right)
   - Shows **annotated frames with YOLO bounding boxes**
   - Detections highlighted:
     - Human: Green
     - Vehicle: Orange
     - Drone: Red

3. **Detection Events List** (below video)
   - Populated with real detections
   - Format: `ClassName - t = X.Xs`
   - Click to jump to that detection

## How It Works

```
1. Operator opens upload.html
2. Uploads video file
3. Backend processes frame-by-frame with YOLO
4. WebSocket broadcasts each frame to all connected clients
5. Dashboard updates in real-time:
   - Live camera shows original frame
   - Recorded footage shows annotated frame
   - Detection list gets populated
```

## Multiple Users

- **Upload Page**: Admin/operator only
- **Dashboard**: Everyone can view
- **Live Feed**: All users see the same video simultaneously
- **WebSocket**: Automatic reconnection

## File Structure

```
frontend/
├── index.html      ← Main dashboard (view feed)
├── upload.html     ← Upload page (admin/operator)
├── app.js          ← Dashboard logic + WebSocket
└── style.css       ← Styling
```

## Testing

1. Open **2 browser windows**:
   - Window 1: `http://localhost:8080/upload.html`
   - Window 2: `http://localhost:8080`

2. In Window 1: Upload `backend/app/vid.mp4`

3. In Window 2: Watch the feed appear in real-time!

## Detections Format

The system now populates the detection list with real YOLO results:

**Mock data (before):**
```
Attacker - t = 2.2s
Weapon - t = 5.8s
```

**Real data (after upload):**
```
human - t = 1.4s
vehicle - t = 3.2s
drone - t = 5.8s
```

Based on actual YOLO detections from your model!

---

**Ready for your presentation!** 🚁
