import numbers as num
from typing import *

import pandas as pd
from pandas._typing import Scalar as pd_scalar


# region Iteration

def multifilter[T](iterable: Iterable[T], *funcs: Callable[[T], bool]) -> Iterable[T]:
    ''' Pass an Iterable through multiple filters. '''
    def combined_filter(item: T) -> bool:
        return all(
            single_filter(item)
            for single_filter in funcs
        )
    return filter(combined_filter, iterable)

class ItemNotFound(ValueError):
    pass
def index_where[T](filter: Callable[[T], bool], iterable: Iterable[T]) -> int:
    '''
    Return index of first item in `iterable`
    for which `filter` returns True.

    Raises ValueError if no matching item found.
    '''
    matching_indexes = (
        i
        for i, item in enumerate(iterable)
        if filter(item)
    )
    try:
        parent_data_loc = next(matching_indexes)
    except StopIteration:
        raise ItemNotFound(f"No matching item found in {iterable}.")
    else:
        return parent_data_loc

def tuple_insert[T](index: int, value: T, tup: Sequence[T]) -> tuple[T, ...]:
    ''' Insert `value` into `tup` at `index`. '''
    return (
        *tup[:index],
        value,
        *tup[index:]
    )

def tuple_pop[T](index: int, tup: Sequence[T]) -> tuple[T, tuple[T, ...]]:
    ''' Pop value from `tup` at `index`. '''
    popped = tup[index]
    rest = (*tup[:index], *tup[index+1:])
    return (popped, rest)

def tuple_replace[T](index: int, value: T, tup: Sequence[T]) -> tuple[T, ...]:
    ''' Replace value at `index` in `tup` with `value`. '''
    return (
        *tup[:index],
        value,
        *tup[index+1:]
    )

# endregion Iteration
# region Typing


@overload
def all_truthy[T](collection: Sequence[T | None]) -> TypeGuard[Sequence[T]]:
    ...
@overload
def all_truthy[T](collection: Collection[T | None]) -> TypeGuard[Collection[T]]:
    ...
def all_truthy[T](collection: Collection[T | None]) -> TypeGuard[Collection[T]]:
    for item in collection:
         if not item:
             return False
    return True

def all_isinstance[T](collection: Collection[Any], item_type: type[T]) -> TypeGuard[Collection[T]]:
    for item in collection:
        if not isinstance(item, item_type):
            return False
    return True

def add_tuples[T: tuple[Any, ...]](a: T, b: T) -> T:
    ''' Add two tuples element-wise, compatibly with type-checkers. '''
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

# endregion Typing
# region pandas

Enumerated2D = NamedTuple('Index2D', [("row", Hashable), ("col", Hashable), ("val", pd_scalar)])
def iter_by_element(df: pd.DataFrame) -> Iterable[Enumerated2D]:
    ''' Iterate a DataFrame by row index, colum index, and value. '''
    for row_idx, row_values in df.iterrows():
        for col_idx, value in row_values.items():
            yield Enumerated2D(row_idx, col_idx, value)

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

def contains_row_for(contains_values: pd.DataFrame | pd.Series, at_index_in: pd.DataFrame | pd.Series) -> pd.Series:
    '''
    Returns:
        Indexed like `at_index_in`.
    '''
    return pd.Series(
        data=True,
        index=contains_values.index,
        dtype = bool
    ).reindex(
        fill_value=False,
        index=at_index_in.index
    )

def join_str_cols(sep: str, df: pd.DataFrame) -> pd.Series:
    ''' Joins on `sep` but drops NaNs. '''
    df = df.replace('', pd.NA)
    rows = df.iterrows()
    jagged_rows = (
        (index, series.dropna())
        for index, series in rows
    )
    joined_rows = (
        (index, sep.join(series))
        for index, series in jagged_rows
    )
    return pd.Series({index: value
        for index, value in joined_rows})

@overload
def reindex_to(to_realign: pd.Series, target_ids: pd.Series) -> pd.Series:
    ...
@overload
def reindex_to(to_realign: pd.DataFrame, target_ids: pd.Series) -> pd.DataFrame:
    ...
def reindex_to(to_realign: pd.Series | pd.DataFrame, target_ids: pd.Series) -> pd.Series | pd.DataFrame:
    '''
    Realign a Series or DataFrame indexed by some ID
    to match another DataFrame, with a different index but
    whose rows each have known IDs.

    Args:
    * to_realign:
        Data to get a reindexed copy of.
    * target_ids:
        A column from the target DataFrame
        whose values correspond to the
        index of `to_realign`.
    Returns:
        A subset of the data in `to_realign`;
        index is a subset of `target_ids.index`.
    '''
    # flip `target_ids`
    target_idx_by_arg_idx = target_ids.index.to_series(index=target_ids)

    # temp DataFrame with new index as a column; drop the column
    # and, if single column, turn to series
    realigned = pd.concat(
        [to_realign, target_idx_by_arg_idx.rename('target_index')],
        join='inner', # only the rows in common between the two
        axis='columns'
    ).set_index(
        'target_index',
        drop=True
    ).squeeze(axis='columns')

    # maybe the input was actually a one-column DataFrame
    match to_realign:
        case pd.Series():
            assert isinstance(realigned, pd.Series)
        case pd.DataFrame():
            if len(to_realign.columns) == 1:
                assert isinstance(realigned, pd.Series)
                realigned = realigned.to_frame()
            else:
                assert isinstance(realigned, pd.DataFrame)

    # reorder the rows of `realigned`
    sorted_index = target_ids.index.intersection(realigned.index)
    realigned = realigned.loc[sorted_index]

    return realigned

# endregion pandas
