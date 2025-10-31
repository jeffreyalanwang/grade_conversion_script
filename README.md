# Grade Conversion Script

Extendable application using Pandas
to convert grades from one .csv format to another.

## Usage

1. [Install `pipx`.](https://pipx.pypa.io/stable/installation/)
    Below is a copy of the linked instructions.
    <i>
    <br/> Skip this step if you can already run the `pipx` command without error
    <br/> (likely the case if running on Linux).
    </i>

    **Mac**
    ```zsh
    # if homebrew not installed
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     
    brew install pipx
    pipx ensurepath
    ```
    **Windows**
    ```PowerShell
    # You may need to replace `py` with `python` or `python3`.
    py -m pip install --user pipx
    py -m pipx ensurepath
    ```
    
2. Run the script.
    ```console
    pipx run --spec git+https://github.com/jeffreyalanwang/grade_conversion_script.git#wheel=grade_conversion_script grade-convert [OPTIONS]
    ```
    <i>
    The above downloads a fresh copy for each run.
    For a local copy, use:
    </i>
    
    ```console
    # Save to local computer
    pipx install git+https://github.com/jeffreyalanwang/grade_conversion_script.git#wheel=grade_conversion_script [OPTIONS]
    
    # Run
    grade-convert [OPTIONS]
    ```
    ```console
    # To uninstall
    pipx uninstall grade_conversion_script
   ```

### Examples

#### Example 1: help

```console
grade-convert output e_rubric --help
```
**Get help** for the **Enhanced Rubric format** (Canvas).

#### Example 2: conversion

```console
grade-convert output e_rubric --help input pollev_attendance 2 $ATT_1 $ATT_2 output e_rubric $ORIG_RUBRIC --no-warn-existing "output.csv"
```
**Read PollEv attendance** export files at paths `$ATT_1` and `$ATT_2`, with each day of attendance worth 2 points.

Convert to Enhanced Rubric format (Canvas).
<br> If an existing value exists, do not replace it and do not print a warning.
<br> Downloaded template is located at `$ORIG_RUBRIC`.

Save result to `./output.csv`.

## Extending

> 💡 It may be easiest to copy code from an existing input or output module.

1. In [input/](/grade_conversion_script/input/) or [output/](/grade_conversion_script/output/), create a new module.

2. Write a new class extending the class in the sibling `.base` module.

3. Add the class in the sibling file named `__init__.py`.

4. Finally, modify [cmd_opts.py](/grade_conversion_script/cmd_opts.py) to add command-line options.
    * See `configure_input_parser()` or `configure_output_parser()`
      <br> to add flags/options.
    * See `_prepare_input_handler()` and `_prepare_output_handler()`
      <br> to match these options to your corresponding new class.

5. Commit new code or fork this repository;
   if applicable, distribute a new `pipx run` command with a link to forked repository.

## Tests

Currently the only tests available are docstring examples, which can be tested using `doctest`;
they can easily be checked all at once by running:
```console
pip install pytest
pytest --doctest-modules ./grade_conversion_script
```
