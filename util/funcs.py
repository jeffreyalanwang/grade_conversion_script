
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

def to_real_number(value: str) -> num.Real:
    if '.' in value:
        out = float(value)
    else:
        out = int(value)
    return cast(num.Real, out)

def is_pd_scalar(obj: Any) -> TypeGuard[pd_scalar]:
    return pd.api.types.is_scalar(obj)
