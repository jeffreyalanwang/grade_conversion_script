# We need to make sure non-packaged dependencies
# (i.e. packages with native extension code, e.g. pandas)
# are available
import os

from grade_conversion_script.bootstrap_utils import ensure_pkg_dependencies

ensure_pkg_dependencies()

import sys
from pathlib import Path
import logging
import pandas as pd


def cli_main():
    from grade_conversion_script import cmd_opts

    handlers, files = cmd_opts.run() # argparse reads cmd args

    # Process input

    if isinstance(files.input, str):
        input_files = [Path(files.input),]
    else:
        input_files = [Path(s) for s in files.input]

    scores = handlers.input.get_scores({
        path.name : pd.read_csv(path)
        for path in input_files
    })

    # Generate output

    output_df = handlers.output.format(scores)

    if isinstance(files.output, str):
        output_file_path = Path(files.output)
    else:
        # could be an iterable of strings in the future,
        # but we do not handle this right now
        raise NotImplementedError

    if not output_file_path.parent.exists():
        raise FileNotFoundError(
            f"Output file's parent directory does not"
            f" exist: {output_file_path.parent}")

    while output_file_path.exists():
        new_filename = output_file_path.stem + "_1" + output_file_path.suffix
        output_file_path = output_file_path.parent / new_filename

    handlers.output.write_file(output_df, output_file_path)
    print(f"Result saved to {output_file_path}.")

def gui_main():
    from grade_conversion_script.gui import start_app
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=os.path.expanduser("~/Desktop"),
        filemode="a"  # Append to the file (default)
    )
    start_app.main()

if __name__ in ('__main__', '__mp_main__'):
    if 'gui' in sys.argv:
        gui_main()
    else:
        cli_main()