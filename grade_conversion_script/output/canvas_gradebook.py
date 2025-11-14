import enum
import inspect
from pathlib import Path
from typing import *  # pyright: ignore[reportWildcardImportFromLibrary]

import pandas as pd
import pandera.pandas as pa
from pandas.api.types import is_integer_dtype
from pandera.typing import DataFrame

from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.custom_types import Matcher, StudentPtsById
from grade_conversion_script.util.funcs import associate_unrecognized_entities, \
    best_effort_is_name, contains_row_for, reindex_to
from grade_conversion_script.util.tui import default_warning_printer, interactive_alias_match
from .base import OutputFormat


class CanvasGradebookOutputFormat(OutputFormat):
    '''
    Output a Canvas Gradebook CSV file for import.

    >>> student_ar = AliasRecord()
    >>> gradebook_csv = pd.DataFrame({
    ...     'Student'     : ["Name One (copy 2)",],
    ...     'ID'          : [None               ,],
    ...     'SIS Login ID': ["name1"            ,],
    ...     'Section'     : [None               ,],
    ...     'Assignment 1': [1                  ,],
    ... })
    >>> def raise_if_match(*args, **kwargs) -> str:
    ...     from itertools import chain
    ...     if any(obj for obj in chain(args, kwargs.values())):
    ...         raise Exception("Matching not expected")
    ...     return dict()
    >>> cgradebook_output = CanvasGradebookOutputFormat(
    ...     gradebook_csv,
    ...     'Assignment 1',
    ...     student_ar,
    ...     unrecognized_name_match=raise_if_match,
    ...     sum=True,
    ...     if_existing=CanvasGradebookOutputFormat.ReplaceBehavior.INCREMENT,
    ...     warn_existing=True
    ... )

    >>> student_ar.add_together(['name1', 'Name One (copy 1)'])
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

    >>> new_csv = cgradebook_output.format(grades) # doctest: +ELLIPSIS
    Incrementing existing grade values:
        1	(adding: 7,	student: Name One (copy ...))
    >>> print(new_csv[['SIS Login ID', 'Assignment 1']].to_string(index=False))
    SIS Login ID  Assignment 1
           name1             8
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
                 student_aliases: AliasRecord,
                 unrecognized_name_match: Matcher[str, str] = interactive_alias_match,
                 *,
                 sum: bool = False,
                 if_existing: ReplaceBehavior = ReplaceBehavior.ERROR,
                 warn_existing: bool = True,
                 warn_existing_handler: Callable[[Sequence[str]], None] = default_warning_printer,):
        '''
        Args:
            gradebook_csv:
                Direct CSV-read DataFrame of a Canvas exported gradebook.
                Columns of the input grades CSV file that are
                required to update the attendance assignment on Canvas.
                # See https://community.canvaslms.com/t5/Instructor-Guide/How-do-I-import-grades-in-the-Gradebook/ta-p/807.
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
        super().__init__(student_aliases)

        self.gradebook = gradebook_csv

        if assignment_header not in self.gradebook.columns:
            raise ValueError(f"No column with name {assignment_header}"
                             f" found in gradebook DataFrame.")
        self.assignment_column_label = assignment_header

        self.sum = sum
        self.if_existing = if_existing
        self.warn_existing = warn_existing

        self.unrecognized_name_match = unrecognized_name_match
        self.warning_handler = warn_existing_handler

    def merge_conflict_values(self, existing: pd.Series, incoming: pd.Series, index_to_alias_id: pd.Series) -> tuple[pd.Series, Sequence[str] | None] | NoReturn:
        '''
        Args should have identical indices
        and be only the conflicting region
        of the full "existing" df.

        Returns:
        * Same-indexed series as args,
            with values to set in parent DataFrame.
        * Message to print if user requested warnings for conflicts.
        '''
        # constants
        tab = "\t"
        def conflicts_detail():
            for row in pd.DataFrame({"existing": existing, "incoming": incoming}).itertuples():
                alias_id = index_to_alias_id[row.Index]
                assert is_integer_dtype(alias_id)
                student_name = self.student_aliases.best_effort_alias(best_effort_is_name, id=int(alias_id))
                yield (row.existing, row.incoming, student_name)

        pd.testing.assert_index_equal(existing.index, incoming.index)

        if existing.empty:
            return (existing, None)

        match self.if_existing:
            case self.ReplaceBehavior.REPLACE:
                values = incoming
                message = [
                    f"Replacing existing grade values:",
                    *(
                        tab.join((
                            f"{existing_val}",
                            f"(new: {new_val},",
                            f"student: {student_name})",
                        ))
                        for existing_val, new_val, student_name
                        in conflicts_detail()
                    )
                ]
            case self.ReplaceBehavior.PRESERVE:
                values = existing
                message = [
                    f"Preserving existing grade values:",
                    *(
                        tab.join((
                            f"{existing_val}",
                            f"(student: {student_name})",
                        ))
                        for existing_val, _, student_name
                        in conflicts_detail()
                    )
                ]
            case self.ReplaceBehavior.INCREMENT:
                values = pd.to_numeric(existing, errors='raise') + pd.to_numeric(incoming, errors='raise')
                message = [
                    f"Incrementing existing grade values:",
                    *(
                        tab.join((
                            f"{existing_val}",
                            f"(adding: {new_val},",
                            f"student: {student_name})",
                        ))
                        for existing_val, new_val, student_name
                        in conflicts_detail()
                    )
                ]
            case self.ReplaceBehavior.ERROR:
                message = [
                    f"Unexpected existing grade values:",
                    *(
                        tab.join((
                            f"{existing_val}",
                            f"(student: {student_name})",
                        ))
                        for existing_val, _, student_name
                        in conflicts_detail()
                    )
                ]
                raise ValueError(message)

        return (values, message if self.warn_existing else None)

    @override
    @pa.check_types
    def format(self, grades: DataFrame[StudentPtsById]) -> pd.DataFrame:
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
                raise ValueError(
                    "Too many columns. See this method's docstring:"
                    "\n" + str(inspect.getdoc(self.format))
                )

        # Prepare input Series (grades)
        grades_series = grades.squeeze('columns') # create a series
        assert isinstance(grades_series, pd.Series) # make sure we didn't squeeze into a DataFrame or scalar

        # Prepare output DataFrame (new_gradebook)
        new_gradebook = self.gradebook[[
            # See https://community.canvaslms.com/t5/Instructor-Guide/How-do-I-import-grades-in-the-Gradebook/ta-p/807.
            'Student', 'ID', 'SIS Login ID', 'Section',
            self.assignment_column_label
        ]].copy()

        # Perform name/id matching
        gb_alias_cols = ['Student', 'SIS Login ID']
        associate_unrecognized_entities(
            self.student_aliases,
            self.unrecognized_name_match,
            input_ids=grades.index,
            dest_alias_lists=(
                list[str](series)
                for _, series in new_gradebook[gb_alias_cols].iterrows()
            )
        )

        # Reindex grades to align with output
        id_by_gb_row = self.student_aliases.id_of_df(
            new_gradebook,
            gb_alias_cols,
            expect_new_entities=True,
            collect_new_aliases=True
        )
        incoming_grades_aligned = reindex_to(
            to_realign=grades_series,
            target_ids=id_by_gb_row
        )

        # Resolve + Set values (handle if_existing, warn_existing)

        # determine which rows are conflicting
        gb_loc_has_existing: pd.Series = new_gradebook[self.assignment_column_label].notna()
        gb_loc_has_incoming: pd.Series = contains_row_for(incoming_grades_aligned, new_gradebook)

        # set conflicting
        gb_loc_conflicting = gb_loc_has_existing & gb_loc_has_incoming
        conflict_vals, warning_msg = self.merge_conflict_values(
            existing = new_gradebook.loc[gb_loc_conflicting, self.assignment_column_label],
            incoming = incoming_grades_aligned[gb_loc_conflicting],
            index_to_alias_id = id_by_gb_row,
        )
        new_gradebook.loc[gb_loc_conflicting, self.assignment_column_label] = conflict_vals
        if warning_msg:
            self.warning_handler(warning_msg)

        # set non-conflicting
        gb_loc_non_conflicting = (~gb_loc_has_existing) & gb_loc_has_incoming
        new_gradebook.loc[gb_loc_non_conflicting, self.assignment_column_label] = (
            incoming_grades_aligned[gb_loc_non_conflicting]
        )

        # Return, asserts
        pd.testing.assert_frame_equal(
            self.gradebook[[*new_gradebook.columns]].fillna('')
                .drop(self.assignment_column_label, axis='columns', inplace=False),
            new_gradebook.fillna('')
                .drop(self.assignment_column_label, axis='columns', inplace=False),
            check_dtype = False,
        )
        return new_gradebook
    
    @override
    @classmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path):
        # Save output grades CSV file.
        self_output.to_csv(filepath, index=False)