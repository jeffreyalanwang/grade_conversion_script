# Grade Conversion Script

Extendable application using Pandas
to convert grades from one .csv format to another.

## Usage

1. Download the script from [the Releases page](https://github.com/jeffreyalanwang/grade_conversion_script/releases/).
1. Install dependencies on your system: `pandas` `pandera` `argparse` `colorama`
   * Python may require you to create a venv:
     ```console
     python3 -m venv VENV_FOLDER_PATH
     mv grade_conversion_script.pyz VENV_FOLDER_PATH
     cd VENV_FOLDER_PATH
     source bin/activate
     ```
   * Then:
     ```console
     python3 -m pip pandas pandera argparse colorama
     ```
1. Run the script.
   ```console
   python3 grade_conversion_script.pyz --help
   ```

### Examples

**Get help** for the Enhanced Rubric format (Canvas).
```console
python3 grade_conversion_script.pyz output e_rubric --help
```

**Read PollEv attendance** export files at paths `$ATT_1` and `$ATT_2`, with each day of attendance worth 2 points.

Convert to Enhanced Rubric format (Canvas). If an existing value exists, do not replace it and do not print a warning. Downloaded template is available at `$ORIG_RUBRIC`.

Save result to `./output.csv`.

```console
python3 ./grade_conversion_script.pyz input pollev_attendance 2 $ATT_1 $ATT_2 output e_rubric $ORIG_RUBRIC --no-warn-existing "output.csv"
```

## Extending

> It may be easiest to copy the code for an existing input or output module, for each of the following steps.

1. In [input/](/input/) or [output/](/output/), create a new module.

2. Write a new class extending the class in the sibling `.base` module.

3. Add the class in the sibling `__init__.py`.

4. Finally, modify [cmd_opts.py](/cmd_opts.py) to add command-line options.
    * See `configure_input_parser()` or `configure_output_parser()` \
      to add flags/options.
    * See `_prepare_input_handler()` and `_prepare_output_handler()` \
      to match these options to your corresponding new class.

## Building

Build a .pyz file using [build.py](/build.py).

**Note:** The build script requires `Python >= 3.13`.

## Tests

Currently the only tests available are docstring examples, which can be test using `doctest`;
they can easily be checked all at once by running [test_all.py](/test_all.py).
