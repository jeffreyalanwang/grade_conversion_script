import pandas as pd
from pathlib import Path

from .base import OutputFormat

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
import pandera.pandas as pa
from pandera.typing import DataFrame

from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.custom_types import StudentPtsById
from grade_conversion_script.util.funcs import best_effort_is_name

class AcrOutputFormat(OutputFormat):
    '''
    Auto Canvas Rubric Chrome extension format.
    
    >>> student_ar = AliasRecord()
    >>> acr_output = AcrOutputFormat(student_ar)

    >>> student_ar.add_together(['name1', 'Name One'])
    >>> student_ar.id_of('name1')
    400
    >>> grades = pd.DataFrame({
    ...     'id'   : [400,],
    ...     'crit1': [3,  ],
    ...     'crit2': [4,  ],
    ... }).set_index('id', drop=True)
    >>> grades
         crit1  crit2
     id
    400      3      4

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
        # Reindex by student name, or best-effort identifier
        best_effort_names = grades.index.to_series().map(
            lambda id:
                self.student_aliases.best_effort_alias(
                    best_effort_is_name,
                    id=id
                ),
        ).rename('name')
        grades_by_name = pd.concat(
            [grades, best_effort_names],
            axis='columns'
        ).set_index('name', drop=True, inplace=False)

        # Go from (one row per name, one column per rubric criteria)
        # to (one column per name, one row per rubric criteria)
        grades_by_criteria = grades_by_name.transpose()

        # For index's header
        grades_by_criteria.rename_axis("criteria", axis='index', inplace=True)
        grades_by_criteria.rename_axis(None, axis='columns', inplace=True)
        
        return grades_by_criteria
    
    @override
    @classmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path) -> None:
        self_output.to_csv(filepath, index=True, header=True)