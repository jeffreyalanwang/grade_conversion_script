import pandas as pd
from pathlib import Path

from typing import *
from pandera.typing import DataFrame
from .util.types import PtsBy_StudentSisId

from .cmd_opts import run as get_cmd_setup
from .input import *
from .output import *

def process_input_file(handler: InputHandler, files: Iterable[Path]):
    ''' Read and process grades to internal format. '''

    read_dfs = { filepath.name : pd.read_csv(filepath)
                 for filepath in files }
    scores = handler.get_scores(read_dfs)
    return scores

def create_output_file(scores: DataFrame[PtsBy_StudentSisId], handler: OutputFormat, filepath: Path):
    ''' Process and write grades to external format. '''

    out_df = handler.format(scores)
    handler.write_file(out_df, filepath)

if __name__ == '__main__':

    handlers, files_str = get_cmd_setup() # argparse reads cmd args

    if isinstance(files_str.input, str):
        input_files_path_coll = (files_str.input,)
    else: # iterable of strings
        input_files_path_coll = files_str.input
    input_files_path_coll = ( Path(s)
                               for s in input_files_path_coll )
    data = process_input_file(handlers.input, input_files_path_coll)

    if isinstance(files_str.output, str):
        output_file_path = Path(files_str.output)
    else:
        # could be an iterable of strings,
        # but we do not handle this right now
        raise NotImplementedError
    create_output_file(data, handlers.output, output_file_path)
