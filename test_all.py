import sys
from pathlib import Path
import pkgutil
from importlib import import_module

from pkgutil import ModuleInfo
from types import ModuleType
from typing import Optional

from util.tools import add_tuples

import doctest

DOCTEST_FLAGS = doctest.FAIL_FAST | doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE

def get_module_from_info(module_info: ModuleInfo):
    return import_module(module_info.name)

def iter_modules_of(package: ModuleType):
    '''
    `pkgutil.iter_modules`, reimplemented to take one ModuleType parameter.
    '''
    return pkgutil.iter_modules(package.__path__, package.__name__ + '.')

def _print_separator():
    print("=====================================================================")

def test_module(module: ModuleType) -> doctest.TestResults:
    '''
    Run all tests for a Python module (aka one file).
    '''
    _print_separator()
    print(f"Test {module.__name__}")
    _print_separator()
    return doctest.testmod(
        module,
        verbose=True,
        optionflags=DOCTEST_FLAGS
    )

def test_submodules_nonrecursive(package: ModuleType):
    '''
    Test all modules which are immediate children of a package.

    Args:
        package_info:
            Describes parent package
            (whose subpackages are not tested).
    '''
    results = doctest.TestResults(0, 0)
    for submodule_info in iter_modules_of(package):
        submodule = get_module_from_info(submodule_info)
        if not submodule_info.ispkg:
            curr_result = test_module(submodule)
            results = add_tuples(results, curr_result)
    return results

def test_submodules_recursive(package: ModuleType):
    '''
    Test all modules inside of all the subpackages
    inside of a package.

    Args:
        package_info:
            Describes parent package
            (whose immediate member modules are not tested).
    '''
    results = doctest.TestResults(0, 0)
    for submodule_info in iter_modules_of(package):
        submodule = get_module_from_info(submodule_info)
        if submodule_info.ispkg:
            curr_result = test_submodules_recursive(submodule)
            results = add_tuples(results, curr_result)
        else:
            curr_result = test_module(submodule)
            results = add_tuples(results, curr_result)
    return results

def test_top_level():
    '''
    Test everything in the top-level package (where __main__.py is located).
    '''
    import __main__ # that's a different file than this one (test_all.py)
    main_file_path = __main__.__file__
    tld = Path(main_file_path).parent

    results = doctest.TestResults(0, 0)
    for child in tld.iterdir():
        if child.is_dir():
            # is python package?
            if "__init__.py" in ( x.name if x.is_file() else None
                                  for x in child.iterdir() ):
                # import as package
                package = import_module(child.stem)
                curr_result = test_submodules_recursive(package)
                results = add_tuples(results, curr_result)
        else:
            # is python module?
            if ( child.suffix == ".py"
                 and child.stem not in ("__init__","__setup__") ):
                # import as module
                module = import_module(child.stem)
                curr_result = test_module(module)
                results = add_tuples(results, curr_result)
    return results

if __name__ == "__main__":
    '''
    >>> python3 ./test_all.py "util.tools"
    '''
    if len(sys.argv) == 2:
        module_name = sys.argv[1]
        module = import_module(module_name)
        module_is_package = hasattr(module, "__path__")
        if module_is_package:
            results = test_submodules_recursive(module)
        else:
            results = test_module(module)
    else:
        results = test_top_level()

    _print_separator()
    print(f"{Path(__file__).name} final results")
    _print_separator()
    print(f"{results.attempted - results.failed} passed"
           " and {results.failed} failed.")
    if results.failed == 0:
        print("Tests passed.")
    else:
        print("Tests failed.")
