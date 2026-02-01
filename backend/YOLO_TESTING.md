# YOLO Model Testing Guide

This guide will help you test your YOLO model before integrating it into the HawkEye2 system.

## Prerequisites

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r app/requirements.txt
   ```

   Or install individually:
   ```bash
   pip install ultralytics opencv-python pillow numpy
   ```

2. **Prepare your model:**
   - Place your `.pt` model file somewhere accessible
   - Example: `backend/models/best.pt`

## Running the Test Script

### Basic Test (with your own image/video)

```bash
# Test with an image
python test_yolo_model.py --model path/to/your/model.pt --source path/to/test/image.jpg

# Test with a video
python test_yolo_model.py --model path/to/your/model.pt --source path/to/test/video.mp4
```

### Test with Dummy Data (no test image needed)

```bash
python test_yolo_model.py --model path/to/your/model.pt
```

This will automatically create a dummy test image for testing.

### Advanced Options

```bash
# Process more video frames (default is 30)
python test_yolo_model.py --model model.pt --source video.mp4 --max-frames 100

# Run more performance iterations (default is 50)
python test_yolo_model.py --model model.pt --source image.jpg --performance-iterations 100
```

## What the Script Tests

The script runs 4 comprehensive tests:

### 1. **Model Loading Test**
- Verifies the model file can be loaded
- Displays model metadata (task type, classes, etc.)

### 2. **Inference Test**
- Runs detection on your test image/video
- Shows detection results with bounding boxes
- Saves annotated output with prefix `test_output_`

### 3. **Performance Test**
- Measures inference speed over multiple iterations
- Calculates average, median, min, max inference times
- Estimates FPS for real-time processing

### 4. **Summary Report**
- Overall test results
- Readiness assessment for integration

## Expected Output

```
============================================================
 YOLO MODEL TEST SCRIPT - HAWKEYE2
============================================================

  Model Path: models/best.pt

============================================================
STEP 1: Testing Model Loading
============================================================
✓ Ultralytics library imported successfully
✓ Model loaded successfully from: models/best.pt

  Model Type: detect
  Model Names: {0: 'person', 1: 'weapon', 2: 'threat'}
  Number of Classes: 3

============================================================
STEP 2: Testing Image Inference
============================================================
✓ Inference completed on image: test.jpg

  Detections found: 2

  Detection details:
    [1] Class: person | Confidence: 85.23% | BBox: [100, 200, 300, 400]
    [2] Class: weapon | Confidence: 92.15% | BBox: [250, 150, 350, 250]

  ✓ Annotated image saved to: test_output_test.jpg

============================================================
STEP 4: Testing Real-time Performance
============================================================
  Running 50 iterations...
    Completed 10/50 iterations...
    Completed 20/50 iterations...
    ...

  Performance Metrics:
    Average inference time: 45.23ms
    Median inference time: 44.50ms
    Min inference time: 42.10ms
    Max inference time: 58.30ms
    Estimated FPS: 22.11

  ✓ EXCELLENT: Model is fast enough for real-time processing!

============================================================
 TEST SUMMARY
============================================================
  ✓ Model loading: PASSED
  ✓ Inference: PASSED
  ✓ Performance test: COMPLETED

  Your YOLO model is ready for integration into HawkEye2!
============================================================
```

## Output Files

The script creates annotated output files:

- **Images:** `test_output_<original_name>.jpg`
- **Videos:** `test_output_<original_name>.mp4`

These files contain bounding boxes and labels drawn on the original media.

## Troubleshooting

### Error: "ultralytics library not found"
```bash
pip install ultralytics
```

### Error: "Could not open video"
- Make sure the video file path is correct
- Try a different video format (MP4 is recommended)

### Error: "Model file not found"
- Check the path to your `.pt` file
- Use absolute path if relative path doesn't work

### Performance Warning
If the script reports slow performance:
- Consider using a smaller YOLO model (YOLOv8n instead of YOLOv8x)
- Enable GPU acceleration if available
- Reduce input image size in the integration code

## Next Steps

Once all tests pass:
1. Note the classes your model detects
2. Check the inference speed (should be <100ms for real-time)
3. Review the annotated output files to verify detection quality
4. Ready to integrate into the HawkEye2 backend!
