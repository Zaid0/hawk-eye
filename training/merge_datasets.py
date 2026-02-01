"""
Dataset Merger for YOLOv8
Merges multiple YOLO datasets with label normalization
"""

import os
import yaml
import shutil
from pathlib import Path
from collections import defaultdict
import random

# Label normalization mapping
LABEL_MAPPING = {
    # Human variations -> person
    'human': 'person',
    'humans': 'person',
    'Person': 'person',
    '-humans-people-armymodel': 'person',

    # Vehicle normalizations
    'tank': 'military_tank',
    'Military truck': 'military_truck',

    # Keep as-is (explicit for clarity)
    'drone': 'drone',
    'civilian_aircraft': 'civilian_aircraft',
    'civilian_car': 'civilian_car',
    'military_aircraft': 'military_aircraft',
    'military_helicopter': 'military_helicopter',
    'military_tank': 'military_tank',
    'military_truck': 'military_truck',
    'BMP': 'BMP',
    'Grad': 'Grad',
    'Smerch': 'Smerch',
    'Tiger': 'Tiger',
}

# Ignore these classes
IGNORE_CLASSES = ['bnik9m nm', 'undefined']

# Dataset paths
DATASET_DIRS = [
    "datasets/Military.v1i.yolov8",
    "datasets/DRONES_NEW.v4i.yolov8",
    "datasets/vehicles.v2i.yolov8",
    "datasets/Drone Human detection.v8i.yolov8",
    "datasets/Drone human.v1i.yolov8",
    "datasets/Human Detection Through Drone.v1i.yolov8",
    "datasets/Human detection from a drone.v1i.yolov8",
]

OUTPUT_DIR = "datasets/merged_military_dataset"


def get_unified_classes():
    """Get unified class list from all datasets"""
    unified_classes = set()

    for dataset_dir in DATASET_DIRS:
        yaml_path = os.path.join(dataset_dir, "data.yaml")
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        for class_name in data['names']:
            if class_name in IGNORE_CLASSES:
                continue
            normalized = LABEL_MAPPING.get(class_name, class_name)
            unified_classes.add(normalized)

    # Sort for consistent ordering
    return sorted(list(unified_classes))


def create_class_id_mapping(dataset_dir, unified_classes):
    """Create mapping from old class IDs to new unified class IDs"""
    yaml_path = os.path.join(dataset_dir, "data.yaml")
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    mapping = {}
    for old_id, class_name in enumerate(data['names']):
        if class_name in IGNORE_CLASSES:
            mapping[old_id] = None  # Mark for deletion
        else:
            normalized = LABEL_MAPPING.get(class_name, class_name)
            new_id = unified_classes.index(normalized)
            mapping[old_id] = new_id

    return mapping


def convert_label_file(input_path, output_path, class_mapping):
    """Convert a YOLO label file with new class IDs"""
    converted_lines = []

    with open(input_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue

            old_class_id = int(parts[0])

            # Skip ignored classes
            if class_mapping[old_class_id] is None:
                continue

            new_class_id = class_mapping[old_class_id]
            converted_line = f"{new_class_id} {' '.join(parts[1:])}\n"
            converted_lines.append(converted_line)

    # Only write if there are valid annotations
    if converted_lines:
        with open(output_path, 'w') as f:
            f.writelines(converted_lines)
        return True
    return False


def merge_datasets(dataset_dirs, output_dir, unified_classes):
    """Merge multiple datasets into one unified dataset"""

    print(f"\n{'='*60}")
    print("MERGING DATASETS")
    print(f"{'='*60}\n")

    # Create output directory structure
    for split in ['train', 'valid', 'test']:
        os.makedirs(os.path.join(output_dir, split, 'images'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, split, 'labels'), exist_ok=True)

    stats = defaultdict(lambda: defaultdict(int))

    for dataset_dir in dataset_dirs:
        dataset_name = os.path.basename(dataset_dir)
        print(f"Processing: {dataset_name}")

        # Get class mapping for this dataset
        class_mapping = create_class_id_mapping(dataset_dir, unified_classes)

        # Process each split
        for split in ['train', 'valid', 'test']:
            images_dir = os.path.join(dataset_dir, split, 'images')
            labels_dir = os.path.join(dataset_dir, split, 'labels')

            if not os.path.exists(images_dir):
                continue

            # Process each image and label
            image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

            for img_file in image_files:
                # Create unique filename to avoid collisions
                base_name = os.path.splitext(img_file)[0]
                ext = os.path.splitext(img_file)[1]
                new_img_name = f"{dataset_name}_{base_name}{ext}"
                new_label_name = f"{dataset_name}_{base_name}.txt"

                # Copy image
                src_img = os.path.join(images_dir, img_file)
                dst_img = os.path.join(output_dir, split, 'images', new_img_name)
                shutil.copy2(src_img, dst_img)

                # Convert and copy label
                src_label = os.path.join(labels_dir, f"{base_name}.txt")
                dst_label = os.path.join(output_dir, split, 'labels', new_label_name)

                if os.path.exists(src_label):
                    if convert_label_file(src_label, dst_label, class_mapping):
                        stats[dataset_name][split] += 1

        print(f"  ✓ {dataset_name}: {sum(stats[dataset_name].values())} images")

    # Create merged data.yaml
    merged_yaml = {
        'path': os.path.abspath(output_dir),
        'train': 'train/images',
        'val': 'valid/images',
        'test': 'test/images',
        'nc': len(unified_classes),
        'names': unified_classes
    }

    yaml_path = os.path.join(output_dir, 'data.yaml')
    with open(yaml_path, 'w') as f:
        yaml.dump(merged_yaml, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Merged dataset created at: {output_dir}")
    print(f"  Total classes: {len(unified_classes)}")
    print(f"  Classes: {unified_classes}")

    # Print statistics
    print(f"\n{'='*60}")
    print("MERGE STATISTICS")
    print(f"{'='*60}\n")

    total_stats = defaultdict(int)
    for dataset, splits in stats.items():
        for split, count in splits.items():
            total_stats[split] += count

    print(f"Train images: {total_stats['train']}")
    print(f"Valid images: {total_stats['valid']}")
    print(f"Test images: {total_stats['test']}")
    print(f"Total images: {sum(total_stats.values())}")

    return yaml_path


def main():
    print(f"\n{'='*60}")
    print("DATASET MERGER WITH LABEL NORMALIZATION")
    print(f"{'='*60}\n")

    # Get unified class list
    unified_classes = get_unified_classes()

    print(f"Unified classes ({len(unified_classes)}):")
    for i, cls in enumerate(unified_classes):
        print(f"  {i}: {cls}")

    print(f"\nLabel normalization:")
    for old, new in LABEL_MAPPING.items():
        if old != new:
            print(f"  '{old}' -> '{new}'")

    print(f"\nIgnoring classes: {IGNORE_CLASSES}")

    # Merge datasets
    merged_yaml_path = merge_datasets(DATASET_DIRS, OUTPUT_DIR, unified_classes)

    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print(f"""
1. Review the merged dataset at: {OUTPUT_DIR}

2. Train YOLOv8 on the merged dataset:
   python finetune_yolov8_merged.py

3. The unified model will detect all {len(unified_classes)} classes:
   {', '.join(unified_classes)}
    """)
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Change to training directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    main()
