"""
YOLOv8 Training Script for Merged Military Dataset
Trains a single unified model on all classes
"""

import os
import platform
from pathlib import Path
from ultralytics import YOLO
import torch

# Configuration
MERGED_DATASET = "datasets/merged_military_dataset/data.yaml"
MODEL_SIZE = "yolov8m.pt"  # medium model

# Training hyperparameters
EPOCHS = 150
BATCH_SIZE = 32  # Optimized for M4 Pro with 24GB RAM (can go up to 48)
IMG_SIZE = 640
PATIENCE = 25  # Early stopping patience
DEVICE = None  # Will be auto-detected

# Output configuration
PROJECT_NAME = "unified_military_detector"
RUN_NAME = "yolov8m_all_classes"


def check_system():
    """Check system capabilities and return appropriate device"""
    print(f"\n{'='*60}")
    print("SYSTEM INFORMATION")
    print(f"{'='*60}")
    print(f"Platform: {platform.system()}")
    print(f"Processor: {platform.processor()}")
    print(f"Python Version: {platform.python_version()}")
    print(f"PyTorch Version: {torch.__version__}")

    if platform.system() == "Darwin":  # macOS
        if torch.backends.mps.is_available():
            device = "mps"
            print(f"✓ MPS (Metal Performance Shaders) is available")
            print(f"  Your Mac's GPU will be used for training")
        else:
            device = "cpu"
            print(f"⚠ MPS not available, using CPU")
            print(f"  Consider updating to macOS 12.3+ and PyTorch 1.12+")
    elif torch.cuda.is_available():
        device = "0"
        print(f"✓ CUDA GPU available: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        print(f"⚠ Using CPU for training")

    print(f"{'='*60}\n")
    return device


def print_dataset_info(data_path):
    """Print information about the dataset"""
    import yaml

    with open(data_path, 'r') as f:
        data = yaml.safe_load(f)

    print(f"\n{'='*60}")
    print("DATASET INFORMATION")
    print(f"{'='*60}")
    print(f"Dataset: {os.path.dirname(data_path)}")
    print(f"Number of classes: {data['nc']}")
    print(f"\nClasses:")
    for i, cls in enumerate(data['names']):
        print(f"  {i}: {cls}")
    print(f"{'='*60}\n")


def train_model(data_path, device):
    """Train YOLOv8 on the merged dataset"""

    print(f"\n{'='*60}")
    print("TRAINING UNIFIED MODEL")
    print(f"{'='*60}\n")

    # Load pretrained model
    print(f"Loading {MODEL_SIZE} pretrained model...")
    model = YOLO(MODEL_SIZE)

    print(f"\nStarting training...")
    print(f"  Epochs: {EPOCHS}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Image size: {IMG_SIZE}")
    print(f"  Device: {device}")
    print(f"  Patience: {PATIENCE}")

    # Train
    results = model.train(
        data=data_path,
        epochs=EPOCHS,
        batch=BATCH_SIZE,
        imgsz=IMG_SIZE,
        device=device,
        project=PROJECT_NAME,
        name=RUN_NAME,
        patience=PATIENCE,
        save=True,
        save_period=10,  # Save checkpoint every 10 epochs
        plots=True,
        verbose=True,
        # Optimization settings
        optimizer='AdamW',
        lr0=0.001,  # Initial learning rate
        lrf=0.01,  # Final learning rate factor
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        # Augmentation
        hsv_h=0.015,  # Hue augmentation
        hsv_s=0.7,  # Saturation augmentation
        hsv_v=0.4,  # Value augmentation
        degrees=0.0,  # Rotation
        translate=0.1,  # Translation
        scale=0.5,  # Scale
        shear=0.0,  # Shear
        perspective=0.0,  # Perspective
        flipud=0.0,  # Flip up-down
        fliplr=0.5,  # Flip left-right
        mosaic=1.0,  # Mosaic augmentation
        mixup=0.0,  # Mixup augmentation
        copy_paste=0.0,  # Copy-paste augmentation
        # Mac-specific optimizations
        workers=8 if platform.system() == "Darwin" else 8,  # M4 Pro can handle more workers
        amp=False if device == "mps" else True,  # Disable AMP for MPS
        # Other settings
        cos_lr=True,  # Cosine learning rate scheduler
        close_mosaic=10,  # Disable mosaic augmentation in last N epochs
    )

    print(f"\n{'='*60}")
    print("TRAINING COMPLETED")
    print(f"{'='*60}")
    print(f"Best model saved to: {PROJECT_NAME}/{RUN_NAME}/weights/best.pt")
    print(f"Last model saved to: {PROJECT_NAME}/{RUN_NAME}/weights/last.pt")
    print(f"Results saved to: {PROJECT_NAME}/{RUN_NAME}")
    print(f"{'='*60}\n")

    return results


def validate_model(model_path, data_path, device):
    """Validate the trained model"""
    print(f"\n{'='*60}")
    print("VALIDATING MODEL")
    print(f"{'='*60}\n")

    model = YOLO(model_path)
    metrics = model.val(data=data_path, device=device)

    print(f"\nValidation Results:")
    print(f"  mAP50: {metrics.box.map50:.4f}")
    print(f"  mAP50-95: {metrics.box.map:.4f}")
    print(f"{'='*60}\n")

    return metrics


def print_usage_guide(model_path):
    """Print guide for using the trained model"""
    print(f"\n{'='*60}")
    print("HOW TO USE YOUR TRAINED MODEL")
    print(f"{'='*60}\n")

    print(f"Your unified model can detect all military objects and persons!")
    print(f"\nModel location: {model_path}\n")

    print("Python usage:")
    print("```python")
    print("from ultralytics import YOLO")
    print()
    print(f"# Load your trained model")
    print(f"model = YOLO('{model_path}')")
    print()
    print("# Run inference on image")
    print("results = model('path/to/image.jpg')")
    print()
    print("# Display results")
    print("results[0].show()")
    print()
    print("# Get predictions")
    print("for result in results:")
    print("    boxes = result.boxes  # Bounding boxes")
    print("    for box in boxes:")
    print("        cls_id = int(box.cls[0])")
    print("        conf = float(box.conf[0])")
    print("        class_name = result.names[cls_id]")
    print("        print(f'Detected {class_name} with confidence {conf:.2f}')")
    print("```")

    print("\nCommand line usage:")
    print(f"```bash")
    print(f"yolo detect predict model={model_path} source=path/to/image.jpg")
    print("```")

    print(f"\n{'='*60}\n")


def main():
    """Main training pipeline"""

    print(f"\n{'='*80}")
    print("YOLOV8 UNIFIED MILITARY DETECTOR TRAINING")
    print(f"{'='*80}\n")

    # Check if merged dataset exists
    if not os.path.exists(MERGED_DATASET):
        print(f"❌ Error: Merged dataset not found at {MERGED_DATASET}")
        print(f"\nPlease run 'python merge_datasets.py' first to create the merged dataset.")
        return

    # Check system
    device = check_system()

    # Print dataset info
    print_dataset_info(MERGED_DATASET)

    # Train model
    results = train_model(MERGED_DATASET, device)

    # Validate model
    best_model_path = f"{PROJECT_NAME}/{RUN_NAME}/weights/best.pt"
    validate_model(best_model_path, MERGED_DATASET, device)

    # Print usage guide
    print_usage_guide(best_model_path)

    print(f"\n{'='*60}")
    print("MAC PERFORMANCE NOTES")
    print(f"{'='*60}")
    print("""
Training Performance on Mac:
- M1/M2/M3 Mac with MPS: ~50-150 images/second
- Expected training time: 4-10 hours (depends on dataset size and Mac model)
- Memory usage: ~8-12 GB (adjust BATCH_SIZE if needed)

Tips:
1. Monitor Activity Monitor during training
2. Reduce BATCH_SIZE to 8 if you get OOM (Out of Memory) errors
3. Keep your Mac plugged in and well-ventilated
4. Close other applications to free up memory
5. Training will pause/resume if interrupted (use last.pt)

To resume training if interrupted:
    model = YOLO('{PROJECT_NAME}/{RUN_NAME}/weights/last.pt')
    model.train(resume=True)
    """)
    print(f"{'='*60}\n")

    print("✅ Training pipeline completed successfully!")


if __name__ == "__main__":
    # Change to training directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    main()
