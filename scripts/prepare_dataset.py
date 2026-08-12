from pathlib import Path

from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}

DATA_DIR = Path("data/images")
MIN_IMAGES = 8
MAX_IMAGES = 12


def main() -> None:
    folders = sorted(p for p in DATA_DIR.iterdir() if p.is_dir())
    skipped: list[Path] = []

    for folder in folders:
        animal = folder.name
        candidates = sorted(folder.iterdir())
        images: list[Path] = []

        for f in candidates:
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
                images.append(f)
            elif f.is_file():
                skipped.append(f)

        for idx, f in enumerate(images, start=1):
            new_name = f"{animal}_{idx:02d}{f.suffix.lower()}"
            new_path = f.with_name(new_name)
            if new_path != f:
                f.rename(new_path)
        if not images and not any(folder.iterdir()):
            folder.rmdir()

    _print_skip_report(skipped)
    _print_summary(folders)


def _print_skip_report(skipped: list[Path]) -> None:
    if not skipped:
        print("Non-image files found: none")
        return
    print("Non-image files skipped (not renamed):")
    for f in skipped:
        print(f"  - {f.relative_to(DATA_DIR)}")
    print()


def _print_summary(folders: list[Path]) -> None:
    print(f"{'Folder':<8} {'Count':<7} {'Failed to open':<30} Status")
    print("-" * 70)
    any_warning = False

    for folder in folders:
        files = sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )
        failed = [
            f.name
            for f in files
            if not _is_valid_image(f)
        ]
        count = len(files) - len(failed)
        if count < MIN_IMAGES or count > MAX_IMAGES:
            status = "WARNING"
            any_warning = True
        else:
            status = "ok"
        failed_str = ", ".join(failed) if failed else "-"
        print(f"{folder.name:<8} {count:<7} {failed_str:<30} {status}")

    if not any_warning:
        print("\nAll folders are within the expected 8-12 image range.")


def _is_valid_image(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img.verify()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()