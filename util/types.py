import re

from typing import *
import pandera.pandas as pa
from pandera.errors import SchemaError
import pandas as pd
import numbers as num

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
        >>> SisId.validate(True)
        False
        >>> SisId.validate("mname3")
        True
        >>> SisId.validate("mname")
        True
        >>> SisId.validate("3")
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
        >>> SisId.from_email("mname3@charlotte.edu")
        'mname3'
        '''
        assert email.count('@') == 1

        sis_login_id, email_domain = email.split('@')
        
        if email_domain != "charlotte.edu":
            raise ValueError(f"Email {email} is not a UNC Charlotte email.")
        
        return cls(sis_login_id)
    
class DataBy_StudentSisId(pa.DataFrameModel):
    '''
    Models any DataFrame whose index is all instances of `SisId`.
    
    >>> import pandas as pd

    >>> df1 = pd.DataFrame(
    ...         {'col1': [1, 2, 3]},
    ...         index=["sisid1", "sisidtwo", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df1 = DataBy_StudentSisId.validate(df1, inplace=False)
    >>> bool(
    ...     (df1 == validated_df1).all(axis=None)
    ... )
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': [1, 2, 3]},
    ...         index=["sisid1", "2", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df2 = DataBy_StudentSisId.validate(df2, inplace=False)
    Traceback (most recent call last):
        ...
    pandera.errors.SchemaError: ...
    '''
    sis_id: pa.typing.Index[str] = pa.Field(check_name=True)

    @pa.check('sis_id', element_wise=True, ignore_na=False)
    def validate_sis_id(cls, x) -> bool:
        return SisId.validate(x)

class BoolsBy_StudentSisId(DataBy_StudentSisId):
    '''
    Models any DataFrame indexed by `SisId`s and with
    columns of booleans.

    >>> import pandas as pd

    >>> df1 = pd.DataFrame(
    ...         {'col1': [True, False, True]},
    ...         index=["sisid1", "sisidtwo", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df1 = BoolsBy_StudentSisId.validate(df1, inplace=False)
    >>> bool(
    ...     (df1 == validated_df1).all(axis=None)
    ... )
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': [True, False, 3]},
    ...         index=["sisid1", "2", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df2 = BoolsBy_StudentSisId.validate(df2, inplace=False)
    Traceback (most recent call last):
        ...
    pandera.errors.SchemaError: ...
    '''
    @pa.dataframe_check(element_wise=True)
    def data_is_bools(cls, row: pd.Series) -> bool:
        bools_schema = pa.SeriesSchema(bool, nullable=False)
        row = row.rename(None, inplace=False)
        try:
            bools_schema.validate(row)
        except SchemaError:
            return False
        
        return True

class PtsBy_StudentSisId(DataBy_StudentSisId):
    '''
    Models any DataFrame indexed by `SisId`s and with
    columns of numerical points.
    
    >>> import pandas as pd
    
    >>> df1 = pd.DataFrame(
    ...         { 'col1': [1, 2, 3],
    ...           'col2': [4, 5, 6.0], },
    ...         index=["sisid1", "sisidtwo", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df1 = PtsBy_StudentSisId.validate(df1, inplace=False)
    >>> bool(
    ...     (df1 == validated_df1).all(axis=None)
    ... )
    True

    >>> df2 = pd.DataFrame(
    ...         {'col1': [True, 2, 3.0]},
    ...         index=["sisid1", "2", "sisid3"]
    ...     ).rename_axis("sis_id")
    >>> validated_df2 = PtsBy_StudentSisId.validate(df2, inplace=False)
    Traceback (most recent call last):
        ...
    pandera.errors.SchemaError: ...
    '''
    @pa.dataframe_check(element_wise=True)
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
        except SchemaError:
            pass
        else:
            return True
        
        return False