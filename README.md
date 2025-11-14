# Grade Conversion Script

Extendable application using Pandas
to convert grades from one .csv format to another.

## Usage

1. [Install `pipx`.](https://pipx.pypa.io/stable/installation/)
    Below is a copy of the linked instructions.
    <i>
    <br/> Skip this step if you can already run the [`pipx`](## "You can 
   also use `uv` (step 2 with `uvx --from` instead of `pipx run --spec`).") 
   command without error
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
    pipx run --spec git+https://github.com/jeffreyalanwang/grade_conversion_script.git grade-convert [OPTIONS]
    ```
    <i>
    The above downloads a fresh copy for each run.
    For a local copy, use:
    </i>
    
    ```console
    # Save to local computer
    pipx install git+https://github.com/jeffreyalanwang/grade_conversion_script.git [OPTIONS]
    
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
grade-convert input pollev_attendance 2 $ATT_1 $ATT_2 output e_rubric $ORIG_RUBRIC --no-warn-existing "output.csv"
```
**Read PollEv attendance** export files at paths `$ATT_1` and `$ATT_2`, with each day of attendance worth 2 points.

Convert to Enhanced Rubric format (Canvas).
<br> If an existing value exists, do not replace it and do not print a warning.
<br> Downloaded template is located at `$ORIG_RUBRIC`.

Save result to `./output.csv`.

## More options

### GUI

Prefix the URL as shown to ensure the extra GUI dependencies are installed.
Then, replace `grade-convert` with `grade-convert-app` to run the GUI.

```console
pipx run --spec "grade_conversion_script[gui] @ git+https://github.com/jeffreyalanwang/grade_conversion_script.git" grade-convert-app

# Local install:
pipx install "grade_conversion_script[gui] @ git+https://github.com/jeffreyalanwang/grade_conversion_script.git"
grade-convert-app
```

### Quicker start with `uv`

`uv` is a popular alternative to `pip` and `pipx` that might be able to build and run this tool more quickly. It implicitly caches a local install but updates it if needed.

[Once installed](https://docs.astral.sh/uv/getting-started/installation/), it can substitute any of the above commands. `uvx --from` replaces `pipx run --spec`.

```console
uvx --from git+https://github.com/jeffreyalanwang/grade_conversion_script.git grade-convert
uvx --from "grade_conversion_script[gui] @ git+https://github.com/jeffreyalanwang/grade_conversion_script.git" grade-convert-app
```

## Extending

> 💡 It is easiest to copy code from an existing input or output module.

1. In [input/](/grade_conversion_script/input/) or [output/](/grade_conversion_script/output/), create a new module.

2. Write a new class extending the class in the sibling `.base` module.

3. Add the class in the sibling file named `__init__.py`.

4. Finally, modify [cmd_opts.py](/grade_conversion_script/cmd_opts.py) to add command-line options.
    * See `configure_input_parser()` or `configure_output_parser()`
      <br> to add flags/options.
    * See `_prepare_input_handler()` and `_prepare_output_handler()`
      <br> to match these options to your corresponding new class.

5. (optional) Add GUI functionality in [gui/flow_components/select_input/](/grade_conversion_script/gui/flow_components/select_input/) or [gui/flow_components/select_output/](/grade_conversion_script/gui/flow_components/select_output/).
   * Create a new handler element and export its metadata, as seen in existing components in the directory.
   * Include the exported metadata in the `HANDLERS` constant (located in [select_input_handler.py](/grade_conversion_script/gui/flow_components/select_input/select_input_handler.py) or [select_output_format.py](/grade_conversion_script/gui/flow_components/select_output/select_output_format.py)).
    
6. Commit new code or fork this repository;
   if applicable, distribute a new `pipx run` command with a link to forked repository.

## Tests

The following runs all doctests as well as files in [test/](/test/).

```console
pip install pytest
pytest ./test --doctest-modules ./grade_conversion_script
```
