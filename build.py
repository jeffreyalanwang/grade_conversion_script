from pathlib import Path
from zipfile import is_zipfile
import zipapp

from typing import Iterable

from bootstrap_utils import get_top_level_dir

'''
Build package into a distributable zip file.

This file requires Python version >= 3.13
(but not the rest of the project).
'''

# Match to paths from top-level directory
ignore_globs: list[str] = [
    ".gitignore",
    ".git/**",
    ".vscode/**",
    "**/__pycache__/**",
    "test_all.py",
    "build.py",
    "dist/**",
]

def children_excluding_globs(dir: Path, globs: list[str]) -> Iterable[Path]:
    '''
    Returns a list of all files (recursive),
    so no empty directories will be included.
    '''
    assert dir.is_dir()
    
    for curr_dir, child_dirs, child_files in dir.walk():
        for filepath_str in child_files:
            filepath = curr_dir.joinpath(filepath_str)

            excluded = False

            relative_path = filepath.relative_to(dir)
            for glob in globs:
                if relative_path.full_match(glob): # this line requires Python 3.13
                    excluded = True
                    break
            
            if not excluded:
                yield filepath

if __name__ == "__main__":

    top_level_dir_path = get_top_level_dir()

    assert not is_zipfile(top_level_dir_path), \
        "Trying to build from already-packaged zip file"

    # Generate location for file to be written
    program_name = top_level_dir_path.name
    output_dir = top_level_dir_path.joinpath("dist/")
    dest_zip_path = output_dir.joinpath(f"{program_name}.pyz")

    # Ensure write location is available
    output_dir.mkdir(exist_ok=True)
    dest_zip_path.unlink(missing_ok=True) # delete if existing

    # Create filter function
    included_files = list(children_excluding_globs(top_level_dir_path, ignore_globs))
    def included_files_only(file: Path) -> bool:
        '''
        zipapp uses this function to
        checks all files
        (including non .py files).

        Args:
            file: relative to the source directory.
        '''
        return any(
            file.samefile(included_file)
            for included_file in included_files
        )

    # Package the application
    zipapp.create_archive(
        source=top_level_dir_path,
        target=dest_zip_path,

        interpreter="/usr/bin/env python3",
        compressed=True,

        filter=included_files_only,
    )

    print(f"===================================================")
    print(f"Created file at {dest_zip_path}")
    print(f"Run using: `python [file{dest_zip_path.suffix}]`")