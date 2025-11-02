import pandas as pd

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
import numbers as num
import pandera.pandas as pa
from pandera.typing import DataFrame
from grade_conversion_script.util.custom_types import BoolsById, StudentPtsById

from grade_conversion_script.util import AliasRecord
from .base import InputHandler, bool_to_pts

class NoAttendanceRuleException(Exception):
    pass

class AttendanceTrueFalse(InputHandler):
    '''
    Abstracts the reading of attendance from generic CSV format of trues/falses.
    Input:  data with external schema (True/False or 1/0).
    Output: data with internally guaranteed schema.

    >>> student_ar = AliasRecord()
    >>> attendance_input = AttendanceTrueFalse(2, student_ar)
    >>> attendance_df = pd.DataFrame({'Name':       ['Name One', 'Name Two'],
    ...                               'Attended 1': [99        ,  0        ],
    ...                               'Attended 2': ['True'    ,  False    ],})
    >>> attendance_input.get_scores(attendance_df)
         Attended 1  Attended 2
    id
    400           2           2
    401           0           0
    >>> str(student_ar)
    "{400: ['Name One'], 401: ['Name Two']}"
    '''

    def __init__(self, pts_per_day: num.Real, student_aliases: AliasRecord):
        ''' Set options which vary among input-handlers here. '''
        super().__init__(student_aliases)
        self.pts_per_day = pts_per_day

    def is_attended(self, element) -> bool:
        # check rule is defined here

        if isinstance(element, bool):
            return element
        if pd.isna(element):
            return False
        if str(element).isnumeric():
            return float(element) > 0

        letter_t = "T" in str(element).upper()
        letter_f = "F" in str(element).upper()
        if letter_t and not letter_f:
            return True
        if letter_f and not letter_t:
            return False

        raise NoAttendanceRuleException(
            f"No rule for bool conversion"
            f" of value {element}"
            f" (type {type(element)})"
        )

    @pa.check_types
    def get_attendance_single_file(self, input: pd.DataFrame) -> DataFrame[BoolsById]:
        '''
        Args:
            input: Dataframe with >= 1 columns. Each column is its own day.
        Returns:
            A DataFrame of same shape and columns,
            modeled by `DataBy_StudentSisId`.
            Values are all type `bool`.
        '''

        input = input.set_index(input.columns[0], drop=True)

        # Determine attendance by element
        attendance = input.map(self.is_attended) # handles NaNs
        
        # Output formatting, populate Name/SisId store
        attendance = self.student_aliases.reindex_by_id(
            attendance,
            expect_new_entities=True,
            collect_new_aliases=True,
            inplace=False
        )

        return DataFrame[BoolsById](attendance)

    @pa.check_types
    def get_attendance_multi_files(self, files: dict[str, pd.DataFrame]) -> DataFrame[BoolsById]:
        '''
        Args:
            files: Dataframes from files.
                keys: Labels for each file.
                vals: DataFrames of CSVs
                      (each with one column per attendance day).
        Returns:
            A multi-column dataframe modeled by `DataBy_StudentSisId`.
            Columns are the concatenated columns of input dataframes.
            Values are all type `bool`.
            The columns are in the same order as the dict's
            insertion order.
        '''
        # Process the files individually first
        attendance_dfs: Iterable[pd.DataFrame] = []
        for file_label, file_df in files.items():
            # process
            attendance_df = self.get_attendance_single_file(file_df)
            # rename columns (to prepare for files concat)
            attendance_df.columns = attendance_df.columns.map(
                lambda x: f"{x} (from file {file_label})"
            )
            # add to list
            attendance_dfs.append(attendance_df)
        
        # Merge the single-file DataFrames in the dict.
        attendance_merged = pd.concat(attendance_dfs, axis='columns', verify_integrity=True)
        
        # Replace NaNs with False.
        # Pandas uses NaN during the merge of columns by index
        # to show that a row was not present for that column.
        attendance_merged = (
            attendance_merged
                .astype("boolean") # pandas nullable Boolean
                .fillna(False)
                .astype(bool)
        )

        return DataFrame[BoolsById](attendance_merged)
    
    @override
    @pa.check_types
    def get_scores(self, csv: pd.DataFrame | dict[str, pd.DataFrame]) -> DataFrame[StudentPtsById]:
        '''
        Args:
            csv:
                `DataFrame`s from input CSV files.
                If a `dict` is provided, each key is the label
                prefixed to that file's columns in the output DataFrame.
        Returns:
            A dataframe modeled by StudentPtsById.
            Columns are the same or prefixed by dict keys.
        '''
        if isinstance(csv, dict):
            attendance_bools = self.get_attendance_multi_files(csv)
        else:
            attendance_bools = self.get_attendance_single_file(csv)

        attendance_pts = bool_to_pts(attendance_bools, self.pts_per_day)

        return attendance_pts
    