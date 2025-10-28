import pandas as pd
from pathlib import Path
from .base import OutputFormat

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
import pandera.pandas as pa
from pandera.typing import DataFrame

from util.types import PtsBy_StudentSisId, DataBy_StudentSisId
from util import AliasRecord

class AcrOutputFormat(OutputFormat):
    '''
    Auto Canvas Rubric Chrome extension format.
    
    >>> name_sis_id = NameSisIdConverter()
    >>> name_sis_id.add(sis_id='name1', name='Name One')
    >>> acr_output = AcrOutputFormat(name_sis_id)
    >>> grades = pd.DataFrame({ 'sis_id': ['name1',],
    ...                         'crit1':  [3,],
    ...                         'crit2':  [4,], 
    ...             }).set_index('sis_id')
    >>> acr_output.format(grades)
              Name One
    criteria          
    crit1            3
    crit2            4
    '''
        
    def __init__(self, name_sis_id_converter: NameSisIdConverter):
        super().__init__()
        self.name_sis_id_converter = name_sis_id_converter

    @override
    @pa.check_types
    def format(self, grades: DataFrame[PtsBy_StudentSisId]) -> pd.DataFrame:
        '''
        Args:
            grades:
                One column per rubric criteria.
                One row per student.
        Returns:
            A dataframe which can be saved to file with self.write_file
        '''
        # Reindex by student name
        arg = cast(DataFrame[DataBy_StudentSisId], grades)
        name_idx_grades = self.name_sis_id_converter.reindex_by_name(arg)

        # Go from (one row per name, one column per rubric criteria)
        # to (one column per name, one row per rubric criteria)
        criteria_idx_grades = name_idx_grades.transpose()
        # For index's header (see method docstring)
        criteria_idx_grades.rename_axis("criteria", axis='index', inplace=True)
        criteria_idx_grades.rename_axis(None, axis='columns', inplace=True)
        
        return criteria_idx_grades
    
    @override
    @classmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path) -> None:
        self_output.to_csv(filepath, index=True, header=True)