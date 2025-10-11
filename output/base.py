from abc import ABC, abstractmethod

from typing import *
from pathlib import Path
import pandas as pd
from pandera.typing import DataFrame
from util.types import PtsBy_StudentSisId

class OutputFormat(ABC):
    '''
    Process grades from a DataFrame modeled by `PtsBy_StudentSisId`,
    to a specific import format for a gradebook service.
    
    Constraint:
        Subclasses need a separate instance for each Canvas assignment.
    '''
    @abstractmethod
    def format(self, grades: DataFrame[PtsBy_StudentSisId]) -> pd.DataFrame:
        ...
    @classmethod # seems cannot be static to work properly with inheritance
    @abstractmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path) -> None:
        ...