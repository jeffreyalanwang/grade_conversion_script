import pandas as pd
from .base import InputHandler

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
import numbers as num
import pandera.pandas as pa
from pandera.typing import DataFrame, Series
from grade_conversion_script.util.types import SisId, PtsBy_StudentSisId, BoolsBy_StudentSisId
from grade_conversion_script.util import AliasRecord

class AttendancePollEv(InputHandler):
    '''
    Abstracts the reading of attendance from PollEverywhere CSV.
    Input:  data with external schema (PollEverywhere export).
    Output: data with internally guaranteed schema.

    >>> name_sis_id = NameSisIdConverter()
    >>> attendance_input = AttendancePollEv(2, name_sis_id)
    >>> pollev_df = pd.DataFrame({'First name': ['Name','Name','Average grade','Average participation'],
    ...                           'Last name' : ['One', 'Two', None,           None],
    ...                           'Email'     : ['name1@charlotte.edu','name2@charlotte.edu', None, None],
    ...                           'Grade'     : [99   ,  0,    None,           None]})
    >>> attendance_input.get_scores(pollev_df)
            attendance
    sis_id            
    name1            2
    name2            0
    >>> str(name_sis_id)
    "{'Name One': 'name1', 'Name Two': 'name2'}"
    '''

    def __init__(
        self,
        pts_per_day: num.Real,
        name_sis_id_store: NameSisIdConverter,
        attendance_rule: Callable[
                             [pd.DataFrame | pd.Series],
                             Series[bool] | bool
                         ] | None
            = None
    ):
        ''' Set options which vary among input-handlers here. '''
        super().__init__(name_sis_id_store)
        self.pts_per_day = pts_per_day
        if attendance_rule is not None:
            self.has_attended = attendance_rule # pyright: ignore[reportAttributeAccessIssue]

    @overload
    def is_attended(self, student_rows: pd.DataFrame, /) -> Series[bool]:
        ...

    @overload
    def is_attended(self, student_rows: pd.Series, /) -> bool:
        ...
    def is_attended(self, student_rows: pd.DataFrame | pd.Series, /) -> Series[bool] | bool:
        '''
        Check rule is defined here.

        May be overridden by `self.__init__()`.
        '''
        numeric_grades: pd.Series | num.Real = pd.to_numeric(student_rows['Grade'], errors="coerce")
        is_na = pd.isna(numeric_grades)
        is_pos = numeric_grades > 0

        if isinstance(numeric_grades, pd.DataFrame):
            assert isinstance(is_na, pd.Series)
            assert isinstance(is_pos, pd.Series)
            truthy = (~is_na) & is_pos
        else:
            assert isinstance(is_na, bool)
            assert isinstance(is_pos, bool)
            truthy = (not is_na) and is_pos

        if isinstance(truthy, pd.Series):
            return Series[bool](truthy)
        else:
            return truthy

    @pa.check_types
    def get_single_day_attendance(self, pollev_day: pd.DataFrame) -> DataFrame[BoolsBy_StudentSisId]:
        '''
        Args:
            pollev_day: Dataframe from one PollEv export CSV.
        Returns:
            A one-column DataFrame modeled by `DataBy_StudentSisId`.
            Values are all type `bool`.
            The column has the generic label 'attended'.
        '''

        # Each row corresponds to one student and their response.
        # Do not iterate over the last two rows, since these
        # only contain average information.
        student_rows = pollev_day[:-2]

        # Double-check that the last 2 rows are, in fact, not students
        average_rows = pollev_day[-2:]
        average_rows_column1: pd.Series = average_rows.iloc(axis='columns')[0]
        assert all( row_label.startswith("Average")
                    for row_label in average_rows_column1 )

        # Determine attendance by student
        attendance = student_rows \
                        .apply(
                            self.has_attended,
                            axis='columns' # passes one row to function at a time
                        ).squeeze()
        assert isinstance(attendance, pd.Series)
        
        # Output formatting
        student_names: pd.Series = student_rows['First name'] + ' ' + student_rows['Last name']
        sis_ids = student_rows['Email'] \
                    .apply(lambda x: SisId.from_email(x)
                                     if not pd.isna(x) else None)
        # drop NaNs before we reindex
        to_drop = student_names.isna() | sis_ids.isna()
        sis_ids = sis_ids[~to_drop]
        student_names = student_names[~to_drop]
        attendance = attendance[~to_drop]
        # set index
        attendance = attendance.set_axis(sis_ids, axis='index')
        # set labels
        attendance = attendance \
                        .rename("attended") \
                        .rename_axis("sis_id", axis='index')
        # convert Series to DataFrame
        assert isinstance(attendance, pd.Series)  
        attendance = attendance.to_frame()
        
        # Populate Name/SisId store        
        self.name_sis_id_store.addFromCols(sis_ids=sis_ids, names=student_names)

        return DataFrame[BoolsBy_StudentSisId](attendance)

    @pa.check_types
    def get_multi_day_attendance(self, pollev_days: dict[str, pd.DataFrame]) -> DataFrame[BoolsBy_StudentSisId]:
        '''
        Args:
            pollev_days: Dataframe from PollEv export CSVs.
                keys: Labels for each PollEv export.
                vals: DataFrames of PollEv export CSV
                      (each is one day of attendance).
        Returns:
            A multi-column dataframe modeled by `DataBy_StudentSisId`.
            Values are all type `bool`.
            One column exists for each entry in the input dict,
            with the given label.
            The columns are in the same order as the dict's
            insertion order.
        '''
        # Create a column for each day of attendance.
        def csv_to_column(col_label, csv: pd.DataFrame) -> Series[bool]:
            attendance_df = self.get_single_day_attendance(csv) # process into bools
            series = attendance_df['attended'] # turn into series
            series.name = col_label # rename with intended column label
            return Series[bool](series)
        cols: Iterable[pd.Series]
        cols = (csv_to_column(day_label, csv)
                for day_label, csv in pollev_days.items())
        # Merge the single-day DataFrames in the dict.
        attendance_multi_day = pd.concat(cols, axis='columns', verify_integrity=True)
        
        # Replace NaNs with False.
        # Pandas uses NaN during the merge of columns by index (i.e. sis_id)
        # to show that a row was not present for that column.
        attendance_multi_day = (
            attendance_multi_day
                .astype("boolean") # pandas nullable Boolean
                .fillna(False)
                .astype(bool)
        )

        # Assert column order.
        expected_column_names: list[str] = list(pollev_days.keys())
        actual_column_names: list[str] = attendance_multi_day.columns.to_list()
        assert expected_column_names == actual_column_names

        return DataFrame[BoolsBy_StudentSisId](attendance_multi_day)
    
    @pa.check_types
    def attendance_bool_to_pts(self, attendance_bools: DataFrame[BoolsBy_StudentSisId]) -> DataFrame[PtsBy_StudentSisId]:
        '''
        Replaces boolean attendence values (i.e. per-student, per-day)
        with defined per-class point value configured with `__init__()`.

        Args:
            attendance_cols: DataFrame of only `bool` values,
            corresponding to whether a student attended class.
        Returns:
            A DataFrame of same shape, index, and labels as input,
            but with int or float values.
        '''
        # Create DataFrame with output type
        dest_type = type(self.pts_per_day)
        attendance_pts = attendance_bools.astype(dest_type) # 0s and 1s

        # Fill in the points
        attendance_pts = attendance_pts * self.pts_per_day

        # Check output formatting
        assert all(attendance_pts.index == attendance_bools.index)
        assert all(attendance_pts.columns == attendance_bools.columns)

        return DataFrame[PtsBy_StudentSisId](attendance_pts)
    
    @override
    @pa.check_types
    def get_scores(self, csv: pd.DataFrame | dict[str, pd.DataFrame]) -> DataFrame[PtsBy_StudentSisId]:
        '''
        Args:
            csv:
                `DataFrame`s from input CSV files.
                If a `dict` is provided, each key is the label
                for that file's column in the output DataFrame.
        Returns:
            A dataframe modeled by PtsBy_StudentSisId.
            If one CSV was provided (i.e. one day),
            output has 1 column, labeled 'attendance'.
        '''
        if isinstance(csv, dict):
            attendance_bools = self.get_multi_day_attendance(csv)
        else:
            attendance_bools = self.get_single_day_attendance(csv) \
                                   .rename(columns={'attended': 'attendance'})

        attendance_pts = self.attendance_bool_to_pts(attendance_bools)

        return attendance_pts