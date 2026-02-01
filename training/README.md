# YOLOv8 Fine-tuning for Military Datasets

This directory contains scripts for fine-tuning YOLOv8 medium on military detection datasets.

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Verify your datasets are in place:**
```
training/
├── datasets/
│   ├── Military.v1i.yolov8/
│   ├── DRONES_NEW.v4i.yolov8/
│   ├── vehicles.v2i.yolov8/
│   └── Drone Human detection.v8i.yolov8/
└── finetune_yolov8.py
```

## Running Training

### Basic Training (Recommended)
```bash
python finetune_yolov8.py
```

This will:
- Auto-detect your Mac's capabilities (MPS/CPU)
- Validate all datasets
- Train YOLOv8 medium on each dataset sequentially
- Save models to `military_detection/` directory

### Custom Training on Single Dataset
```python
from ultralytics import YOLO

model = YOLO('yolov8m.pt')
results = model.train(
    data='datasets/Military.v1i.yolov8/data.yaml',
    epochs=100,
    batch=16,
    imgsz=640,
    device='mps'  # or 'cpu'
)
```

## Mac Compatibility

### Will Your Mac Be Enough?

**M1/M2/M3 Macs (Apple Silicon):**
- ✅ **YES** - These have excellent MPS (Metal Performance Shaders) support
- Training speed: ~50-150 images/second
- Recommended batch size: 8-16
- Expected time per dataset: 2-6 hours

**Intel Macs:**
- ⚠️ **POSSIBLE but SLOW** - Will use CPU only
- Training speed: ~10-30 images/second
- Recommended batch size: 4-8
- Expected time per dataset: 8-20+ hours
- Consider using cloud GPUs instead

### Performance Tips for Mac

1. **Reduce batch size if you get memory errors:**
   - Edit `BATCH_SIZE = 8` in `finetune_yolov8.py`

2. **Use smaller image size for faster training:**
   - Edit `IMG_SIZE = 416` (default is 640)

3. **Close other applications** to free up RAM

4. **Keep your Mac plugged in** - training will drain battery fast

5. **Monitor with Activity Monitor** to check GPU/CPU usage

## Datasets Overview

| Dataset | Classes | Purpose |
|---------|---------|---------|
| Military.v1i.yolov8 | 6 | Military/civilian vehicles and aircraft |
| DRONES_NEW.v4i.yolov8 | 1 | Drone detection |
| vehicles.v2i.yolov8 | 7 | Military vehicles (tanks, trucks, etc.) |
| Drone Human detection.v8i.yolov8 | 2 | Human detection from drone view |
| Drone human.v1i.yolov8 | 1 | Human detection from drone |
| Drone human.v1i.yolov8 2 | 1 | Human detection from drone (duplicate/variant) |
| Human Detection Through Drone.v1i.yolov8 | 1 | Human detection from drone |
| Human detection from a drone.v1i.yolov8 | 1 | Person detection from drone |

**Note:** You have 4 similar human detection datasets. Consider merging them for better results or choosing the largest/best one.

## Output

After training, you'll find:

```
military_detection/
├── Military.v1i.yolov8/
│   └── weights/
│       ├── best.pt      # Best model
│       └── last.pt      # Last epoch
├── DRONES_NEW.v4i.yolov8/
│   └── weights/
│       ├── best.pt
│       └── last.pt
└── ... (other datasets)
```

## Using Trained Models

```python
from ultralytics import YOLO

# Load your trained model
model = YOLO('military_detection/Military.v1i.yolov8/weights/best.pt')

# Run inference
results = model('path/to/image.jpg')

# Display results
results[0].show()
```

## Troubleshooting

### "MPS not available" error
- Update to macOS 12.3+ and PyTorch 1.12+
- The script will fall back to CPU automatically

### Out of memory errors
- Reduce `BATCH_SIZE` in the script
- Reduce `IMG_SIZE` to 416 or 512
- Close other applications

### Slow training on Intel Mac
- Consider using Google Colab (free GPU)
- Or AWS/Azure cloud instances

## Cloud Alternatives

If your Mac is too slow, consider:

1. **Google Colab** (Free GPU):
   - Upload datasets and run training there
   - Free Tesla T4 GPU

2. **Roboflow** (Has built-in training):
   - Your datasets are from Roboflow
   - They offer cloud training options

3. **AWS SageMaker / Azure ML** (Paid):
   - More powerful GPUs available
