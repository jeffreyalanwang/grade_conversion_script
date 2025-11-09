from enum import Enum
from typing import *  # pyright: ignore[reportWildcardImportFromLibrary]

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaError

IndexFlag = Enum('IndexFlag', 'Index')
# to minimize confusion, Index is referenced as IndexFlag.Index
NoChangeFlag = Enum('NoChangeFlag', 'NoChange')
NoChange = NoChangeFlag.NoChange
UnsetFlag = Enum('UnsetFlag', 'Unset')
Unset = UnsetFlag.Unset

type IterableOfStr = list[str] | tuple[str] | set[str] | Generator[str]

class Matcher[T1, T2](Protocol):
    def __call__(self, user: Collection[T1], dest: Collection[T2]) -> dict[T1, T2]:
        ...

class RubricMatcher(Matcher[str, str], Protocol):
    def __call__(self, given_labels: Collection[str], dest_labels: Collection[str]) -> dict[str, str]:
        ...

class SisId(str):
    ''' A Canvas SIS Login ID (i.e. UNC Charlotte username) '''
    @classmethod
    def from_email(cls, email: str) -> Self:
        '''
        >>> SisId.from_email("mname3@charlotte.edu")
        'mname3'
        '''
        assert email.count('@') == 1

        sis_login_id, email_domain = email.split('@')
        
        if email_domain != "charlotte.edu":
            raise ValueError(f"Email {email} is not a UNC Charlotte email."
                              "Try modifying or removing from dataset.")
        
        return cls(sis_login_id)

class AnyById(pa.DataFrameModel):
    '''
    Models any DataFrame whose index is IDs from an `AliasRecord`.
    
    >>> import pandas as pd

    >>> df1 = pd.DataFrame(
    ...         {'col1': [1, 2, 3]},
    ...         index=[404, 405, 406]
    ...     ).rename_axis("id")
    >>> validated_df1 = AnyById.validate(df1, inplace=False)
    >>> bool(
    ...     (df1 == validated_df1).all(axis=None)
    ... )
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': [1, 2, 3]},
    ...         index=[404, "405", 406]
    ...     ).rename_axis("id")
    >>> validated_df2 = StudentPtsById.validate(df2, inplace=False)
    Traceback (most recent call last):
        ...
    pandera.errors.SchemaError: ...
    '''
    id: pa.typing.Index[int] = pa.Field(check_name=True)

    @pa.check('id', element_wise=True, ignore_na=False)
    def validate_alias_id(cls, x) -> bool:
        return x >= 400

class BoolsById(AnyById):
    '''
    Models any DataFrame indexed by IDs in an
    `AliasRecord` and composed of columns of
    booleans.

    >>> import pandas as pd

    >>> df1 = pd.DataFrame(
    ...         {'col1': [True, False, True]},
    ...         index=[404, 405, 406]
    ...     ).rename_axis("id")
    >>> validated_df1 = BoolsById.validate(df1, inplace=False)
    >>> df1.equals(validated_df1)
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': [True, False, 3]},
    ...         index=[404, 405, 406]
    ...     ).rename_axis("id")
    >>> validated_df2 = StudentPtsById.validate(df2, inplace=False)
    Traceback (most recent call last):
        ...
    pandera.errors.SchemaError: ...
    '''
    @pa.dataframe_check(element_wise=True) # element_wise actually means by rows
    def data_is_bools(cls, row: pd.Series) -> bool:
        bools_schema = pa.SeriesSchema(bool, nullable=False)
        row = row.rename(None, inplace=False)
        try:
            bools_schema.validate(row)
        except SchemaError as e:
            print(e)
            return False
        
        return True

class StudentPtsById(AnyById):
    '''
    Models any DataFrame indexed by IDs in an
    `AliasRecord` and composed of columns of
    numerical points.
    
    >>> import pandas as pd
    
    >>> df1 = pd.DataFrame(
    ...         { 'col1': [1, 2, 3],
    ...           'col2': [4, 5, 6.0], },
    ...         index=[407, 408, 409]
    ...     ).rename_axis("id")
    >>> validated_df1 = StudentPtsById.validate(df1, inplace=False)
    >>> df1.equals(validated_df1)
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': ["1", 2, 3.0]},
    ...         index=[404, 405, 406]
    ...     ).rename_axis("id")
    >>> validated_df2 = StudentPtsById.validate(df2, inplace=False)
    Traceback (most recent call last):
        ...
    pandera.errors.SchemaError: ...
    '''
    @pa.dataframe_check(element_wise=True) # element_wise actually means by rows
    def data_is_nums(cls, row: pd.Series) -> bool:

        row = row.rename(None, inplace=False)
        
        ints_schema = pa.SeriesSchema(int, nullable=False)
        try:
            ints_schema.validate(row)
        except SchemaError:
            pass
        else:
            return True

        floats_schema = pa.SeriesSchema(float, nullable=False)
        try:
            floats_schema.validate(row)
        except SchemaError as e:
            print(e)
        else:
            return True
        
        return False
