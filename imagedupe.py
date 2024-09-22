import os
import shutil
import pickle
import imagehash
from PIL import Image
import pillow_heif  # Import to support HEIC
import click
import logging
import time

# Increase the pixel limit to 200 million pixels (200MP)
Image.MAX_IMAGE_PIXELS = 200000000  # Set the max pixel limit to 200MP

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache file to store precomputed pHashes
CACHE_FILE = "phash_cache.pkl"
CORRUPT_FILES = []
SCANNED_FILES = 0
DUPLICATE_FILES = 0

# Register HEIF format to support HEIC files
pillow_heif.register_heif_opener()

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            return pickle.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache, f)

def calculate_phash(image_path):
    global SCANNED_FILES
    try:
        with Image.open(image_path) as img:
            SCANNED_FILES += 1
            return imagehash.phash(img)
    except Exception as e:
        logging.error(f"Error calculating pHash for {image_path}: {e}")
        CORRUPT_FILES.append(image_path)
        return None

def compare_resolution(image1, image2):
    try:
        with Image.open(image1) as img1, Image.open(image2) as img2:
            res1 = img1.width * img1.height
            res2 = img2.width * img2.height
            return res1, res2
    except Exception as e:
        logging.error(f"Error comparing resolution: {e}")
        return None, None

def find_duplicates(directory, cache):
    duplicates = {}
    total_files = 0
    start_time = time.time()

    for root, _, files in os.walk(directory):
        for file in files:
            total_files += 1
            file_path = os.path.join(root, file)
            if file_path in cache:
                phash = cache[file_path]
            else:
                phash = calculate_phash(file_path)
                if phash:
                    cache[file_path] = phash
                else:
                    continue  # Skip files with failed pHash calculation

            # Check for duplicates
            if phash in duplicates:
                duplicates[phash].append(file_path)
            else:
                duplicates[phash] = [file_path]
        
        # Verbosity: Show progress
        elapsed_time = time.time() - start_time
        scan_rate = SCANNED_FILES / elapsed_time if elapsed_time > 0 else 0
        logging.info(f"Scanned {SCANNED_FILES} images so far ({scan_rate:.2f} images/second).")

    # Filter duplicates where there are multiple files with the same pHash
    duplicates = {k: v for k, v in duplicates.items() if len(v) > 1}
    
    elapsed_time = time.time() - start_time
    scan_rate = SCANNED_FILES / elapsed_time if elapsed_time > 0 else 0
    logging.info(f"Completed scanning {SCANNED_FILES} images in {elapsed_time:.2f} seconds "
                 f"({scan_rate:.2f} images/second).")

    return duplicates

def handle_duplicates(duplicates, action, destination=None, base_directory=None):
    global DUPLICATE_FILES
    for phash, files in duplicates.items():
        DUPLICATE_FILES += len(files) - 1  # Count duplicate files, excluding the original
        logging.info(f"\nFound duplicates for pHash {phash}:")
        for file in files:
            logging.info(f"  - {file}")

        # Compare resolutions and determine which file to remove
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
                logging.error(f"Error opening {file} for resolution comparison: {e}")
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
                    # Recreate the source directory structure in the destination
                    relative_path = os.path.relpath(file, base_directory)
                    new_path = os.path.join(destination, relative_path)

                    # Ensure the target directory exists
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    shutil.move(file, new_path)
                    logging.info(f"  * Moved {file} to {new_path}")
                except Exception as e:
                    logging.error(f"  * Error moving {file} to {new_path}: {e}")

@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False))
@click.option('--action', type=click.Choice(['list', 'delete', 'move']), default='list', help="Action to take with duplicates.")
@click.option('--destination', default=None, help="Destination directory if moving duplicates.")
@click.option('--report-corrupt', is_flag=True, help="Report corrupt image files.")
def main(directory, action, destination, report_corrupt):
    """
    Scan a directory for duplicate images based on pHash and handle them accordingly.
    """
    if action == "move" and not destination:
        logging.error("Destination directory must be specified when using the 'move' action.")
        return

    cache = load_cache()
    duplicates = find_duplicates(directory, cache)
    save_cache(cache)

    if duplicates:
        handle_duplicates(duplicates, action, destination, base_directory=directory)
    else:
        logging.info("No duplicates found.")

    # Summary
    logging.info("\n--- Summary ---")
    logging.info(f"Total images scanned: {SCANNED_FILES}")
    logging.info(f"Duplicate images found: {DUPLICATE_FILES}")
    logging.info(f"Corrupt images found: {len(CORRUPT_FILES)}")

    if report_corrupt and CORRUPT_FILES:
        logging.info("\nThe following files were corrupt and skipped:")
        for file in CORRUPT_FILES:
            logging.info(f" - {file}")

if __name__ == "__main__":
    main()
