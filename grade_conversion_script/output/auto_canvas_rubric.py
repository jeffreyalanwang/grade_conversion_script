import pandas as pd
from pathlib import Path

from .base import OutputFormat

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
import pandera.pandas as pa
from pandera.typing import DataFrame

from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.types import StudentPtsById
from grade_conversion_script.util.funcs import best_effort_is_name

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
        
    def __init__(self, student_aliases: AliasRecord):
        super().__init__(student_aliases)

    @override
    @pa.check_types
    def format(self, grades: DataFrame[StudentPtsById]) -> pd.DataFrame:
        '''
        Args:
            grades:
                One column per rubric criteria.
                One row per student.
        Returns:
            A dataframe which can be saved to file with self.write_file
        '''
        # Reindex by student name, or best-effort identifier
        grades_by_name = cast(
            pd.DataFrame,
            grades.reindex(
                index=grades.index.map(
                    lambda id:
                        self.student_aliases.best_effort_alias(
                            best_effort_is_name,
                            id=id
                        ),
                ),
                copy=False
            )
        )

        # Go from (one row per name, one column per rubric criteria)
        # to (one column per name, one row per rubric criteria)
        grades_by_criteria = grades_by_name.transpose()
        # For index's header (see method docstring)
        grades_by_criteria.rename_axis("criteria", axis='index', inplace=True)
        grades_by_criteria.rename_axis(None, axis='columns', inplace=True)
        
        return grades_by_criteria
    
    @override
    @classmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path) -> None:
        self_output.to_csv(filepath, index=True, header=True)