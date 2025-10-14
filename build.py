from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import is_zipfile, ZipFile, ZIP_DEFLATED

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
                if relative_path.full_match(glob):
                    excluded = True
                    break
            
            if not excluded:
                yield filepath        

def add_files_into_zipfile(files: Iterable[Path], zipfile: ZipFile, package_tld: Path):
    '''
    Add a list of files into a ZipFile,
    compiling scripts to .pyc.

    Args:
        files: Paths to files which are all contained in package_tld.
        zipfile: ZipFile opened in a mode which allows append.
        package_tld: Path to package's top-level-directory.
    '''
    assert zipfile.mode in ('w', 'x', 'a')

    for filepath in files:
        assert filepath.exists()
        zipfile.write(filepath, arcname=filepath.relative_to(package_tld))

if __name__ == "__main__":
    top_level_dir_path = get_top_level_dir()
    assert not is_zipfile(top_level_dir_path), \
        "Trying to build from already-packaged zip file"

    included_files = children_excluding_globs(top_level_dir_path, ignore_globs)

    # create dist/
    output_dir = top_level_dir_path.joinpath("dist/")
    output_dir.mkdir(exist_ok=True)

    # create zipfile elsewhere, then move to dest location
    with TemporaryDirectory() as tmp_dir_path:
        tmp_zip_path = Path(tmp_dir_path).joinpath("archive.zip")
        assert not tmp_zip_path.exists()
        
        # create zipfile
        with ZipFile(
            str(tmp_zip_path),
            'x',                        # 'x' = must be creating new
            compression=ZIP_DEFLATED,   # shrink files, but guarantee unzip support on Windows
        ) as zipfile:
            add_files_into_zipfile(included_files, zipfile, top_level_dir_path)

        # move zipfile inside dist/
        program_name = top_level_dir_path.name
        dest_zip_path = output_dir.joinpath(f"{program_name}.pyz")
        tmp_zip_path.replace(dest_zip_path)

    print(f"Created file at {dest_zip_path}")
    print( "Run using: `python [filepath]`")