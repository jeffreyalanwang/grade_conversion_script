from abc import ABC, abstractmethod
from typing import final

import pandas as pd
from pandera.typing import DataFrame
from grade_conversion_script.util.types import StudentPtsById
from grade_conversion_script.util import AliasRecord

class InputHandler(ABC):
    '''
    Process data with a specific format, using a specific behavior,
    to extract grades into a DataFrame modeled by `PtsBy_StudentSisId`.

    Subclasses must generate a `NameSisIdConverter`.
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
            A dataframe modeled by PtsBy_StudentSisId.
            If one CSV was provided (i.e. one day), output has
            1 column, labeled 'attendance'.
        '''
        ...
