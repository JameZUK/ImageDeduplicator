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
* **Fuzzy Matching:** Configurable Hamming distance threshold to catch near-duplicates that differ slightly.
* **Multiple Format Support:** Handles common image formats including JPG, PNG, GIF, BMP, TIFF, WebP, and **HEIC/HEIF**.
* **Configurable Actions:**
    * `list`: Identifies and lists duplicate sets.
    * `delete`: Deletes lower-resolution duplicates (with confirmation prompt).
    * `move`: Moves lower-resolution duplicates to a specified directory, preserving relative path structure.
* **Keeps Highest Resolution:** When duplicates are found, the script defaults to keeping the image with the largest pixel area (width \* height).
* **Smart Caching:** Saves computed pHashes to a JSON cache file with modification-time tracking to detect changed files.
* **Corrupt File Reporting:** Identifies and can report images that cannot be opened or processed.
* **Large Image Support:** Configured to handle images up to 200 Megapixels.
* **User-Friendly CLI:** Built with `click` for clear command-line arguments and help.
* **Progress Indication:** Logs progress during the scan, including scan rate.

## How it Works

1.  **Directory Scan:** The script recursively scans the specified input directory for image files based on their extensions.
2.  **pHash Calculation:** For each valid image file:
    * It first checks if the image's pHash is already in the cache and the file hasn't been modified since caching.
    * If not cached or modified, it opens the image, calculates its perceptual hash (pHash), and stores it in the cache.
    * Corrupt or unreadable images are logged and skipped.
3.  **Duplicate Identification:** Images are grouped by their pHashes. With `--threshold 0` (default), only exact pHash matches are grouped. With a higher threshold, images within the specified Hamming distance are grouped together.
4.  **Resolution Comparison:** Within each duplicate set, the script compares the resolutions (width x height) of the images.
5.  **Action Execution:** Based on the chosen action (`list`, `delete`, `move`):
    * **List:** Prints the identified duplicate sets and indicates which files are candidates for removal (i.e., not the highest resolution).
    * **Delete:** Deletes all images in a duplicate set except for the one with the highest resolution. Requires confirmation unless `--yes` is passed.
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
    cd ImageDeduplicator
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The script is run from the command line.

```bash
python imagedupe.py <DIRECTORY> [OPTIONS]
```

### Command-Line Options

* `DIRECTORY`: (Required) The path to the directory you want to scan for duplicate images.
* `--action [list|delete|move]`:
    * `list` (default): Lists duplicate image sets and suggests which files to remove.
    * `delete`: Deletes the identified lower-resolution duplicate images. **Prompts for confirmation** unless `--yes` is passed.
    * `move`: Moves the identified lower-resolution duplicate images to the directory specified by `--destination`.
* `--destination <PATH>`:
    * Required if `action` is `move`. Specifies the directory where lower-resolution duplicates will be moved.
* `--threshold <INT>`:
    * Hamming distance threshold for pHash comparison. Default is `0` (exact match only). Higher values (e.g., `4-8`) will catch more visually similar images but may produce false positives.
* `--report-corrupt`:
    * If set, lists all files that were found to be corrupt or unreadable during the scan.
* `--yes` / `-y`:
    * Skip the confirmation prompt when using `--action delete`.
* `--help`:
    * Shows the help message and exits.

### Examples

1.  **List duplicates in `/path/to/your/photos`:**
    ```bash
    python imagedupe.py /path/to/your/photos
    ```
    Or explicitly:
    ```bash
    python imagedupe.py /path/to/your/photos --action list
    ```

2.  **Find near-duplicates with a Hamming distance threshold of 4:**
    ```bash
    python imagedupe.py /path/to/your/photos --threshold 4
    ```

3.  **Delete lower-resolution duplicates in `/path/to/your/photos`:**
    ```bash
    # This will prompt for confirmation before deleting.
    # It's recommended to run with --action list first.
    python imagedupe.py /path/to/your/photos --action delete
    ```

4.  **Delete duplicates without confirmation (for scripting):**
    ```bash
    python imagedupe.py /path/to/your/photos --action delete --yes
    ```

5.  **Move lower-resolution duplicates from `/path/to/your/photos` to `/path/to/duplicates_backup`:**
    ```bash
    python imagedupe.py /path/to/your/photos --action move --destination /path/to/duplicates_backup
    ```
    If a file `/path/to/your/photos/subdir/duplicate.jpg` is moved, it will be placed at `/path/to/duplicates_backup/subdir/duplicate.jpg`.

6.  **List duplicates and report any corrupt image files found:**
    ```bash
    python imagedupe.py /path/to/your/photos --report-corrupt
    ```

## The Cache

* The script creates a cache file named `phash_cache.json` inside the scanned directory.
* This file stores the perceptual hashes and file modification times of images that have already been processed.
* On subsequent runs, if an image path is found in the cache **and its modification time hasn't changed**, the cached pHash is used directly, significantly speeding up scans.
* If a file has been modified since it was last cached, its hash is automatically recalculated.
* To force a full rescan, you can delete `phash_cache.json` before running the script.

## Handling Corrupt Files

* The script attempts to open and process each image. If an image file is corrupt or not a valid image format that Pillow can understand (even with `pillow_heif`), an error will be logged.
* These files are added to a list of corrupt files.
* If you use the `--report-corrupt` flag, this list will be printed at the end of the script's execution.
* Corrupt files are skipped and do not interfere with the processing of other images.
* When using `--action delete`, files that cannot be opened for resolution comparison are **not** deleted as a safety measure.

## HEIC/HEIF Support

The script includes support for `.heic` and `.heif` (High Efficiency Image Container/Format) files, commonly used by Apple devices. This is enabled by the `pillow_heif` library, which registers the HEIF opener with Pillow.

## Important Considerations

* **Backup Your Data:** Before using the `delete` action, it is **strongly recommended** to back up your image directory. Data loss due to accidental deletion is irreversible. Run with `list` first to review.
* **Cache Staleness:** The cache tracks file modification times. If a file is modified, its hash is automatically recalculated on the next run.
* **pHash Limitations:** Perceptual hashing is powerful but not infallible.
    * Extremely similar but distinct images might occasionally produce the same pHash.
    * Conversely, images that a human considers duplicates but have undergone significant transformations (e.g., major crops, artistic filters, large overlays) might have different pHashes.
    * With `--threshold 0`, only images with *identical* pHashes are considered duplicates. Use a higher threshold to catch near-duplicates.
* **Tie-Breaking:** If multiple duplicate images share the same highest resolution, the script will keep one of them based on iteration order; the others will be marked for removal/moving.
* **Performance:** For very large collections (hundreds of thousands of images), the initial scan can take a significant amount of time. Subsequent scans will be much faster due to caching. When using `--threshold` > 0, duplicate detection is O(n*g) where g is the number of hash groups, which is slower than exact matching.

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
