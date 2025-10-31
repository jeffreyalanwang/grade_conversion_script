from pathlib import Path
import pandas as pd

from abc import ABC, abstractmethod

from pandera.typing import DataFrame
from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.types import StudentPtsById

class OutputFormat(ABC):
    '''
    Process grades from a DataFrame modeled by `PtsBy_StudentSisId`,
    to a specific import format for a gradebook service.
    
    Constraint:
        Subclasses need a separate instance for each Canvas assignment.
    '''
    @abstractmethod
    def __init__(self, student_aliases: AliasRecord):
        self.student_aliases: AliasRecord = student_aliases

    @abstractmethod
    def format(self, grades: DataFrame[StudentPtsById]) -> pd.DataFrame:
        ...
    @classmethod # seems cannot be static to work properly with inheritance
    @abstractmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path) -> None:
        ...