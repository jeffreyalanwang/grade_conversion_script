import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
import pandas as pd

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]

from util import EnumAction, NameSisIdConverter
from util.funcs import to_real_number
from input import *
from output import *

'''
To add a new command option, modify `setup_per_args` to handle
an attribute of `input_args` or `output_args`.

Then, add the command argument in either
`configure_input_parser` or `configure_output_parser`.
'''

# Only function from this file
# to be called by others
# is `run()`
__all__ = ['run',]

def parse_args() -> tuple[Namespace, Namespace]:
    '''
    Set up parser and use it.

    Returns:
        Tuple.
        (input args, output args)
    '''
    def configure_input_parser(input_parser: ArgumentParser):
        ''' Configure one subparser for each input handler. '''

        input_parser.usage = "input FORMAT [INPUT OPTIONS]"
        input_parser._positionals.title = "FORMAT"

        # Input formats are mutually exclusive
        input_subparsers = input_parser.add_subparsers(dest='input_format')

        # All subparsers
        input_parser \
        .set_defaults(
            # add default for any subparser that takes these args
            input_csvs=[# all files in directory
                        item.name
                        for item in Path("..").iterdir()
                        if item.is_file()]
        )

        # PollEv attendance
        pollev_attendance_cmd = input_subparsers \
            .add_parser(
                'pollev_attendance', # stored under args['input_format']
                description="generate student attendance from PollEv export",
                help="`input pollev_attendance --help`",
            )
        pollev_attendance_cmd.usage = \
            "pollev_attendance ATTENDANCE_POINTS INPUT_CSVS"
        pollev_attendance_cmd \
        .add_argument(
            'attendance_points',
            type=to_real_number,
            help='# of points per student per day (int or float)'
        )
        pollev_attendance_cmd \
        .add_argument(
            'input_csvs',
            type=str,
            action='extend',
            nargs='+',
            help='one or more PollEverywhere results CSV files corresponding'
                ' to attendance on one or more days'
        )

    def configure_output_parser(output_parser: ArgumentParser):
        ''' Configure one subparser for each output format. '''

        output_parser.usage = "output FORMAT [OUTPUT OPTIONS] OUTPUT_GRADES_CSV"
        output_parser._positionals.title = "FORMAT"

        # Output formats are mutually exclusive
        output_subparsers = output_parser.add_subparsers(dest='output_format')

        # All subparsers
        output_parser \
        .add_argument_group(
            'required options'
        ) \
        .add_argument(
            # add an argument which applies to all output formats
            'output_grades_csv',
            type=str,
            help='output file location',
            default='grades_out.csv'
        )

        # Canvas Gradebook CSV
        c_gradebook_cmd = output_subparsers \
            .add_parser(
                'c_gradebook', # stored under args['input_format']
                description="fill a Canvas Gradebook export to reupload",
                help="`output c_gradebook --help`",
            )
        c_gradebook_cmd.usage = \
            "c_gradebook CSV_TEMPLATE HEADER [optional arguments]"
        c_gradebook_cmd \
        .add_argument(
            'csv_template',
            type=str,
            help='a grades CSV file exported from Canvas'
        )
        c_gradebook_cmd \
        .add_argument(
            'header',
            type=str,
            help='the header of the column corresponding to the'
                ' attendance assignment in the grades CSV file,'
                ' for example, "Attendance (2577952)"'
        )
        c_gradebook_cmd \
        .add_argument(
            '--if-existing',
            type=CanvasGradebookOutputFormat.ReplaceBehavior,
            action=EnumAction,
            dest='if_existing',
            help='Behavior for existing grades in gradebook file'
        )
        c_gradebook_cmd \
        .add_argument(
            '--no-warn-existing',
            action='store_false', # => default (flag not present) is True
            dest='warn_existing',
            help='warn if a grade to be filled already'
                ' exists (even if it is not replaced).'
        )

        # Auto Canvas Rubric
        acr_cmd = output_subparsers \
            .add_parser(
                'acr', # stored under args['input_format']
                description='create a file which can be loaded into'
                            ' Auto Canvas Rubric Chrome extension'
                            ' (for non-enhanced rubrics; see'
                            ' https://github.com/jeffreyalanwang/auto_canvas_rubric/)',
                help="`output acr --help`",
            )
        acr_cmd.usage = \
            "acr"
        
        # Canvas Enhanced Rubric CSV
        c_enhanced_rubric_cmd = output_subparsers \
            .add_parser(
                'e_rubric', # stored under args['input_format']
                description='fill a Canvas rubric export to reupload'
                            ' (note: Enhanced Rubrics only)',
                help="`output e_rubric --help`",
            )
        c_enhanced_rubric_cmd.usage = \
            "e_rubric CSV_TEMPLATE [optional arguments]"
        c_enhanced_rubric_cmd \
        .add_argument(
            'csv_template',
            type=str,
            help='a rubric CSV file exported from Canvas'
        )
        c_enhanced_rubric_cmd \
        .add_argument(
            '--replace',
            action='store_true',
            dest='replace',
            help='whether to replace a grade that already'
                ' has a rating, grade, or comment'
        )
        c_enhanced_rubric_cmd \
        .add_argument(
            '--no-warn-existing',
            action='store_false', # => default (flag not present) is True
            dest='warn_existing',
            help='warn if a grade to be filled already'
                ' exists (even if it is not replaced).'
        )

    def execute_parser(parser: ArgumentParser):
        '''
        Read all the arguments for one subparser
        (input or output), then the other.
        
        Returns:
            Same as outer function (`parse_args`).
        '''
    
        if all((x in sys.argv)
               for x in ('input', 'output')):
            input_keyword_idx = sys.argv.index('input')
            output_keyword_idx = sys.argv.index('output')
            
            pre_argv = sys.argv[ : input_keyword_idx]
            input_argv = sys.argv[input_keyword_idx : output_keyword_idx]
            output_argv = sys.argv[output_keyword_idx : ]
            
            # pre_args = parser.parse_args(pre_argv)
            input_args = parser.parse_args(input_argv)
            output_args = parser.parse_args(output_argv)

            return input_args, output_args

        # Get argparse to show our keyword
        given_args, rest = parser.parse_known_args()
        raise UserWarning("Missing input or output keyword")

    # Parse command-line arguments.
    top_level_parser = ArgumentParser(
        description='This script takes CSV grades from various sources'
                    ' (such as PollEverywhere results export)'
                    ' to create a new CSV file containing updated'
                    ' grades that can be imported to Canvas.',
        usage="%(prog)s input [INPUT OPTIONS] output [OUTPUT OPTIONS]",
    )

    # Input/Output subparsers

    subparsers = top_level_parser.add_subparsers(dest='input_output', required=True)
    top_level_parser._positionals.title = "Command arg parts"

    input_parser = subparsers \
        .add_parser(
            'input', # stored under args['input_output']
            help="`%(prog)s input --help`"
        )
    configure_input_parser(input_parser)
    
    output_parser = subparsers \
        .add_parser(
            'output', # stored under args['input_output']
            help="`%(prog)s output --help`"
        )
    configure_output_parser(output_parser)
    
    # Execute
    result_args_input, result_args_output = execute_parser(top_level_parser)
    return result_args_input, result_args_output

class Handlers_Collection(NamedTuple):
    input: InputHandler
    output: OutputFormat
class Files_Collection(NamedTuple):
    input: str | Iterable[str]
    output: str | Iterable[str]
class Setup_Collection(NamedTuple):
    handlers: Handlers_Collection
    files: Files_Collection

def setup_per_args(input_args, output_args) -> Setup_Collection:
    ''' Create objects for injection based on cmd args. '''

    def _prepare_input_handler(args, *, student_id_record) -> InputHandler:
        handler = None
        match args.input_format:
            case 'pollev_attendance':
                handler = AttendancePollEv(
                    pts_per_day=args.attendance_points,
                    name_sis_id_store=student_id_record
                )
            case _:
                raise ValueError
        return handler
    def _prepare_output_handler(args, *, student_id_record, input_is_attendance) -> OutputFormat:
        handler = None
        match args.output_format:
            case 'c_gradebook':
                handler = CanvasGradebookOutputFormat(
                    gradebook_csv=pd.read_csv(args.csv_template),
                    assignment_header=args.header,
                    sum=True, # This program only supports one assignment at a time
                    if_existing=( args.if_existing
                                    if hasattr(args, "if_existing")
                                  else CanvasGradebookOutputFormat.ReplaceBehavior.INCREMENT
                                    if input_is_attendance
                                  else CanvasGradebookOutputFormat.ReplaceBehavior.ERROR ),
                    warn_existing=( args.warn_on_existing
                                    if hasattr(args, "warn_on_existing")
                                    else input_is_attendance ),
                )
            case 'acr':
                handler = AcrOutputFormat(
                    name_sis_id_converter=student_id_record
                )
            case 'e_rubric':
                handler = CanvasEnhancedRubricOutputFormat(
                    name_sis_id_converter=student_id_record,
                    rubric_csv=pd.read_csv(args.csv_template),
                    replace_existing=(args.replace
                                        if args.replace is not None
                                        else False),
                    warn_existing=( args.warn_on_existing
                                    if hasattr(args, "warn_on_existing")
                                    else input_is_attendance ),
                )
            case _:
                raise ValueError
        return handler
    def prepare_handlers(input_args, output_args) -> Handlers_Collection:

        # Create shared resources

        shared_student_id_record = NameSisIdConverter()
        """ Links `SisId`s and names as seen in the input file. """

        # Create handlers

        input_handler = _prepare_input_handler(
            input_args,
            student_id_record = shared_student_id_record,
        )
        output_handler = _prepare_output_handler(
            output_args,
            student_id_record = shared_student_id_record,
            input_is_attendance = (
                input_args.input_format in (
                    'pollev_attendance',
                ),
            ),
        )

        return Handlers_Collection(input_handler, output_handler)
    
    def get_file_args(input_args, output_args) -> Files_Collection:
        input_files = input_args.input_csvs
        output_files = output_args.output_grades_csv

        for files in (input_files, output_files):
            assert (
                isinstance(files, str)
                or (
                    isinstance(files, list)
                    and (
                        isinstance(files[0], str)
                        or len(files) == 0
                    )
                )
            )
        
        return Files_Collection(input_files, output_files)

    files = get_file_args(input_args, output_args)
    handlers = prepare_handlers(input_args, output_args)
    return Setup_Collection(handlers, files)
        
def run():
    args = parse_args()
    prepared_objs = setup_per_args(*args)
    return prepared_objs