import enum
import pandas as pd
from pathlib import Path
from .base import OutputFormat

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
import numbers as num
import pandera.pandas as pa
from pandera.typing import DataFrame
from grade_conversion_script.util.funcs import is_pd_scalar, to_real_number
from grade_conversion_script.util.types import SisId, PtsBy_StudentSisId

class CanvasGradebookOutputFormat(OutputFormat):
    '''
    Output a Canvas Gradebook CSV file for import.
    
    >>> gradebook_csv = pd.DataFrame({'SIS Login ID': ["name1",],
    ...                               'Assignment Name': [1,]})
    >>> cgradebook_output = CanvasGradebookOutputFormat(gradebook_csv, 'Assignment Name', sum=True, if_existing=CanvasGradebookOutputFormat.ReplaceBehavior.INCREMENT, warn_existing=True)
    >>> grades = pd.DataFrame({
    ...                         'sis_id':    ['name1',],
    ...                         'Pts pt. 1': [1,      ],
    ...                         'Pts pt. 2': [2,      ],
    ...                     }).set_index('sis_id', drop=True)
    >>> new_csv = cgradebook_output.format(grades)
    Incrementing grade value of 1 for new total grade 4 for student with ID name1.
    >>> print(new_csv[['SIS Login ID', 'Assignment Name']].to_string(index=False))
    SIS Login ID  Assignment Name
           name1                4
    '''

    class ReplaceBehavior(enum.Enum):
        REPLACE = enum.auto()
        PRESERVE = enum.auto()

        INCREMENT = enum.auto()
        '''
        We add the the input grades to the
        original grades found in the gradebook for 
        this assignment, rather than replacing.
        '''

        ERROR = enum.auto()

    def __init__(self, gradebook_csv: pd.DataFrame, assignment_header: str,
                 sum: bool = False,
                 if_existing: ReplaceBehavior = ReplaceBehavior.ERROR,
                 warn_existing: bool = True):
        '''
        Args:
            gradebook_csv:
                Direct CSV-read DataFrame of a Canvas exported gradebook.
            assignment_header:
                The header label for the CSV gradebook column
                corresponding to this assignment's points.
            sum:
                Allow passing multiple columns of grades per student;
                they will be summed up to get the grade corresponding to 
                the assignment.
                Useful if columns correspond to the assignment's
                rubric criteria.
            if_existing:
                See `cls.ReplaceBehavior`.
            warn_existing:
                If True, then when modifying a student's existing grade
                for an assignment, notify with a message to the console.
        '''
        super().__init__()

        self.gradebook = gradebook_csv

        if assignment_header not in self.gradebook.columns:
            raise ValueError(f"No column with name {assignment_header}"
                             f" found in gradebook DataFrame.")
        self.assignment_column_label = assignment_header

        self.sum = sum
        self.if_existing = if_existing
        self.warn_existing = warn_existing

    @override
    @pa.check_types
    def format(self, grades: DataFrame[PtsBy_StudentSisId]) -> pd.DataFrame:
        '''
        Note: rounds the student's previous grade.
        Args:
            grades:
                The new grade to assign to each student.
                Must have one column if `self.sum` is False.
        '''
        if len(grades.columns) > 1:
            if self.sum:
                grades = DataFrame(grades.sum(axis='columns'))
            else:
                raise ValueError("See this method's docstring")

        # Prepare input
        one_col_grades = grades.squeeze('columns') # create a series
        assert isinstance(one_col_grades, pd.Series) # make sure we didn't squeeze into a DataFrame or scalar
        # Prepare output
            # Make a copy of the columns of the input grades CSV file that are
            # required to update the attendance assignment on Canvas.
            # See https://community.canvaslms.com/t5/Instructor-Guide/How-do-I-import-grades-in-the-Gradebook/ta-p/807.
        desired_cols = ('Student', 'ID', 'SIS Login ID', 'Section', self.assignment_column_label)
        available_desired_cols = filter(
            lambda col_name: col_name in desired_cols,
            self.gradebook.columns
        )
        new_gradebook = self.gradebook[[*available_desired_cols]].copy()

        # Iterate by student
        for curr_sis_id, param_grade in one_col_grades.items():
            # Establish types
            assert SisId.validate(curr_sis_id)
            assert isinstance(param_grade, num.Real)

            matching_row_idxs = \
                new_gradebook.index[ 
                    new_gradebook['SIS Login ID'] == curr_sis_id 
                ]
            if len(matching_row_idxs) == 0:
                print(f"Skipping {curr_sis_id} (student not in rubric)")
                continue

            # Get the row of the output gradebook DataFrame
            # which corresponds to the student.
            assert (
                (matches := len(matching_row_idxs))
                    == 1
            ), f"Found {curr_sis_id} {matches} times in gradebook"
            gradebook_row_idx = matching_row_idxs[0]
            gradebook_row = new_gradebook.iloc[gradebook_row_idx]
            assert isinstance(gradebook_row, pd.Series)
            
            # Determine new grade.
            existing_grade = to_real_number(gradebook_row[self.assignment_column_label])
            if pd.isna(cast(float | int, existing_grade)):
                new_grade = param_grade
            else:
                match self.if_existing:
                    case self.ReplaceBehavior.REPLACE:
                        new_grade = param_grade
                        message = (f"Replacing grade value of {existing_grade}"
                                   f" with new grade {new_grade} for student"
                                   f" with ID {curr_sis_id}.")
                    case self.ReplaceBehavior.PRESERVE:
                        new_grade = existing_grade
                        message = (f"Preserving grade value of {existing_grade}" 
                                   f" for student with ID {curr_sis_id}.")
                    case self.ReplaceBehavior.INCREMENT:
                        new_grade = existing_grade + param_grade
                            # TODO why did we increment by 1 and not by 2? (idek what this means and i wrote this comment myself)
                        message = (f"Incrementing grade value of" 
                                   f" {existing_grade} for new total grade" 
                                   f" {new_grade} for student with ID" 
                                   f" {curr_sis_id}.")
                    case self.ReplaceBehavior.ERROR:
                        raise ValueError(f"Existing grade value of"
                                         f" {existing_grade} for student"
                                         f" with ID {curr_sis_id}.")
                if self.warn_existing:
                    print(message)
            
            # Set new grade.
            if '.' in str(new_grade):
                # round decimals in case of float imprecision
                new_grade = round(new_grade, 2)
            assert is_pd_scalar(new_grade)
            new_gradebook.loc[gradebook_row_idx, self.assignment_column_label] \
                = new_grade
                # TODO why were we accessing loc with 'i' (see original code)?

        assert (
            self.gradebook[[*new_gradebook.columns]]
                .drop(self.assignment_column_label, axis='columns', inplace=False)
            .equals(
                new_gradebook
                    .drop(self.assignment_column_label, axis='columns', inplace=False)
            )
        )

        return new_gradebook
    
    @override
    @classmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path):
        # Save output grades CSV file.
        self_output.to_csv(filepath, index=False)