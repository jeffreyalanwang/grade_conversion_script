from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
from pandera.typing import DataFrame

from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.custom_types import StudentPtsById


class OutputFormat(ABC):
    '''
    Process grades from a DataFrame modeled by `StudentPtsById`,
    to a specific import format for a gradebook.
    
    Constraint:
        Subclasses need a separate instance for each assignment.
    '''
    @abstractmethod
    def __init__(self, student_aliases: AliasRecord):
        self.student_aliases: AliasRecord = student_aliases

    @abstractmethod
    def format(self, grades: DataFrame[StudentPtsById]) -> pd.DataFrame:
        '''
        Args:
            grades:
                One column per rubric criteria.
                One row per student.
        Returns:
            A dataframe which can be saved to file with self.write_file.
        '''
        ...
    @classmethod # seems cannot be static to work properly with inheritance
    @abstractmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path) -> None:
        ''' Write the output of this class to a file. '''
        ...