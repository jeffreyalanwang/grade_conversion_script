from abc import ABC, abstractmethod

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
from pathlib import Path
import pandas as pd
from pandera.typing import DataFrame
from util.types import PtsBy_StudentSisId
from util import NameSisIdConverter

class InputHandler(ABC):
    '''
    Process data with a specific format, using a specific behavior,
    to extract grades into a DataFrame modeled by `PtsBy_StudentSisId`.

    Subclasses must generate a `NameSisIdConverter`.
    '''
    @abstractmethod
    def __init__(self, name_sis_id_store: NameSisIdConverter):
        self.name_sis_id_store = name_sis_id_store

    @abstractmethod
    def get_scores(self, csv: pd.DataFrame | dict[str, pd.DataFrame]) -> DataFrame[PtsBy_StudentSisId]:
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
