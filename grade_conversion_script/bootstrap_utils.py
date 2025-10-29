'''
Tools which must be available early on, before importing unrelated packages.
'''

def get_top_level_dir():
    '''
    Points to top-level of package, not repository.

    Note: might point to a zip file.
    '''
    from pathlib import Path
    from zipfile import ZipFile, is_zipfile

    bootstrap_module = Path(__file__)
    top_level_dir = bootstrap_module.parent
    
    if is_zipfile(top_level_dir):
        with ZipFile(top_level_dir, 'r') as top_level_zip:
            paths_from_top_level = top_level_zip.namelist()
            assert "__main__.py" in paths_from_top_level
    else:
        top_level_files = (
            path.name
            for path in top_level_dir.iterdir() # iterdir is non-recursive
        )
        assert "__main__.py" in top_level_files

    return top_level_dir

def get_pkg_dependencies():
    '''
    Only works if dependencies are defined in `pyproject.toml`.
    '''
    import tomllib
    from zipfile import ZipFile, is_zipfile

    # Read contents of pyproject.toml
    top_level_dir_path = get_top_level_dir()
    pyproject_toml_filename = "pyproject.toml"
    if is_zipfile(top_level_dir_path):
        with (
            ZipFile(top_level_dir_path, 'r')
                as top_level_zip,
            top_level_zip.open(pyproject_toml_filename)
                as toml_file
        ):
            pyproject_toml = tomllib.load(toml_file)
    else:
        pyproject_toml_path = top_level_dir_path.joinpath(pyproject_toml_filename)
        if not pyproject_toml_path.is_file():
            pyproject_toml_path = top_level_dir_path.parent.joinpath(pyproject_toml_filename)
            if not pyproject_toml_path.is_file():
                raise FileNotFoundError(f"Could not find pyproject.toml.")
        with open(pyproject_toml_path, "rb") as toml_file:
            pyproject_toml = tomllib.load(toml_file)

    # Get dependencies
    project_table = pyproject_toml["project"]
    dependencies: list[str] = project_table["dependencies"]

    return dependencies

def ensure_pkg_dependencies():
    '''
    Insure this package's dependencies are installed,
    using data from top-level `pyproject.toml`.
    '''
    from importlib import import_module

    if "pyproject.toml" not in (
        path.name
        for path in get_top_level_dir().iterdir()  # iterdir is non-recursive
    ):
        # built wheels might not include this file
        return
    
    dependencies = get_pkg_dependencies()

    # Try importing each, check if unavailable
    for dependency in dependencies:
        try:
            import_module(dependency)
        except ModuleNotFoundError as e:
            missing_module = e.name
            e.msg += (f"\n\n"
                      f"Try installing the dependency:"
                      f" python -m pip install {missing_module}")
            raise e