# Complete YOLOv8 Training Guide - Unified Military Detector

This guide will help you train a single YOLOv8 model that can detect all classes from your 7 military datasets.

## Overview

You have **7 datasets** with **label inconsistencies** that need normalization:

### Label Issues Found:
1. **Human variants**: `human`, `humans`, `Person`, `-humans-people-armymodel` → normalized to `person`
2. **Vehicle duplicates**: `tank`/`military_tank`, `Military truck`/`military_truck` → normalized
3. **Ignored classes**: `bnik9m nm` (unclear), `undefined` → removed

### Final Unified Classes (12 total):
1. `BMP` - Armored personnel carrier
2. `Grad` - Multiple rocket launcher
3. `Smerch` - Heavy multiple rocket launcher
4. `Tiger` - Russian armored vehicle
5. `civilian_aircraft`
6. `civilian_car`
7. `drone`
8. `military_aircraft`
9. `military_helicopter`
10. `military_tank`
11. `military_truck`
12. `person` - Humans detected from drone view

## Step-by-Step Training Process

### Step 1: Install Dependencies

```bash
cd /Users/zaidrjoub/college/hawk-eye2/training
pip install -r requirements.txt
```

### Step 2: Merge and Normalize Datasets

This script will:
- Combine all 7 datasets
- Normalize class labels (human→person, etc.)
- Remove unclear/undefined classes
- Create a unified dataset with 12 classes

```bash
python merge_datasets.py
```

**Expected output:**
```
Merged dataset created at: datasets/merged_military_dataset
Total classes: 12
Train images: ~XXXX
Valid images: ~XXX
Test images: ~XXX
```

### Step 3: Train Unified Model

```bash
python finetune_yolov8_merged.py
```

**This will:**
- Train YOLOv8 Medium on all classes
- Use your Mac's GPU (MPS) if available
- Save checkpoints every 10 epochs
- Create final model at: `unified_military_detector/yolov8m_all_classes/weights/best.pt`

**Training time estimate:**
- M1/M2/M3 Mac: 4-10 hours
- Intel Mac: 12-24+ hours (recommend using cloud instead)

### Step 4: Use Your Trained Model

```python
from ultralytics import YOLO

# Load your unified model
model = YOLO('unified_military_detector/yolov8m_all_classes/weights/best.pt')

# Detect on image
results = model('drone_footage.jpg')

# Show results
results[0].show()

# Get detections
for result in results:
    for box in result.boxes:
        cls_id = int(box.cls[0])
        class_name = result.names[cls_id]
        confidence = float(box.conf[0])
        print(f"Found {class_name} with {confidence:.2%} confidence")
```

## Training Configuration

**Hyperparameters** (in `finetune_yolov8_merged.py`):
```python
EPOCHS = 150           # Adjust if needed
BATCH_SIZE = 16        # Reduce to 8 if OOM errors
IMG_SIZE = 640         # Standard YOLO size
PATIENCE = 25          # Early stopping patience
```

**Optimizer Settings:**
- AdamW optimizer
- Cosine learning rate scheduler
- Learning rate: 0.001 → 0.00001
- Weight decay: 0.0005

**Data Augmentation:**
- Horizontal flip: 50%
- Mosaic augmentation
- HSV color jittering
- Translation and scaling

## Mac Compatibility

### Will Your Mac Be Enough?

**Apple Silicon (M1/M2/M3/M4):**
- ✅ **EXCELLENT** - Uses MPS (Metal Performance Shaders)
- Training speed: 50-150 images/second
- Recommended batch size: 16
- Expected time: 4-10 hours
- Memory needed: 8-16GB RAM

**Intel Mac:**
- ⚠️ **SLOW** - CPU only
- Training speed: 10-30 images/second
- Recommended batch size: 4-8
- Expected time: 12-24+ hours
- **Recommendation**: Use Google Colab free GPU instead

### Performance Tips

1. **If you get memory errors:**
   ```python
   BATCH_SIZE = 8  # or even 4
   IMG_SIZE = 512  # reduce from 640
   ```

2. **Monitor your Mac:**
   - Open Activity Monitor
   - Watch Memory and GPU usage
   - Keep Mac plugged in
   - Ensure good ventilation

3. **Resume interrupted training:**
   ```python
   from ultralytics import YOLO
   model = YOLO('unified_military_detector/yolov8m_all_classes/weights/last.pt')
   model.train(resume=True)
   ```

## Dataset Statistics

After merging, you should see something like:

```
Dataset: Military.v1i.yolov8          - Classes: 6
Dataset: DRONES_NEW.v4i.yolov8        - Classes: 1
Dataset: vehicles.v2i.yolov8          - Classes: 7
Dataset: Drone Human detection...     - Classes: 2 → 1 (normalized)
Dataset: Drone human.v1i.yolov8       - Classes: 1
Dataset: Human Detection Through...   - Classes: 1
Dataset: Human detection from...      - Classes: 1

Total unique classes: 12 (after normalization)
```

## Troubleshooting

### "MPS backend out of memory"
```python
# Reduce batch size
BATCH_SIZE = 8  # or 4
```

### "RuntimeError: MPS not available"
- Update to macOS 12.3+
- Update PyTorch: `pip install --upgrade torch torchvision`
- Script will fallback to CPU automatically

### "Module 'ultralytics' not found"
```bash
pip install ultralytics
```

### Training is too slow
- Check if MPS is being used (script will tell you)
- Close other applications
- Consider using Google Colab:
  1. Upload datasets to Google Drive
  2. Use free Tesla T4 GPU
  3. Training will be 5-10x faster

### Labels look wrong after merge
- Check `datasets/merged_military_dataset/data.yaml`
- Verify class names are correct
- Check a few label files in `datasets/merged_military_dataset/train/labels/`

## File Structure

After running everything:

```
training/
├── datasets/
│   ├── Military.v1i.yolov8/          # Original datasets
│   ├── DRONES_NEW.v4i.yolov8/
│   ├── vehicles.v2i.yolov8/
│   ├── ...
│   └── merged_military_dataset/       # ← Merged unified dataset
│       ├── data.yaml                  # ← Unified config
│       ├── train/
│       │   ├── images/
│       │   └── labels/
│       ├── valid/
│       └── test/
├── unified_military_detector/         # ← Training outputs
│   └── yolov8m_all_classes/
│       ├── weights/
│       │   ├── best.pt               # ← Your trained model!
│       │   └── last.pt               # ← Resume from here
│       ├── results.png               # Training curves
│       ├── confusion_matrix.png
│       └── ...
├── merge_datasets.py                  # Step 1
├── finetune_yolov8_merged.py         # Step 2
└── requirements.txt
```

## Expected Results

After training completes, you should see:

```
Validation Results:
  mAP50: 0.75-0.85      (75-85% accuracy at 50% IoU)
  mAP50-95: 0.50-0.70   (50-70% accuracy averaged across IoUs)
```

These are good results for a multi-class military detector!

## Cloud Alternatives (If Mac is Too Slow)

### Google Colab (Free)
1. Upload merged dataset to Google Drive
2. Open new Colab notebook
3. Mount Drive and run training
4. Free Tesla T4 GPU (~5-10x faster)

### Roboflow (Paid but Easy)
- Your datasets are from Roboflow
- They offer cloud training
- Easiest option but costs money

### AWS/Azure (Paid)
- Most powerful option
- Expensive ($1-3/hour for good GPU)
- Use only if you need fastest training

## Summary

**Quick Start:**
```bash
# 1. Install
pip install -r requirements.txt

# 2. Merge datasets with normalized labels
python merge_datasets.py

# 3. Train unified model
python finetune_yolov8_merged.py

# 4. Wait 4-10 hours (M1/M2/M3 Mac)

# 5. Use your model!
# Model saved at: unified_military_detector/yolov8m_all_classes/weights/best.pt
```

You'll have a **single model** that detects **all 12 classes** across your military datasets!
