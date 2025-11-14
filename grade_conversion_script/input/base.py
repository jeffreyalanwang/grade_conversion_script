import numbers as num
from abc import ABC, abstractmethod

import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame

from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.custom_types import BoolsById, StudentPtsById


class InputHandler(ABC):
    '''
    Process data with a specific format, using a specific behavior,
    to extract grades into a DataFrame modeled by `StudentPtsById`.

    Subclasses must take and populate an `AliasRecord`.
    '''
    @abstractmethod
    def __init__(self, student_aliases: AliasRecord):
        self.student_aliases: AliasRecord = student_aliases

    @abstractmethod
    def get_scores(self, csv: pd.DataFrame | dict[str, pd.DataFrame]) -> DataFrame[StudentPtsById]:
        '''
        Args:
            csv:
                `DataFrame`s from input CSV files.
                If a `dict` is provided, each key is the label
                for that file's column in the output DataFrame.
        Returns:
            A dataframe modeled by StudentPtsById.
            If one CSV was provided (i.e. one day), output has
            1 column, labeled 'attendance'.
        '''
        ...

@pa.check_types
def bool_to_pts(attendance_bools: DataFrame[BoolsById], pts_if_true: num.Real) -> DataFrame[StudentPtsById]:
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
    # Create DataFrame with output type (float OR int)
    dest_type = type(pts_if_true)
    attendance_pts = attendance_bools.astype(dest_type) # 0s and 1s

    # Fill in the points
    attendance_pts = attendance_pts * pts_if_true

    # Check output formatting
    assert all(attendance_pts.index == attendance_bools.index)
    assert all(attendance_pts.columns == attendance_bools.columns)

    return DataFrame[StudentPtsById](attendance_pts)