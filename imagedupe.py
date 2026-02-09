import os
import json
import shutil
import imagehash
from PIL import Image
import pillow_heif
import click
import logging
import time

# Increase the pixel limit to 200 million pixels (200MP)
Image.MAX_IMAGE_PIXELS = 200000000

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache file to store precomputed pHashes
CACHE_FILE = "phash_cache.json"

# Register HEIF format to support HEIC files
pillow_heif.register_heif_opener()

# List of valid image file extensions
VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.heic', '.heif', '.webp'}


def is_image_file(file_path):
    """Check if the file is an image based on its extension."""
    _, ext = os.path.splitext(file_path.lower())
    return ext in VALID_IMAGE_EXTENSIONS


def load_cache(cache_file):
    """Load the pHash cache from a JSON file."""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            return {k: (v["hash"], v["mtime"]) for k, v in data.items()}
        except (json.JSONDecodeError, KeyError, TypeError):
            logging.warning(f"Cache file {cache_file} is corrupt, starting fresh.")
            return {}
    return {}


def save_cache(cache, cache_file):
    """Save the pHash cache to a JSON file."""
    data = {k: {"hash": v[0], "mtime": v[1]} for k, v in cache.items()}
    with open(cache_file, 'w') as f:
        json.dump(data, f)


def calculate_phash(image_path):
    """Calculate the perceptual hash of an image. Returns (hash_string, mtime) or None on failure."""
    try:
        mtime = os.path.getmtime(image_path)
        with Image.open(image_path) as img:
            return str(imagehash.phash(img)), mtime
    except Exception as e:
        logging.error(f"Error calculating pHash for {image_path}: {e}")
        return None


def find_duplicates(directory, cache, threshold=0):
    """Scan directory for duplicate images based on pHash.

    Returns (duplicates_dict, stats) where stats contains counters.
    """
    hash_groups = {}
    scanned = 0
    corrupt_files = []
    start_time = time.time()

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if not is_image_file(file_path):
                continue

            scanned += 1
            cached = cache.get(file_path)
            if cached:
                cached_hash, cached_mtime = cached
                try:
                    current_mtime = os.path.getmtime(file_path)
                except OSError:
                    continue
                if current_mtime == cached_mtime:
                    phash_str = cached_hash
                else:
                    result = calculate_phash(file_path)
                    if result:
                        phash_str, _ = result
                        cache[file_path] = result
                    else:
                        corrupt_files.append(file_path)
                        continue
            else:
                result = calculate_phash(file_path)
                if result:
                    phash_str, _ = result
                    cache[file_path] = result
                else:
                    corrupt_files.append(file_path)
                    continue

            if threshold == 0:
                # Exact match: group by hash string directly
                if phash_str in hash_groups:
                    hash_groups[phash_str].append(file_path)
                else:
                    hash_groups[phash_str] = [file_path]
            else:
                # Fuzzy match: check Hamming distance against existing groups
                phash_obj = imagehash.hex_to_hash(phash_str)
                matched = False
                for group_hash_str in list(hash_groups.keys()):
                    group_hash = imagehash.hex_to_hash(group_hash_str)
                    if phash_obj - group_hash <= threshold:
                        hash_groups[group_hash_str].append(file_path)
                        matched = True
                        break
                if not matched:
                    hash_groups[phash_str] = [file_path]

        elapsed_time = time.time() - start_time
        scan_rate = scanned / elapsed_time if elapsed_time > 0 else 0
        logging.info(f"Scanned {scanned} images so far ({scan_rate:.2f} images/second).")

    # Filter to only groups with actual duplicates
    duplicates = {k: v for k, v in hash_groups.items() if len(v) > 1}

    elapsed_time = time.time() - start_time
    scan_rate = scanned / elapsed_time if elapsed_time > 0 else 0
    logging.info(f"Completed scanning {scanned} images in {elapsed_time:.2f} seconds "
                 f"({scan_rate:.2f} images/second).")

    stats = {
        "scanned": scanned,
        "corrupt_files": corrupt_files,
    }
    return duplicates, stats


def handle_duplicates(duplicates, action, destination=None, base_directory=None):
    """Process duplicate sets according to the chosen action. Returns count of duplicates."""
    duplicate_count = 0
    for phash, files in duplicates.items():
        duplicate_count += len(files) - 1
        logging.info(f"\nFound duplicates for pHash {phash}:")
        for file in files:
            logging.info(f"  - {file}")

        # Compare resolutions and determine which file to keep
        highest_res = -1
        to_keep = None
        to_remove = []

        for file in files:
            try:
                with Image.open(file) as img:
                    res = img.width * img.height
                if res > highest_res:
                    highest_res = res
                    if to_keep:
                        to_remove.append(to_keep)
                    to_keep = file
                else:
                    to_remove.append(file)
            except Exception as e:
                logging.warning(f"Could not open {file} for resolution comparison: {e}")
                if action == "delete":
                    logging.warning(f"  * Skipping unreadable file (will not delete): {file}")
                else:
                    to_remove.append(file)

        for file in to_remove:
            if action == "list":
                logging.info(f"  * Suggested to remove: {file}")
            elif action == "delete":
                try:
                    os.remove(file)
                    logging.info(f"  * Deleted: {file}")
                except Exception as e:
                    logging.error(f"  * Error deleting {file}: {e}")
            elif action == "move" and destination:
                try:
                    relative_path = os.path.relpath(file, base_directory)
                    new_path = os.path.join(destination, relative_path)
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    shutil.move(file, new_path)
                    logging.info(f"  * Moved {file} to {new_path}")
                except Exception as e:
                    logging.error(f"  * Error moving {file}: {e}")

    return duplicate_count


@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--action', type=click.Choice(['list', 'delete', 'move']), default='list',
              help="Action to take with duplicates.")
@click.option('--destination', default=None,
              help="Destination directory if moving duplicates.")
@click.option('--threshold', default=0, type=int,
              help="Hamming distance threshold for pHash comparison (0 = exact match).")
@click.option('--report-corrupt', is_flag=True,
              help="Report corrupt image files.")
@click.option('--yes', '-y', is_flag=True,
              help="Skip confirmation prompt for delete action.")
def main(directory, action, destination, threshold, report_corrupt, yes):
    """
    Scan a directory for duplicate images based on pHash and handle them accordingly.
    """
    if action == "move" and not destination:
        logging.error("Destination directory must be specified when using the 'move' action.")
        return

    cache_file = os.path.join(directory, CACHE_FILE)
    cache = load_cache(cache_file)
    duplicates, stats = find_duplicates(directory, cache, threshold=threshold)
    save_cache(cache, cache_file)

    if duplicates:
        if action == "delete" and not yes:
            total = sum(len(v) - 1 for v in duplicates.values())
            if not click.confirm(f"This will permanently delete {total} duplicate file(s). Continue?"):
                logging.info("Aborted.")
                return

        duplicate_count = handle_duplicates(duplicates, action, destination, base_directory=directory)
    else:
        logging.info("No duplicates found.")
        duplicate_count = 0

    # Summary
    logging.info("\n--- Summary ---")
    logging.info(f"Total images scanned: {stats['scanned']}")
    logging.info(f"Duplicate images found: {duplicate_count}")
    logging.info(f"Corrupt images found: {len(stats['corrupt_files'])}")

    if report_corrupt and stats['corrupt_files']:
        logging.info("\nThe following files were corrupt and skipped:")
        for file in stats['corrupt_files']:
            logging.info(f" - {file}")


if __name__ == "__main__":
    main()
