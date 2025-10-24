import pandas as pd
from .base import InputHandler, bool_to_pts

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
import numbers as num
import pandera.pandas as pa
from pandera.typing import DataFrame, Series
from util.types import SisId, PtsBy_StudentSisId, BoolsBy_StudentSisId
from util import NameSisIdConverter

class AttendanceTrueFalse(InputHandler):
    '''
    Abstracts the reading of attendance from generic CSV format of trues/falses.
    Input:  data with external schema (True/False or 1/0).
    Output: data with internally guaranteed schema.

    >>> name_sis_id = NameSisIdConverter()
    >>> attendance_input = AttendanceTrueFalse(2, name_sis_id)
    >>> attendance_df = pd.DataFrame({'Name':       ['Name One', 'Name Two'],
    ...                               'Attended 1': [99        ,  0        ],
    ...                               'Attended 2': [True      ,  False    ],})
    >>> attendance_input.get_scores(attendance_df)
            Attended 1  Attended 2
    sis_id            
    name1            2           2
    name2            0           0
    >>> str(name_sis_id)
    "{'Name One': 'name1', 'Name Two': 'name2'}" TODO i know this doesn't work
    '''

    def __init__(self, pts_per_day: num.Real, name_sis_id_store: NameSisIdConverter):
        ''' Set options which vary among input-handlers here. '''
        super().__init__(name_sis_id_store)
        self.pts_per_day = pts_per_day

    @pa.check_types
    def get_attendance_single_file(self, input: pd.DataFrame) -> DataFrame[BoolsBy_StudentSisId]:
        '''
        Args:
            input: Dataframe with >= 1 columns. Each column is its own day.
        Returns:
            A DataFrame of same shape and columns,
            modeled by `DataBy_StudentSisId`.
            Values are all type `bool`.
        '''

        # Determine attendance by element
        
        def has_attended(element) -> bool:
            if isinstance(element, str) and element.startswith("'"):
                # clean a quirk Excel might add
                element = element[1:]

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
            
            raise NotImplementedError(
                f"No rule for bool conversion"
                f" of value {element}"
                f" (type {type(element)})"
            )

        attendance = input.map(has_attended) # handles NaNs
        
        # Output formatting TODO the following ~7 lines
        student_names: pd.Series = student_rows['First name'] + ' ' + student_rows['Last name']
        sis_ids = student_rows['Email'] \
                    .apply(lambda x: SisId.from_email(x) if not pd.isna(x) else None)
        # set index TODO
        attendance = attendance.set_axis(sis_ids, axis='index')
        
        # Populate Name/SisId store TODO
        self.name_sis_id_store.addFromCols(sis_ids=sis_ids, names=student_names)

        return DataFrame[BoolsBy_StudentSisId](attendance)

    @pa.check_types
    def get_attendance_multi_files(self, files: dict[str, pd.DataFrame]) -> DataFrame[BoolsBy_StudentSisId]:
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

        return DataFrame[BoolsBy_StudentSisId](attendance_merged)
    
    @override
    @pa.check_types
    def get_scores(self, csv: pd.DataFrame | dict[str, pd.DataFrame]) -> DataFrame[PtsBy_StudentSisId]:
        '''
        Args:
            csv:
                `DataFrame`s from input CSV files.
                If a `dict` is provided, each key is the label
                prefixed to that file's columns in the output DataFrame.
        Returns:
            A dataframe modeled by PtsBy_StudentSisId.
            Columns are the same or prefixed by dict keys.
        '''
        if isinstance(csv, dict):
            attendance_bools = self.get_attendance_multi_files(csv)
        else:
            attendance_bools = self.get_attendance_single_file(csv)

        attendance_pts = bool_to_pts(attendance_bools, self.pts_per_day)

        return attendance_pts
    