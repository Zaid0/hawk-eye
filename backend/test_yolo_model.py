#!/usr/bin/env python3
"""
YOLO Model Test Script
----------------------
This script tests your trained YOLO model (.pt file) to ensure it works correctly
before integrating it into the HawkEye2 drone monitoring system.

Usage:
    python test_yolo_model.py --model path/to/your/model.pt --source path/to/test/image_or_video.mp4

Requirements:
    pip install ultralytics opencv-python pillow
"""

import argparse
import sys
from pathlib import Path
import cv2
import numpy as np

def test_model_loading(model_path: str):
    """Test if the model can be loaded successfully."""
    print("\n" + "="*60)
    print("STEP 1: Testing Model Loading")
    print("="*60)

    try:
        from ultralytics import YOLO
        print(f"✓ Ultralytics library imported successfully")
    except ImportError:
        print("✗ ERROR: ultralytics library not found!")
        print("  Install it with: pip install ultralytics")
        return None

    try:
        model = YOLO(model_path)
        print(f"✓ Model loaded successfully from: {model_path}")

        # Print model information
        print(f"\n  Model Type: {model.task}")
        print(f"  Model Names: {model.names}")
        print(f"  Number of Classes: {len(model.names)}")

        return model
    except Exception as e:
        print(f"✗ ERROR loading model: {e}")
        return None


def test_image_inference(model, image_path: str):
    """Test inference on a single image."""
    print("\n" + "="*60)
    print("STEP 2: Testing Image Inference")
    print("="*60)

    try:
        # Run inference
        results = model(image_path, verbose=False)
        print(f"✓ Inference completed on image: {image_path}")

        # Analyze results
        result = results[0]
        detections = result.boxes

        print(f"\n  Detections found: {len(detections)}")

        if len(detections) > 0:
            print("\n  Detection details:")
            for i, det in enumerate(detections):
                cls_id = int(det.cls[0])
                conf = float(det.conf[0])
                bbox = det.xyxy[0].cpu().numpy()

                print(f"    [{i+1}] Class: {model.names[cls_id]} | Confidence: {conf:.2%} | BBox: {bbox}")

        # Save annotated image
        output_path = Path(image_path).parent / f"test_output_{Path(image_path).name}"
        annotated = result.plot()
        cv2.imwrite(str(output_path), annotated)
        print(f"\n  ✓ Annotated image saved to: {output_path}")

        return True

    except Exception as e:
        print(f"✗ ERROR during inference: {e}")
        return False


def test_video_inference(model, video_path: str, max_frames: int = 30):
    """Test inference on a video file."""
    print("\n" + "="*60)
    print("STEP 3: Testing Video Inference")
    print("="*60)

    try:
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"✗ ERROR: Could not open video: {video_path}")
            return False

        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"✓ Video opened: {video_path}")
        print(f"  Resolution: {width}x{height}")
        print(f"  FPS: {fps}")
        print(f"  Total Frames: {total_frames}")
        print(f"\n  Processing first {max_frames} frames...")

        # Setup video writer
        output_path = Path(video_path).parent / f"test_output_{Path(video_path).name}"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        frame_count = 0
        detection_stats = []

        while cap.isOpened() and frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            # Run inference
            results = model(frame, verbose=False)
            annotated_frame = results[0].plot()

            # Write frame
            out.write(annotated_frame)

            # Collect stats
            num_detections = len(results[0].boxes)
            detection_stats.append(num_detections)

            frame_count += 1

            if frame_count % 10 == 0:
                print(f"    Processed {frame_count} frames...")

        cap.release()
        out.release()

        print(f"\n  ✓ Processed {frame_count} frames")
        print(f"  Average detections per frame: {np.mean(detection_stats):.2f}")
        print(f"  Max detections in a frame: {max(detection_stats)}")
        print(f"  ✓ Annotated video saved to: {output_path}")

        return True

    except Exception as e:
        print(f"✗ ERROR during video inference: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_realtime_performance(model, test_image: str, iterations: int = 50):
    """Test inference speed for real-time performance."""
    print("\n" + "="*60)
    print("STEP 4: Testing Real-time Performance")
    print("="*60)

    try:
        import time

        # Load test image
        img = cv2.imread(test_image)
        if img is None:
            print(f"✗ Could not load test image: {test_image}")
            return False

        print(f"  Running {iterations} iterations...")

        times = []
        for i in range(iterations):
            start = time.time()
            results = model(img, verbose=False)
            end = time.time()
            times.append(end - start)

            if (i + 1) % 10 == 0:
                print(f"    Completed {i + 1}/{iterations} iterations...")

        times = np.array(times)

        print(f"\n  Performance Metrics:")
        print(f"    Average inference time: {np.mean(times)*1000:.2f}ms")
        print(f"    Median inference time: {np.median(times)*1000:.2f}ms")
        print(f"    Min inference time: {np.min(times)*1000:.2f}ms")
        print(f"    Max inference time: {np.max(times)*1000:.2f}ms")
        print(f"    Estimated FPS: {1/np.mean(times):.2f}")

        if np.mean(times) < 0.1:  # Less than 100ms
            print(f"\n  ✓ EXCELLENT: Model is fast enough for real-time processing!")
        elif np.mean(times) < 0.2:  # Less than 200ms
            print(f"\n  ✓ GOOD: Model should work well for near real-time processing")
        else:
            print(f"\n  ⚠ WARNING: Model may be slow for real-time video processing")

        return True

    except Exception as e:
        print(f"✗ ERROR during performance test: {e}")
        return False


def create_dummy_test_image():
    """Create a dummy test image if no source is provided."""
    print("\n  Creating dummy test image...")
    dummy_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    dummy_path = Path("test_dummy_image.jpg")
    cv2.imwrite(str(dummy_path), dummy_img)
    print(f"  ✓ Dummy image created: {dummy_path}")
    return str(dummy_path)


def main():
    parser = argparse.ArgumentParser(
        description="Test YOLO model for HawkEye2 integration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to your YOLO model file (.pt)"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Path to test image or video file (optional, will create dummy if not provided)"
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=30,
        help="Maximum frames to process for video testing (default: 30)"
    )
    parser.add_argument(
        "--performance-iterations",
        type=int,
        default=50,
        help="Number of iterations for performance testing (default: 50)"
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print(" YOLO MODEL TEST SCRIPT - HAWKEYE2")
    print("="*60)
    print(f"\n  Model Path: {args.model}")

    # Check if model exists
    if not Path(args.model).exists():
        print(f"\n✗ ERROR: Model file not found: {args.model}")
        print("\nPlease provide the correct path to your .pt model file")
        sys.exit(1)

    # STEP 1: Load model
    model = test_model_loading(args.model)
    if model is None:
        print("\n✗ FAILED: Could not load model")
        sys.exit(1)

    # Determine test source
    test_source = args.source
    if test_source is None:
        print("\n⚠ No test source provided, creating dummy image...")
        test_source = create_dummy_test_image()
    elif not Path(test_source).exists():
        print(f"\n✗ ERROR: Test source not found: {test_source}")
        sys.exit(1)

    # STEP 2: Test inference
    is_video = test_source.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))

    if is_video:
        success = test_video_inference(model, test_source, args.max_frames)
    else:
        success = test_image_inference(model, test_source)

    if not success:
        print("\n✗ FAILED: Inference test failed")
        sys.exit(1)

    # STEP 3: Test performance
    test_img = test_source if not is_video else create_dummy_test_image()
    test_realtime_performance(model, test_img, args.performance_iterations)

    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    print("  ✓ Model loading: PASSED")
    print("  ✓ Inference: PASSED")
    print("  ✓ Performance test: COMPLETED")
    print("\n  Your YOLO model is ready for integration into HawkEye2!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
