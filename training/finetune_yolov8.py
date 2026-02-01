"""
YOLOv8 Medium Fine-tuning Script for Military Datasets
Supports training on multiple datasets with Mac (MPS) compatibility
"""

import os
import yaml
import platform
from pathlib import Path
from ultralytics import YOLO
import torch

# Configuration
DATASETS = [
    "datasets/Military.v1i.yolov8/data.yaml",
    "datasets/DRONES_NEW.v4i.yolov8/data.yaml",
    "datasets/vehicles.v2i.yolov8/data.yaml",
    "datasets/Drone Human detection.v8i.yolov8/data.yaml",
    "datasets/Drone human.v1i.yolov8/data.yaml",
    "datasets/Drone human.v1i.yolov8 2/data.yaml",
    "datasets/Human Detection Through Drone.v1i.yolov8/data.yaml",
    "datasets/Human detection from a drone.v1i.yolov8/data.yaml",
]

# Training hyperparameters
EPOCHS = 100
BATCH_SIZE = 16  # Adjust based on your Mac's memory
IMG_SIZE = 640
PATIENCE = 20  # Early stopping patience
DEVICE = None  # Will be auto-detected

# Output directories
PROJECT_NAME = "military_detection"
RUNS_DIR = "runs/detect"


def check_system():
    """Check system capabilities and return appropriate device"""
    print(f"\n{'='*60}")
    print("SYSTEM INFORMATION")
    print(f"{'='*60}")
    print(f"Platform: {platform.system()}")
    print(f"Processor: {platform.processor()}")
    print(f"Python Version: {platform.python_version()}")

    # Check PyTorch and device availability
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
        device = "0"  # CUDA GPU
        print(f"✓ CUDA GPU available: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        print(f"⚠ Using CPU for training")

    print(f"{'='*60}\n")
    return device


def validate_dataset(dataset_path):
    """Validate that dataset exists and has proper structure"""
    if not os.path.exists(dataset_path):
        print(f"✗ Dataset not found: {dataset_path}")
        return False

    with open(dataset_path, 'r') as f:
        data = yaml.safe_load(f)

    dataset_dir = os.path.dirname(dataset_path)

    # Check for train, val directories
    train_path = os.path.join(dataset_dir, data.get('train', ''))
    val_path = os.path.join(dataset_dir, data.get('val', ''))

    if not os.path.exists(train_path):
        print(f"✗ Training images not found for {dataset_path}")
        return False

    if not os.path.exists(val_path):
        print(f"✗ Validation images not found for {dataset_path}")
        return False

    print(f"✓ Dataset valid: {os.path.basename(os.path.dirname(dataset_path))}")
    print(f"  Classes ({data['nc']}): {data['names']}")

    return True


def merge_datasets(dataset_paths):
    """
    Create a merged data.yaml combining all datasets
    Note: This creates a unified class list across all datasets
    """
    all_classes = []
    class_mapping = {}

    print(f"\n{'='*60}")
    print("MERGING DATASETS")
    print(f"{'='*60}")

    for dataset_path in dataset_paths:
        with open(dataset_path, 'r') as f:
            data = yaml.safe_load(f)

        dataset_name = os.path.basename(os.path.dirname(dataset_path))

        for cls in data['names']:
            if cls not in all_classes:
                all_classes.append(cls)

        class_mapping[dataset_name] = data['names']

    print(f"Total unique classes: {len(all_classes)}")
    print(f"Classes: {all_classes}\n")

    # Create merged data.yaml
    merged_config = {
        'path': '../datasets',  # Base path
        'train': [],
        'val': [],
        'test': [],
        'nc': len(all_classes),
        'names': all_classes
    }

    # Note: For actual merged training, you'd need to combine the datasets
    # and remap class indices. For now, we'll train on each separately.

    return all_classes


def train_on_dataset(dataset_path, device, model_path=None):
    """Train YOLOv8 on a single dataset"""

    dataset_name = os.path.basename(os.path.dirname(dataset_path))

    print(f"\n{'='*60}")
    print(f"TRAINING ON: {dataset_name}")
    print(f"{'='*60}\n")

    # Load model
    if model_path and os.path.exists(model_path):
        print(f"Loading previous model from: {model_path}")
        model = YOLO(model_path)
    else:
        print(f"Loading YOLOv8 Medium pretrained model")
        model = YOLO('yolov8m.pt')

    # Train
    results = model.train(
        data=dataset_path,
        epochs=EPOCHS,
        batch=BATCH_SIZE,
        imgsz=IMG_SIZE,
        device=device,
        project=PROJECT_NAME,
        name=dataset_name,
        patience=PATIENCE,
        save=True,
        save_period=10,  # Save checkpoint every 10 epochs
        plots=True,
        verbose=True,
        # Mac-specific optimizations
        workers=4 if platform.system() == "Darwin" else 8,
        amp=False if device == "mps" else True,  # Disable AMP for MPS
    )

    print(f"\n✓ Training completed for {dataset_name}")
    print(f"  Best model saved to: {results.save_dir}/weights/best.pt")

    return results, f"{PROJECT_NAME}/{dataset_name}/weights/best.pt"


def train_sequentially(dataset_paths, device):
    """Train on each dataset sequentially, optionally using transfer learning"""

    print(f"\n{'='*60}")
    print("SEQUENTIAL TRAINING MODE")
    print(f"{'='*60}")
    print("Will train on each dataset separately")
    print("Each model will be saved independently\n")

    results = {}

    for i, dataset_path in enumerate(dataset_paths, 1):
        dataset_name = os.path.basename(os.path.dirname(dataset_path))

        print(f"\n[{i}/{len(dataset_paths)}] Processing: {dataset_name}")

        # Train on this dataset
        result, model_path = train_on_dataset(dataset_path, device)
        results[dataset_name] = {
            'model_path': model_path,
            'metrics': result
        }

    return results


def print_summary(results):
    """Print training summary"""
    print(f"\n{'='*60}")
    print("TRAINING SUMMARY")
    print(f"{'='*60}\n")

    for dataset_name, info in results.items():
        print(f"Dataset: {dataset_name}")
        print(f"  Model: {info['model_path']}")
        print()


def main():
    """Main training pipeline"""

    print(f"\n{'='*60}")
    print("YOLOV8 MEDIUM FINE-TUNING SCRIPT")
    print(f"{'='*60}\n")

    # Check system capabilities
    device = check_system()

    # Validate datasets
    print(f"\n{'='*60}")
    print("VALIDATING DATASETS")
    print(f"{'='*60}\n")

    valid_datasets = []
    for dataset in DATASETS:
        full_path = os.path.join("training", dataset)
        if validate_dataset(full_path):
            valid_datasets.append(full_path)

    if not valid_datasets:
        print("\n✗ No valid datasets found!")
        return

    print(f"\n✓ Found {len(valid_datasets)} valid datasets")

    # Analyze all classes
    merge_datasets(valid_datasets)

    # Train on each dataset
    results = train_sequentially(valid_datasets, device)

    # Print summary
    print_summary(results)

    print(f"\n{'='*60}")
    print("MAC COMPATIBILITY NOTES")
    print(f"{'='*60}")
    print("""
Your Mac setup:
- YOLOv8 will use MPS (Metal Performance Shaders) if available on M1/M2/M3 Macs
- Training will be slower than NVIDIA GPUs but much faster than CPU
- Batch size of 16 should work, but reduce to 8 if you get memory errors
- Expect training to take several hours per dataset

Recommendations:
1. Monitor Activity Monitor for memory usage
2. Close other applications during training
3. Ensure your Mac is plugged in (not on battery)
4. Consider using smaller batch sizes if training is unstable
5. For faster training, consider using cloud GPUs (Google Colab, AWS, etc.)

Performance expectations (M1/M2/M3 Mac):
- Training speed: ~50-150 images/second (depends on Mac model)
- Time per dataset: 2-6 hours (100 epochs, ~1000 images)
- Total time for all datasets: ~12-24 hours
    """)
    print(f"{'='*60}\n")

    print("✓ All training completed successfully!")


if __name__ == "__main__":
    # Change to training directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    main()
