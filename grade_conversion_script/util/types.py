from enum import Enum
import pandas as pd

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
import pandera.pandas as pa
from pandera.errors import SchemaError


IndexFlag = Enum('Index', 'Index')
Index = IndexFlag.Index

type IterableOfStr = list[str] | tuple[str] | set[str] | Generator[str]

type Matcher[T1, T2] = Callable[
    [Collection[T1], Collection[T2]],
    dict[T1, T2]
]

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
    Models any DataFrame whose index is all instances of `SisId`.
    
    >>> import pandas as pd

    >>> df1 = pd.DataFrame(
    ...         {'col1': [1, 2, 3]},
    ...         index=["sisid1", "sisidtwo", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df1 = AnyById.validate(df1, inplace=False)
    >>> bool(
    ...     (df1 == validated_df1).all(axis=None)
    ... )
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': [1, 2, 3]},
    ...         index=["sisid1", "2", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df2 = AnyById.validate(df2, inplace=False)
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
    Models any DataFrame indexed by `SisId`s and with
    columns of booleans.

    >>> import pandas as pd

    >>> df1 = pd.DataFrame(
    ...         {'col1': [True, False, True]},
    ...         index=["sisid1", "sisidtwo", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df1 = BoolsById.validate(df1, inplace=False)
    >>> bool(
    ...     (df1 == validated_df1).all(axis=None)
    ... )
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': [True, False, 3]},
    ...         index=["sisid1", "2", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df2 = BoolsById.validate(df2, inplace=False)
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
    Models any DataFrame indexed by `SisId`s and with
    columns of numerical points.
    
    >>> import pandas as pd
    
    >>> df1 = pd.DataFrame(
    ...         { 'col1': [1, 2, 3],
    ...           'col2': [4, 5, 6.0], },
    ...         index=["sisid1", "sisidtwo", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df1 = StudentPtsById.validate(df1, inplace=False)
    >>> bool(
    ...     (df1 == validated_df1).all(axis=None)
    ... )
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': [True, 2, 3.0]},
    ...         index=["sisid1", "2", "sisid3"]
    ...     ).rename_axis("sis_id")
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