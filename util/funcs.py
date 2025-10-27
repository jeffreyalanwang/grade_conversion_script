
import numbers as num
import pandas as pd
from pandas._typing import Scalar as pd_scalar

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]

def add_tuples[T: tuple](a: T, b: T) -> T:
    ''' Add two tuples element-wise. '''
    sum_elements = (
        element_a + element_b
        for element_a, element_b in zip(a, b)
    )
    return type(a)(*sum_elements)

def to_real_number(value: Any) -> num.Real:
    if '.' in str(value) or pd.isna(value):
        out = float(value)
    else:
        out = int(value)
    return cast(num.Real, out)

def iter_by_element(df: pd.DataFrame) -> Iterable[Tuple[Hashable, Hashable, pd_scalar]]:
    ''' Iterate a DataFrame by row index, colum index, and value. '''
    for row_idx, row_values in df.iterrows():
        for col_idx, value in row_values.items():
            yield (row_idx, col_idx, value)

def is_pd_scalar(obj: Any) -> TypeGuard[pd_scalar]:
    return pd.api.types.is_scalar(obj)

def is_pd_value_present(value) -> bool:
    ''' Returns False if `value` came from an empty Pandas dataframe element. '''
    if pd.isna(value):
        return False
    if isinstance(value, str):
        if "nan" == value.lower():
            return False
        if len(value) == 0:
            return False
    return True