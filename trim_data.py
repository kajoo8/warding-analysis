import json
import os
import sys
from pathlib import Path


def trim_file(filepath: Path) -> tuple[int, int]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    size_before = filepath.stat().st_size

    trimmed = {
        'player_info': data.get('player_info'),
        'match_info':  data.get('match_info'),
        'match_data': {
            'metadata': data.get('match_data', {}).get('metadata'),
            'info': {
                k: v for k, v in data.get('match_data', {}).get('info', {}).items()
                if k == 'participants'
            }
        },
        'vision_data': data.get('vision_data'),
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(trimmed, f, indent=2, ensure_ascii=False)

    size_after = filepath.stat().st_size
    return size_before, size_after


def trim_folder(folder: str):
    folder_path = Path(folder)

    if not folder_path.exists():
        print(f"Folder not found: {folder}")
        sys.exit(1)

    files = list(folder_path.glob('*.json'))
    if not files:
        print(f"No JSON files found in {folder}")
        return

    total_before = total_after = 0

    for i, filepath in enumerate(files, 1):
        before, after = trim_file(filepath)
        total_before += before
        total_after += after
        saved_pct = (1 - after / before) * 100 if before else 0
        print(f"[{i}/{len(files)}] {filepath.name}: {before//1024} KB → {after//1024} KB  (-{saved_pct:.0f}%)")

    print(f"\nTotal: {total_before//1024//1024} MB → {total_after//1024//1024} MB  "
          f"(saved {(total_before - total_after)//1024//1024} MB, "
          f"-{(1 - total_after/total_before)*100:.0f}%)")


if __name__ == '__main__':
    folder = sys.argv[1] if len(sys.argv) > 1 else input("Folder path: ").strip()
    trim_folder(folder)
