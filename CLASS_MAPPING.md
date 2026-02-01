# Class Label Mapping

## Backend Mapping (ai_worker.py)

The system automatically renames detection classes:

```python
# Line 109-111 in backend/app/ai_worker.py
class_name = model.names[cls_id]
if class_name.lower() == "human":
    class_name = "soldier"
```

**Result:** All "human" detections → "soldier"

## Frontend Color Coding (app.js)

Bounding boxes are color-coded by class:

| Class | Color | RGB |
|-------|-------|-----|
| **soldier** | 🟢 Green | `rgba(0,255,0,0.95)` |
| **vehicle** | 🟡 Yellow | `rgba(255,200,0,0.95)` |
| **drone** | 🔴 Red | `rgba(255,0,0,0.98)` |
| weapon | 🔴 Red | `rgba(255,80,80,0.98)` |
| threat | 🟠 Orange | `rgba(255,165,0,0.95)` |
| other | 🔵 Blue | `rgba(30,200,255,0.95)` |

## Detection List Format

**Before:**
```
human - t = 1.4s
vehicle - t = 3.2s
drone - t = 5.8s
```

**After:**
```
soldier - t = 1.4s    ← Changed from "human"
vehicle - t = 3.2s
drone - t = 5.8s
```

## To Add More Mappings

Edit `backend/app/ai_worker.py` line 109:

```python
# Get class name and apply custom mappings
class_name = model.names[cls_id]

# Add your custom mappings here
if class_name.lower() == "human":
    class_name = "soldier"
elif class_name.lower() == "car":
    class_name = "vehicle"
elif class_name.lower() == "person":
    class_name = "soldier"
# ... add more mappings as needed
```

## Color Customization

Edit `frontend/app.js` line 474-489:

```javascript
// Add or modify colors here
if (labelLower === 'soldier' || labelLower === 'human') {
  color = 'rgba(0,255,0,0.95)';    // Green
} else if (labelLower === 'vehicle') {
  color = 'rgba(255,200,0,0.95)';  // Yellow
}
// ... etc
```

---

**All changes are backend-side!** The YOLO model still detects "human", but the system converts it to "soldier" before displaying.
