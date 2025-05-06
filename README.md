# Duplicate Image Finder (pHash)

A Python command-line tool to find and manage duplicate or visually similar images within a directory. It uses perceptual hashing (pHash) to identify duplicates, which allows it to find images that are the same even if they have different file formats, resolutions, or minor edits. The script prioritizes keeping the image with the highest resolution when duplicates are found.

## Table of Contents

- [Key Features](#key-features)
- [How it Works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [Command-Line Options](#command-line-options)
  - [Examples](#examples)
- [The Cache](#the-cache)
- [Handling Corrupt Files](#handling-corrupt-files)
- [HEIC/HEIF Support](#heicheif-support)
- [Important Considerations](#important-considerations)
- [Contributing](#contributing)
- [License](#license)

## Key Features

* **Perceptual Hashing:** Uses `imagehash.phash` to find visually similar images, not just exact file duplicates.
* **Multiple Format Support:** Handles common image formats including JPG, PNG, GIF, BMP, TIFF, WebP, and **HEIC/HEIF**.
* **Configurable Actions:**
    * `list`: Identifies and lists duplicate sets.
    * `delete`: Deletes lower-resolution duplicates.
    * `move`: Moves lower-resolution duplicates to a specified directory, preserving relative path structure.
* **Keeps Highest Resolution:** When duplicates are found, the script defaults to keeping the image with the largest pixel area (width \* height).
* **Caching System:** Saves computed pHashes to a cache file (`phash_cache.pkl`) to significantly speed up subsequent scans of the same directory.
* **Corrupt File Reporting:** Identifies and can report images that cannot be opened or processed.
* **Large Image Support:** Configured to handle images up to 200 Megapixels.
* **User-Friendly CLI:** Built with `click` for clear command-line arguments and help.
* **Progress Indication:** Logs progress during the scan, including scan rate.

## How it Works

1.  **Directory Scan:** The script recursively scans the specified input directory for image files based on their extensions.
2.  **pHash Calculation:** For each valid image file:
    * It first checks if the image's pHash is already in the cache.
    * If not cached, it opens the image, calculates its perceptual hash (pHash), and stores it in the cache.
    * Corrupt or unreadable images are logged and skipped.
3.  **Duplicate Identification:** Images are grouped by their pHashes. If multiple images share the same pHash, they are considered a duplicate set.
4.  **Resolution Comparison:** Within each duplicate set, the script compares the resolutions (width x height) of the images.
5.  **Action Execution:** Based on the chosen action (`list`, `delete`, `move`):
    * **List:** Prints the identified duplicate sets and indicates which files are candidates for removal (i.e., not the highest resolution).
    * **Delete:** Deletes all images in a duplicate set except for the one with the highest resolution.
    * **Move:** Moves all images in a duplicate set (except the highest resolution one) to a specified destination directory. The original directory structure relative to the input directory is recreated within the destination directory for the moved files.
6.  **Summary Report:** After processing, a summary is displayed showing total images scanned, duplicates found, and corrupt images encountered.

## Requirements

* Python 3.7+
* The following Python libraries:
    * `Pillow` (PIL Fork)
    * `imagehash`
    * `pillow_heif` (for HEIC/HEIF support)
    * `click`

## Installation

1.  **Clone the repository (or download the script):**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
    Or, simply save the script as `duplicate_image_finder.py`.

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    Create a `requirements.txt` file with the following content:
    ```txt
    Pillow
    imagehash
    pillow_heif
    click
    ```
    Then install them:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The script is run from the command line.

```bash
python duplicate_image_finder.py <DIRECTORY> [OPTIONS]
```

### Command-Line Options

* `DIRECTORY`: (Required) The path to the directory you want to scan for duplicate images.
* `--action [list|delete|move]`:
    * `list` (default): Lists duplicate image sets and suggests which files to remove.
    * `delete`: Deletes the identified lower-resolution duplicate images. **Use with caution!**
    * `move`: Moves the identified lower-resolution duplicate images to the directory specified by `--destination`.
* `--destination <PATH>`:
    * Required if `action` is `move`. Specifies the directory where lower-resolution duplicates will be moved.
* `--report-corrupt`:
    * If set, lists all files that were found to be corrupt or unreadable during the scan.
* `--help`:
    * Shows the help message and exits.

### Examples

1.  **List duplicates in `/path/to/your/photos`:**
    ```bash
    python duplicate_image_finder.py /path/to/your/photos
    ```
    Or explicitly:
    ```bash
    python duplicate_image_finder.py /path/to/your/photos --action list
    ```

2.  **Delete lower-resolution duplicates in `/path/to/your/photos`:**
    ```bash
    # WARNING: This will permanently delete files!
    # It's highly recommended to run with --action list first.
    # Consider backing up your photos before running this.
    python duplicate_image_finder.py /path/to/your/photos --action delete
    ```

3.  **Move lower-resolution duplicates from `/path/to/your/photos` to `/path/to/duplicates_backup`:**
    ```bash
    python duplicate_image_finder.py /path/to/your/photos --action move --destination /path/to/duplicates_backup
    ```
    If a file `/path/to/your/photos/subdir/duplicate.jpg` is moved, it will be placed at `/path/to/duplicates_backup/subdir/duplicate.jpg`.

4.  **List duplicates and report any corrupt image files found:**
    ```bash
    python duplicate_image_finder.py /path/to/your/photos --report-corrupt
    ```

## The Cache

* The script creates a cache file named `phash_cache.pkl` in the directory where you run the script.
* This file stores the perceptual hashes of images that have already been processed, keyed by their file paths.
* On subsequent runs, if an image path is found in the cache, its pHash is loaded directly, significantly speeding up the scanning process, especially for large collections or repeated scans.
* If you suspect images have been modified without their paths changing, or if you want to force a full rescan, you can delete `phash_cache.pkl` before running the script.

## Handling Corrupt Files

* The script attempts to open and process each image. If an image file is corrupt or not a valid image format that Pillow can understand (even with `pillow_heif`), an error will be logged.
* These files are added to a list of corrupt files.
* If you use the `--report-corrupt` flag, this list will be printed at the end of the script's execution.
* Corrupt files are skipped and do not interfere with the processing of other images.

## HEIC/HEIF Support

The script includes support for `.heic` (High Efficiency Image Container) files, commonly used by Apple devices. This is enabled by the `pillow_heif` library, which registers the HEIF opener with Pillow.

## Important Considerations

* **Backup Your Data:** Before using the `delete` action, it is **strongly recommended** to back up your image directory. Data loss due to accidental deletion is irreversible. Run with `list` first to review.
* **Cache Staleness:** The cache uses file paths as keys. If an image file is replaced or significantly modified *without its path changing*, the cache will return the old pHash. For a full, fresh scan, delete `phash_cache.pkl`.
* **pHash Limitations:** Perceptual hashing is powerful but not infallible.
    * Extremely similar but distinct images might occasionally produce the same pHash.
    * Conversely, images that a human considers duplicates but have undergone significant transformations (e.g., major crops, artistic filters, large overlays) might have different pHashes.
    * This script considers images with *identical* pHashes as duplicates.
* **Tie-Breaking:** If multiple duplicate images share the same highest resolution, the script will keep one of them based on iteration order; the others will be marked for removal/moving. This is generally consistent but not guaranteed to be the "oldest" or "first alphabetically" among those tie-breakers.
* **Performance:** For very large collections (hundreds of thousands of images), the initial scan can take a significant amount of time. Subsequent scans will be much faster due to caching.

## Contributing

Contributions are welcome! If you have suggestions for improvements, new features, or bug fixes, please feel free to:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/AmazingFeature`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
5.  Push to the branch (`git push origin feature/AmazingFeature`).
6.  Open a Pull Request.

Please ensure your code adheres to good Python practices and include comments where necessary.

## License

Distributed under the MIT License. See `LICENSE` file for more information.
