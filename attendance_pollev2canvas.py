import argparse
import math
import re
import enum
from pathlib import Path
from abc import ABC, abstractmethod

import pandas as pd

from typing import *
import numbers
import pandas.api.types as pd_types
import pandera.pandas as pa
from pandera.typing import DataFrame

#region Utility

def to_real_number(value: str) -> numbers.Real:
    if '.' in value:
        out = float(value)
    else:
        out = int(value)
    return cast(numbers.Real, out)

class EnumAction(argparse.Action):
    """
    Argparse action for handling Enums
    """
    def __init__(self, **kwargs):
        # Pop off the type value
        enum_type = kwargs.pop("type", None)

        # Ensure an Enum subclass is provided
        if enum_type is None:
            raise ValueError("type must be assigned an Enum when using EnumAction")
        if not issubclass(enum_type, enum.Enum):
            raise TypeError("type must be an Enum when using EnumAction")

        # Generate choices from the Enum
        kwargs.setdefault("choices", tuple(e.name for e in enum_type))

        super(EnumAction, self).__init__(**kwargs)

        self._enum = enum_type

    def __call__(self, parser, namespace, values, option_string=None):
        # Convert value back into an Enum
        assert values and not isinstance(values, Sequence)
        value = self._enum[values]
        setattr(namespace, self.dest, value)

class SisId(str):
    ''' A Canvas SIS Login ID (i.e. UNC Charlotte username) '''
    
    def __new__(cls, value):
        if cls.validate(value) != True:
            raise ValueError(f"Not a valid SIS ID: {value}")
        return super().__new__(cls, value)

    @classmethod
    def validate(cls, instance: Any) -> TypeGuard[Self]:
        '''
        sis_id is a UNC Charlotte email without the @charlotte.edu
        >>> validate(True)
        False
        >>> validate("mname3")
        True
        >>> validate("mname")
        True
        >>> validate("3")
        False
        '''
        
        if not isinstance(instance, str):
            return False

        if '@' in instance:
            return False
        
        pattern: re.Pattern = re.compile(r'[a-z]+[0-9]*')
        if (not pattern.fullmatch(instance)):
            return False

        return True

    @classmethod
    def from_email(cls, email: str) -> Self:
        '''
        >>> from_email("mname3@charlotte.edu")
        "mname3"
        '''
        sis_login_id, email_domain = email.split('@')[0]
        if email_domain != "charlotte.edu":
            raise ValueError(f"Email {email} is not a UNC Charlotte email.")
        return cls(sis_login_id)
    
class DataBy_StudentSisId(pa.DataFrameModel):
    '''
    Models any DataFrame whose index is all instances of `SisId`.
    
    >>> df1 = pd.DataFrame({'col1': [1, 2, 3]}, index=["name1", "nametwo", "name3"])
    >>> validated = DataBy_StudentSisId.validate(df1, inplace=False)
    >>> df1 == validated_df
    True
    >>> df2 = pd.DataFrame({'col1': [1, 2, 3]}, index=["name1", "2", "name3"])
    >>> validated = DataBy_StudentSisId.validate(df2, inplace=False)
    Traceback (most recent call last):
    ...
    SchemaError
    '''
    sis_id: pa.typing.Index[str] = pa.Field(check_name=True)

    pa.Check(SisId.validate, 'sis_id', element_wise=True, ignore_na=False)

class BoolsBy_StudentSisId(DataBy_StudentSisId):
    '''
    Models any DataFrame indexed by `SisId`s and with
    columns of booleans.

    >>> df1 = pd.DataFrame({'col1': [True, False, True]}, index=["name1", "name2", "name3"])
    >>> validated = DataBy_StudentSisId.validate(df1, inplace=False)
    >>> df1 == validated_df
    True
    >>> df2 = pd.DataFrame({'col1': [True, False, 3]}, index=["name1", "name2", "name3"])
    >>> validated = DataBy_StudentSisId.validate(df2, inplace=False)
    Traceback (most recent call last):
    ...
    SchemaError
    '''
    class Config: # pyright: ignore[reportIncompatibleVariableOverride] | Intended way to config pandara
        dtype: bool

class PtsBy_StudentSisId(DataBy_StudentSisId):
    '''
    Models any DataFrame indexed by `SisId`s and with
    columns of numerical points.
    
    >>> df1 = pd.DataFrame({'col1': [1, 2, 3]}, index=["name1", "name2", "name3"])
    >>> validated = DataBy_StudentSisId.validate(df1, inplace=False)
    >>> df1 == validated_df
    True
    >>> df2 = pd.DataFrame({'col1': [1, False, 3]}, index=["name1", "name2", "name3"])
    >>> validated = DataBy_StudentSisId.validate(df2, inplace=False)
    Traceback (most recent call last):
    ...
    SchemaError
    '''
    class Config: # pyright: ignore[reportIncompatibleVariableOverride] | Intended way to config pandara
        dtype: numbers.Real

class NameSisIdConverter:
    def __init__(self):
        self._name_to_sis: dict[str, SisId] = {}
        self._sis_to_name: dict[SisId, str] = {}

    def __str__(self):
        return str(self._name_to_sis)
    
    def add(self, *, name: str, sis_id: SisId):
        if (name in self._name_to_sis.keys()
            or sis_id in self._sis_to_name.keys()):
            raise ValueError(f"Cannot add name/sis_id ({name}, {sis_id}). "
                             f"Call remove_name() or remove_sis_id() first.")
        self._name_to_sis[name] = sis_id
        self._sis_to_name[sis_id] = name

    def addFromCols(self, sis_ids: pd.Series[SisId], names: pd.Series[str]):
        assert sis_ids.index == names.index
        data = \
            pd.DataFrame.from_dict(
                {'sis_id': sis_ids, 'name': names},
                orient='columns'
            )
        for _, row in data.iterrows():
            self.add(
                sis_id=row['sis_id'],
                name=row['name']
            )

    def remove_name(self, name: str):
        sis_id = self._name_to_sis[name]
        del self._name_to_sis[name]
        del self._sis_to_name[sis_id]
        
    def remove_sis_id(self, sis_id: SisId):
        name = self._sis_to_name[sis_id]
        del self._name_to_sis[name]
        del self._sis_to_name[sis_id]

    def to_name(self, sis_id: SisId) -> str:
        return self._sis_to_name[sis_id]

    def to_sis_id(self, name: str) -> SisId:
        return self._name_to_sis[name]
    
    @overload
    def reindex_by_name(self, df: DataFrame[DataBy_StudentSisId]) -> pd.DataFrame: ...
    @overload
    def reindex_by_name(self, df: pd.DataFrame, sis_id_col: str) -> pd.DataFrame: ...
    @pa.check_types
    def reindex_by_name(self, df: pd.DataFrame, sis_id_col: Optional[str] = None) -> pd.DataFrame:
        '''
        Set the row index for a DataFrame which only contains
        values for `SisId`.

        Does not require the index of `df` to be set before
        this method call.
        Does not work in-place; returns a modified copy.

        Args:
            df: The `DataFrame`.
            sis_id_col:
                The name of the column in `df` which holds `SisId`s.
                If None, then use row index.
        Returns:
            A DataFrame indexed by Student Names.
            Does not reorder the rows, or modify columns
            (besides the index).
        '''
        df = df.copy()
        df['student_name'] = \
            (
                df[sis_id_col] if sis_id_col is not None
                else df.index.to_series()
            ) \
            .apply(
                self.to_name,
                inplace=False
            )
        df.set_index(
            'sis_id',
            drop=True, # ends up with unchanged columns
            verify_integrity=True,
            inplace=True
        )
        return df

    @pa.check_types
    def reindex_by_sis_id(self, df: pd.DataFrame, name_col: Optional[str] = None) -> DataFrame[DataBy_StudentSisId]:
        '''
        Set the row index for a DataFrame which only contains
        values for Student Names.

        Does not require the index of `df` to be set before
        this method call.
        Does not work in-place; returns a modified copy.

        Args:
            df: The `DataFrame`.
            name_col:
                The name of the column in `df` which holds
                student names.
                If None, then use row index.
        Returns:
            A DataFrame indexed by `SisId`s.
            Does not reorder the rows, or modify columns
            (besides the index).

        >>> converter = NameSisIdConverter()
        >>> NameSisIdConverter().add(sis_id="name1",name="Student Name")
        >>> df1 = pd.DataFrame({"id": ["name1",], "st_name":["Name One",]})
        >>> df2 = df1.reindex("id", drop=True, inplace=False)
        >>> converter.reindex_by_sis_id(df1, "st_name")
                  id       st_name
        name1  name1  Student Name
        >>> converter.reindex_by_sis_id(df2)
                    st_name
        name1  Student Name
        '''
        df = df.copy()
        df['sis_id'] = \
            (
                df[name_col] if name_col is not None
                else df.index.to_series()
            ) \
            .apply(
                self.to_sis_id,
                inplace=False
            )
        df.set_index(
            'sis_id',
            drop=True, # ends up with unchanged columns
            verify_integrity=True,
            inplace=True
        )
        return DataFrame[DataBy_StudentSisId](df)

def interactive_name_sis_id_match(out: NameSisIdConverter, *, names_to_match: Iterable[str], sis_ids_to_match: Iterable[SisId]) -> None:
    '''
    Ask the user to match student names and SIS IDs.
    Stores provided info persistently in provided data structure.

    Not all names or SIS IDs are necessarily matched.
    However, no names or SIS IDs should have existing mappings in `out`. TODO wtf

    Args:
        names_to_match:
            Student names which do not have a known corresponding SIS ID.
        sis_ids_to_match:
            SIS IDs which do not have a known corresponding name.
        out:
            Record in which to store new mappings.
    '''

    names = list(names_to_match) # we need to mutate for internal processing
    for sis_id in sis_ids_to_match:
        start_idx = 1
        print_enumerated(names, start_idx)
        
        prompt_header(sis_id)
        selection_idx = prompt_selection_idx(start_idx)
        selection_str = names.pop(selection_idx)

        out.add(name=selection_str, sis_id=sis_id)

def interactive_rubric_criteria_match(given_labels: Sequence[str], dest_labels: Sequence[str]) -> dict[str, str]:
    '''
    Ask the user to match student names and SIS IDs.
    Stores provided info persistently in provided data structure.
    
    Because not all rubric criteria must be filled,
    `given_labels` can have less but not more values than
    `dest_labels`.

    Args:
        given_labels:
            List of criteria names provided by user as unverified input.
        dest_labels:
            List of criteria names stipulated by destination format.
    Returns:
        Mapping of given values.
        
        keys:
            Members of `given_labels`.
        vals:
            Members of `dest_labels`.
    '''
    assert len(given_labels) <= len(dest_labels)

    out = dict()
    dest_labels = list(dest_labels) # we need to mutate for internal processing
    for given_label in given_labels:
        prompt_header(given_label)
        start_idx = 1
        print_enumerated(dest_labels, start_idx)
        
        selection_idx = prompt_selection_idx(start_idx)
        selection_str = dest_labels.pop(selection_idx)

        out[given_label] = selection_str
    return out

#endregion Utility
#region Input format handlers

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

class AttendancePollEv(InputHandler):
    '''
    Abstracts the reading of attendance from PollEverywhere CSV.
    Input:  data with external schema (PollEverywhere export).
    Output: data with internally guaranteed schema.

    >>> name_sis_id = NameSisIdConverter()
    >>> attendance_input = AttendancePollEv(2, name_sis_id)
    >>> pollev_df = pd.DataFrame({'First Name': ['Name','Name'],
                                  'Last Name' : ['One', 'Two'],
                                  'Email'     : ['name1@charlotte.edu','name2@charlotte.edu'],
                                  'Grade'     : [99   ,  0]})
    >>> attendance_input.get_scores(pollev_df)
    sis_id  attended
     name1      True
     name2     False 
    >>> str(name_sis_id)
    {"Name One": "name1", "Name Two": "name2"}
    '''

    def __init__(self, pts_per_day: numbers.Real, name_sis_id_store: NameSisIdConverter):
        ''' Set options which vary among input-handlers here. '''
        super().__init__(name_sis_id_store)
        self.pts_per_day = pts_per_day

    @pa.check_types
    def get_single_day_attendance(self, pollev_day: pd.DataFrame) -> DataFrame[BoolsBy_StudentSisId]:
        '''
        Args:
            pollev_day: Dataframe from one PollEv export CSV.
        Returns:
            A one-column DataFrame modeled by `DataBy_StudentSisId`.
            Values are all type `bool`.
            The column has the generic label 'attended'.
        '''

        # Each row corresponds to one student and their response.
        # Do not iterate over the last two rows, since these
        # only contain average information.
        student_rows = pollev_day[:-2]

        # Double-check that the last 2 rows are, in fact, not students
        average_rows = pollev_day[-2:]
        average_rows_column1 = average_rows.iloc(axis='columns')[0]
        assert all( "average" in csv_row_label
                    for csv_row_label in average_rows_column1.str.lower() )

        # Determine attendance by student
        def has_attended(student_row):
            # check rule is defined here
            return student_row['Grade'].to_numeric() != 0
        attendance = student_rows \
                        .apply(
                            has_attended,
                            axis='columns' # passes one row to function at a time
                        )
        
        # Output formatting
        # set index
        sis_ids = student_rows['Email'] \
                    .apply(SisId.from_email)
        attendance = attendance.set_axis(sis_ids, axis='index')
        # set labels
        attendance = attendance \
                        .rename("attended") \
                        .rename_axis("sis_id", axis='index')
        # convert Series to DataFrame
        assert isinstance(attendance, pd.Series)  
        attendance = attendance.to_frame()
        
        # Populate Name/SisId store
        student_names: pd.Series = student_rows[['First name', 'Last name']].agg(' '.join, axis='columns')
        self.name_sis_id_store.addFromCols(sis_ids=sis_ids, names=student_names)

        return DataFrame[BoolsBy_StudentSisId](attendance)

    @pa.check_types
    def get_multi_day_attendance(self, pollev_days: dict[str, pd.DataFrame]) -> DataFrame[BoolsBy_StudentSisId]:
        '''
        Args:
            pollev_days: Dataframe from PollEv export CSVs.
                keys: Labels for each PollEv export.
                vals: DataFrames of PollEv export CSV
                      (each is one day of attendance).
        Returns:
            A multi-column dataframe modeled by `DataBy_StudentSisId`.
            Values are all type `bool`.
            One column exists for each entry in the input dict,
            with the given label.
            The columns are in the same order as the dict's
            insertion order.
        '''
        # Create a column for each day of attendance.
        def csv_to_column(col_label, csv: pd.DataFrame) -> pd.Series[bool]:
            attendance_df = self.get_single_day_attendance(csv) # process into bools
            series = attendance_df['attended'] # turn into series
            series.name = col_label # rename with intended column label
            return series
        cols: Iterable[pd.Series]
        cols = (csv_to_column(day_label, csv)
                for day_label, csv in pollev_days.items())
        # Merge the single-day DataFrames in the dict.
        attendance_multi_day = pd.concat(cols, axis='columns', verify_integrity=True)
        
        # Replace NaNs with False.
        # Pandas uses NaN during the merge of columns by index (i.e. sis_id)
        # to show that a row was not present for that column.
        attendance_multi_day.fillna(False)

        # Assert column order.
        expected_column_names: list[str] = list(pollev_days.keys())
        actual_column_names: list[str] = attendance_multi_day.columns.to_list()
        assert expected_column_names == actual_column_names

        return DataFrame[BoolsBy_StudentSisId](attendance_multi_day)
    
    @pa.check_types
    def attendance_bool_to_pts(self, attendance_bools: DataFrame[BoolsBy_StudentSisId]) -> DataFrame[PtsBy_StudentSisId]:
        '''
        Replaces boolean attendence values (i.e. per-student, per-day)
        with defined per-class point value configured with `__init__()`.

        Args:
            attendance_cols: DataFrame of only `bool` values,
            corresponding to whether a student attended class.
        Returns:
            A DataFrame of same shape, index, and labels as input,
            but with int or float values.
        '''
        # Check input DataFrame
        assert len(attendance_bools.dtypes) == 1
        assert attendance_bools.dtypes.iloc[0] == bool

        # Create DataFrame with output type
        dest_type = type(self.pts_per_day)
        attendance_pts = attendance_bools.astype(dest_type) # 0s and 1s

        # Fill in the points
        attendance_pts = attendance_pts * self.pts_per_day

        # Check output formatting
        assert attendance_pts.index == attendance_bools.index
        assert attendance_pts.columns == attendance_bools.columns

        return DataFrame[PtsBy_StudentSisId](attendance_pts)
    
    @override
    @pa.check_types
    def get_scores(self, csv: pd.DataFrame | dict[str, pd.DataFrame]) -> DataFrame[PtsBy_StudentSisId]:
        '''
        Args:
            csv:
                `DataFrame`s from input CSV files.
                If a `dict` is provided, each key is the label
                for that file's column in the output DataFrame.
        Returns:
            A dataframe modeled by PtsBy_StudentSisId.
            If one CSV was provided (i.e. one day),
            output has 1 column, labeled 'attendance'.
        '''
        if isinstance(csv, dict):
            attendance_bools = self.get_multi_day_attendance(csv)
        else:
            attendance_bools = self.get_single_day_attendance(csv) \
                                   .rename(columns={'attended': 'attendance'})

        attendance_pts = self.attendance_bool_to_pts(attendance_bools)

        return attendance_pts

#endregion Input format handlers
#region Output format handlers

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

class CanvasGradebookOutputFormat(OutputFormat):
    '''
    Output a Canvas Gradebook CSV file for import.
    
    >>> gradebook_csv = pd.DataFrame({'SIS Login ID': ["name1",],
    ...                               'Assignment Name': [1,]})
    >>> cgradebook_output = CanvasEnhancedRubricOutputFormat(gradebook_csv, 'Assignment Name', sum=True, if_existing=CanvasGradebookOutputFormat.ReplaceBehavior.INCREMENT, warn_existing=True)
    >>> grades = pd.DataFrame({'sis_id': ['name1',],
    ...                        'Pts pt. 1': [1,],
    ...                        'Pts pt. 2': [2,]})
    >>> new_csv = cgradebook_output.format(grades)
    Incrementing grade value of 1 for new total grade 4 for student with ID name1.
    >>> print(new_csv[['Student Name', 'Criterion 1', 'Criterion 2']])
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
        new_gradebook = self.gradebook[['Student', 'ID', 'SIS Login ID', 'Section', self.assignment_column_label]].copy()
        assert pd_types.is_string_dtype(new_gradebook.loc(axis='columns')[self.assignment_column_label])

        # Iterate by student
        for curr_sis_id, param_grade in one_col_grades.items():
            # Establish types
            assert SisId.validate(curr_sis_id)
            assert isinstance(param_grade, numbers.Real)

            # Get the row of the output gradebook DataFrame
            # which corresponds to the student.
            matching_row_idxs = \
                new_gradebook.index[ 
                    new_gradebook['SIS Login ID'] == curr_sis_id 
                ]
            assert len(matching_row_idxs) == 1
            gradebook_row_idx = matching_row_idxs[0]
            gradebook_row = new_gradebook.iloc[gradebook_row_idx]
            
            # Determine new grade.
            existing_grade = float(gradebook_row[self.assignment_column_label])
            if pd.isna(existing_grade):
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
                            # TODO why were we rounding the grade first (see original code)?
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
            new_gradebook.loc[gradebook_row_idx, self.assignment_column_label] \
                = f"{new_grade:.2f}"
                        # TODO why were we accessing loc with 'i' (see original code)?

        assert self.gradebook.drop(self.assignment_column_label, inplace=False) \
                .equals(
                    new_gradebook.drop(self.assignment_column_label, inplace=False)
                )

        return new_gradebook
    
    @override
    @classmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path):
        # Save output grades CSV file.
        self_output.to_csv(filepath, index=False)

class AcrOutputFormat(OutputFormat):
    '''
    Auto Canvas Rubric Chrome extension format.
    
    >>> name_sis_id = NameSisIdConverter()
    >>> name_sis_id.add(sis_id='name1', name='Name One')
    >>> acr_output = AcrOutputFormat(name_sis_id)
    >>> grades = pd.DataFrame({'sis_id': ['name1',], 'crit1': [3,], 'crit2': [4,]})
    >>> print(acr_output.format(grades))
    criteria,Name One
    crit1,3
    crit2,4
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
        # For index's header (see this method's docstring)
        criteria_idx_grades.rename_axis("criteria", axis='index')
        
        return criteria_idx_grades
    
    @override
    @classmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path) -> None:
        self_output.to_csv(filepath, index=True, header=True)
    
class CanvasEnhancedRubricOutputFormat(OutputFormat):
    '''
    Populate an Enhanced Rubric file generated by Canvas.

    >>> name_sis_id = NameSisIdConverter()
    >>> name_sis_id.add(sis_id='name1', name='Name One')
    >>> rubric_csv = pd.DataFrame({'Student Name': ["Name One",],
    ...                            'Criterion 1 - Rating': [,], 'Criterion 1 - Points': [,], 'Criterion 1 - Comments': [,],
    ...                            'Criterion 2 - Rating': [,], 'Criterion 2 - Points': [5,], 'Criterion 2 - Comments': ["excused",]})
    >>> cerubric_output = CanvasEnhancedRubricOutputFormat(rubric_csv, name_sis_id, replace_existing=False, warn_existing=True)
    >>> grades = pd.DataFrame({'sis_id': ['name1',], 'Criterion 1': [3,], 'Criterion 2': [4,]})
    >>> new_csv = cerubric_output.format(grades)
    Keeping old grade of 5 at name1, Criterion 2 (Rating "" and Comment "excused")
    >>> print(new_csv[['Student Name', 'Criterion 1', 'Criterion 2']])
    Student Name  Criterion 1  Criterion 2
        Name One            3            5
    '''

    def __init__(self, rubric_csv: pd.DataFrame, name_sis_id_converter: NameSisIdConverter, replace_existing: bool, warn_existing: bool):
        super().__init__()
        self.name_sis_id_converter = name_sis_id_converter
        
        self.name_aliases = dict() # keep track of new names
        interactive_name_sis_id_match(real: self.rubric, given: self.name_sis_id_converter, out: self.name_aliases) # TODO doesn't this need to happen somewhere else too?
        
        self.rubric_template = self.name_sis_id_converter.reindex_by_sis_id \
                                                    (rubric_csv, 'Student Name')
        
        self.replace_existing = replace_existing
        self.warn_existing = warn_existing

    @override
    @pa.check_types
    def format(self, grades: DataFrame[PtsBy_StudentSisId]) -> pd.DataFrame:
        '''
        Args:
            grades:
                One column per rubric criteria.
                One row per student.
        Returns:
            A dataframe which can be saved to file with self.write_file().
        '''
        user_criteria = list(grades.columns.astype(str))
        canvas_criteria = list( )
        .map(interactive_rubric_criteria_match(real:, given:, out: ))
        
        self.name_aliases # we need to make use of this somewhere here

        new_rubric = self.rubric_template.copy()
        
        # Iterate by both axes in `grades` dataframe
        grades_iterator: Iterable = \
        (
            (cast(SisId, student), cast(str, criterion_name), cast(numbers.Real, grade))
            for student, criteria_scores
                in grades.iterrows()
            for criterion_name, grade
                in criteria_scores.items()
        )
        for student_idx, criterion_idx, param_score in grades_iterator:
            # Get corresponding columns in Canvas enhanced rubric CSV
            SemanticLabel = enum.Enum('SemanticLabel', ['PTS_LABEL', 'PTS', 'COMMENTS'])
            criterion_csv_headers: dict[SemanticLabel, str] = \
            {
                semantic_label: criterion_idx + suffix
                for semantic_label, suffix in {
                                        # These go after the criterion name
                                        SemanticLabel.PTS_LABEL: " - Rating",
                                        SemanticLabel.PTS      : " - Points",
                                        SemanticLabel.COMMENTS : " - Comments"
                                    }.items()
            }
            def get_curr_val(semantic_label: SemanticLabel) -> numbers.Real | str:
                col_header = criterion_csv_headers[semantic_label]
                value = new_rubric[student_idx, col_header].squeeze()
                assert isinstance(value, (numbers.Real, str))
                return value
            def set_curr_val(semantic_label: SemanticLabel, value: numbers.Real | str):
                col_header = criterion_csv_headers[semantic_label]
                new_rubric[student_idx, col_header] = value
            
            # Should we fill the current criterion for the current student?
            grade_already_present: bool = \
                any(
                    bool(get_curr_val(semantic_label))
                    for semantic_label in criterion_csv_headers.keys()
                )
            should_fill_curr = (not grade_already_present) or self.replace_existing

            # Print warning if requested
            should_warn_curr = self.warn_existing and grade_already_present
            if should_warn_curr:
                match should_fill_curr:
                    case True:
                        message = (
                            f'Replacing old grade of {get_curr_val(SemanticLabel.PTS)}'
                            f' with new grade {param_score} at {student_idx},'
                            f' {criterion_idx} (keeping Rating of "{get_curr_val(SemanticLabel.PTS_LABEL)}" '
                            f'and Comment of "{get_curr_val(SemanticLabel.COMMENTS)}")'
                        )
                    case False:
                        message = (
                            f'Keeping old grade of {get_curr_val(SemanticLabel.PTS)}'
                            f' at {student_idx}, {criterion_idx} (Rating'
                            f' "{get_curr_val(SemanticLabel.PTS_LABEL)}"'
                            f' and Comment "{get_curr_val(SemanticLabel.COMMENTS)}")'
                        )
                print(message)

            # Fill score for curr criterion & student
            if should_fill_curr:
                set_curr_val(SemanticLabel.PTS, param_score)
        
        modified_columns: Iterable[str] = (f"{criterion} - Points"
                                           for criterion in grades.columns)
        assert self.rubric_template.drop(modified_columns, inplace=False) \
                .equals(
                    new_rubric.drop(modified_columns, inplace=False)
                )

        return new_rubric
    
    @override
    @classmethod
    def write_file(cls, self_output: pd.DataFrame, filepath: Path) -> None:
        self_output.to_csv(filepath, index=False, header=True)

#endregion Output format handlers
#region __main__

if __name__ == '__main__':

    # Parse command-line arguments.
    parser = argparse.ArgumentParser(
        description='This script takes CSV grades from various sources'
                    ' (such as PollEverywhere results export)'
                    ' to create a new CSV file containing updated'
                    ' grades that can be imported to Canvas.')
    subparsers = parser.add_subparsers(dest='part_name', required=True)

    # Input/Output subparsers are both required
    input_parser = subparsers \
        .add_parser(
            'input', # stored under args['part_name']
            help="input format and corresponding options"
        )
    output_parser = subparsers \
        .add_parser(
            'output', # stored under args['part_name']
            help="output format and corresponding options"
        )
    
    # Input formats are mutually exclusive
    input_subparsers = input_parser.add_subparsers(dest='input_format')
    input_parser \
    .set_defaults(
        input_csvs=[item.name # all files in directory
                    for item in Path(".").iterdir()
                    if item.is_file()]
    )
    # PollEv attendance
    pollev_attendance_cmd = input_subparsers \
        .add_parser(
            'pollev_attendance', # stored under args['input_format']
            help="generate student attendance from PollEv export"
        )
    pollev_attendance_cmd \
    .add_argument(
        'attendance_points',
        type=to_real_number,
        help='# of points per student per day (int or float)'
    )
    pollev_attendance_cmd \
    .add_argument(
        'input_csvs',
        type=str,
        action='extend',
        nargs='+',
        help='one or more PollEverywhere results CSV files corresponding'
             ' to attendance on one or more days'
    )

    # Output formats are mutually exclusive
    output_subparsers = output_parser.add_subparsers(dest='output_format')
    output_parser \
    .add_argument( # add an argument which applies to all output formats
        'output_grades_csv',
        type=str,
        help='output file location',
        default='grades_out.csv'
    )
    # Canvas Gradebook CSV
    c_gradebook_cmd = output_subparsers \
        .add_parser(
            'c_gradebook', # stored under args['input_format']
            help='fill a Canvas Gradebook export to reupload'
        )
    c_gradebook_cmd \
    .add_argument(
        'csv_template',
        type=str,
        help='a grades CSV file exported from Canvas'
    )
    c_gradebook_cmd \
    .add_argument(
        'header',
        type=str,
        help='the header of the column corresponding to the'
             ' attendance assignment in the grades CSV file,'
             ' for example, "Attendance (2577952)"'
    )
    c_gradebook_cmd \
    .add_argument(
        '--if-existing',
        type=CanvasGradebookOutputFormat.ReplaceBehavior,
        action=EnumAction,
        dest='if_existing',
        help='Behavior for existing grades in gradebook file'
    )
    c_gradebook_cmd \
    .add_argument(
        '--warn-existing',
        type=bool,
        action='store_true',
        dest='warn_existing',
        help='warn if a grade to be filled already'
            ' exists (even if it is not replaced).'
    )
    # Auto Canvas Rubric
    acr_cmd = output_subparsers \
        .add_parser(
            'acr', # stored under args['input_format']
            help='create a file which can be loaded into'
                 ' Auto Canvas Rubric Chrome extension'
        )
    # Canvas Enhanced Rubric CSV
    c_enhanced_rubric_cmd = output_subparsers \
        .add_parser(
            'e_rubric', # stored under args['input_format']
            help='fill a Canvas rubric export to reupload'
                ' (note: Enhanced Rubrics only)'
        )
    c_enhanced_rubric_cmd \
    .add_argument(
        'csv_template',
        type=str,
        help='a rubric CSV file exported from Canvas'
    )
    c_enhanced_rubric_cmd \
    .add_argument(
        '--replace',
        type=bool,
        action='store_true',
        dest='replace',
        help='whether to replace a grade that already'
            ' has a rating, grade, or comment'
    )
    c_enhanced_rubric_cmd \
    .add_argument(
        '--warn-existing',
        type=bool,
        action='store_true',
        dest='warn_existing',
        help='warn if a grade to be filled already'
             ' exists (even if it is not replaced).'
    )
    
    # Read all the arguments for one subparser (input or output), then the other
    
    args_1, rest = parser.parse_known_args()
    args_2, rest = parser.parse_known_args(rest)
    assert len(rest) == 0

    match hasattr(args_1, 'input_format'), hasattr(args_2, 'input_format'):
        case True, False:
            input_args = args_1
            output_args = args_2
        case False, True:
            output_args = args_1
            input_args = args_2
        case _:
            raise ValueError
    
    assert hasattr(input_args, 'input_format')
    assert hasattr(output_args, 'output_format')

    # Prepare input/output handler objects.
    
    shared_student_id_record = NameSisIdConverter()
    ''' Links `SisId`s and names as seen in the input file. '''
    input_is_attendance = bool(input_args.input_format in ('pollev_attendance',))

    input_handler: InputHandler
    match input_args.input_format:
        case 'pollev_attendance':
            input_handler = AttendancePollEv(
                pts_per_day=input_args.attendance_pts,
                name_sis_id_store=shared_student_id_record
            )
        case _:
            raise ValueError
    
    output_handler: OutputFormat
    match output_args.output_format:
        case 'c_gradebook':
            output_handler = CanvasGradebookOutputFormat(
                gradebook_csv=pd.read_csv(output_args.csv_template),
                assignment_header=output_args.header,
                sum=True, # This program only supports one assignment at a time
                if_existing=(output_args.if_existing
                             if output_args.if_existing is not None
                             else
                             CanvasGradebookOutputFormat.ReplaceBehavior.INCREMENT
                             if input_is_attendance
                             else CanvasGradebookOutputFormat.ReplaceBehavior.ERROR),
                warn_existing=(output_args.warn_on_existing
                                  if output_args.warn_on_existing is not None
                                  else not input_is_attendance)
            )
        case 'acr':
            output_handler = AcrOutputFormat(
                name_sis_id_converter=shared_student_id_record
            )
        case 'e_rubric':
            output_handler = CanvasEnhancedRubricOutputFormat(
                name_sis_id_converter=shared_student_id_record,
                rubric_csv=pd.read_csv(output_args.csv_template),
                replace_existing=(output_args.replace
                                  if output_args.replace is not None
                                  else False),
                warn_existing=(output_args.warn_on_existing
                               if output_args.warn_on_existing is not None
                               else input_is_attendance),
            )
        case _:
            raise ValueError
    
    # Read and process grades to internal format.
    input_dfs = {filename: pd.read_csv(filename)
                 for filename in input_args.input_csvs}
    scores = input_handler.get_scores(input_dfs)

    # Process and write grades to external format.
    out_df = output_handler.format(scores)
    output_handler.write_file(out_df, output_args.output_grades_csv)

#endregion __main__
