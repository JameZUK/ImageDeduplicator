Key Changes:

    Preserving Directory Structure:
        The handle_duplicates() function now uses os.path.relpath() to compute the relative path from the base directory. When moving a file, it recreates the full directory structure in the destination directory.

    New Argument base_directory:
        The base_directory is passed to handle_duplicates() so that the relative path of each file can be determined and preserved when moved.

    Directory Creation:
        The os.makedirs() call ensures that the target directory (in the destination) is created if it doesn’t already exist.

    HEIC Support:
        The script includes HEIC file handling using pillow-heif.

Example Usage:

    List duplicates:

    bash

python find_duplicates.py /path/to/images --action list

Move duplicates to another directory and preserve directory structure:

bash

python find_duplicates.py /path/to/images --action move --destination /path/to/destination

Delete duplicates:

bash

python find_duplicates.py /path/to/images --action delete
