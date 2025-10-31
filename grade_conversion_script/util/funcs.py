import numbers as num
from typing import *

import pandas
import pandas as pd
from pandas._typing import Scalar as pd_scalar

from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.types import Matcher # pyright: ignore[reportWildcardImportFromLibrary]

# region Typing

def add_tuples[T: tuple[Any, ...]](a: T, b: T) -> T:
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
    df.replace('', pd.NA, inplace=True)
    rows = df.iterrows()
    jagged_rows = (
        (index, series.dropna())
        for index, series in rows
    )
    joined_rows = (
        (index, sep.join(series))
        for index, series in jagged_rows
    )
    return pd.Series(joined_rows)


def reindex_to[T: pd.Series | pd.DataFrame](to_realign: T, target_ids: pd.Series) -> T:
    '''
    Realign a Series or DataFrame indexed by some ID
    to match another DataFrame whose IDs per row are known.

    Values in `to_realign` may be dropped.

    Args:
    * to_realign:
        Data to get a reindexed copy of.
    * target_ids:
        A column from the target DataFrame
        whose values correspond to the
        index of `to_realign`.
    '''
    # flip `target_ids`
    target_idx_by_origin_idx = target_ids.index.to_series(index=target_ids)

    # drop values of `to_realign` that do not have dest index
    to_realign = to_realign[to_realign.index.isin(target_ids)]
    realigned = to_realign.reindex(index=target_idx_by_origin_idx)
    assert isinstance(realigned, type(to_realign))
    realigned.sort_index(inplace=True)

    return realigned

# endregion pandas
# region AliasRecord

def best_effort_is_name(s: str):
    for letter in s:

        # letter is certainly allowed in name
        if any((
            letter.isalpha(),
            letter in (' ', '-', "'", '.')
        )):
            continue

        # s is certainly not name
        if any((
            letter.isdigit(),
            letter in (',')
        )):
            return False

    words = s.split(' ')
    is_full_name = len(words) >= 2

    required_capitalized_words = (words[0], words[-1])
    is_required_capitalized = any(
        any(letter.isupper() for letter in word) # d'Angelo
        for word in required_capitalized_words
    )

    return is_full_name and is_required_capitalized

UnrecognizedAliases = NamedTuple('UnrecognizedAliases', (
    ('input', list[str]),
    ('dest', list[str])
))
def get_unmatched_entities(
        alias_record: AliasRecord,
        *,
        input_ids: Iterable[int],
        dest_alias_lists: Iterable[str | Sequence[str]],
  ) -> UnrecognizedAliases:

    matched_dest_alias_lists = list[Sequence[str]]()
    unmatched_dest_alias_lists = list[Sequence[str]]()
    for dest_alias_list in dest_alias_lists:
        if isinstance(dest_alias_list, str):
            dest_alias_list = (dest_alias_list,)

        if any(
            dest_alias in alias_record.all_aliases
            for dest_alias in dest_alias_list
        ):
            matched_dest_alias_lists.append(dest_alias_list)
        else:
            unmatched_dest_alias_lists.append(dest_alias_list)
    unmatched_dest_names = [
        unmatched_alias_list[0]
        for unmatched_alias_list in unmatched_dest_alias_lists
    ]

    matched_dest_ids = [
        alias_record.id_of_any(matched_dest_aliases)
        for matched_dest_aliases in matched_dest_alias_lists
    ]
    unmatched_input_ids = filter(
        lambda input_id: input_id not in matched_dest_ids,
        input_ids
    )
    unmatched_input_names = [
        alias_record.best_effort_alias(best_effort_is_name, id=input_id)
        for input_id in unmatched_input_ids
    ]

    return UnrecognizedAliases(input=unmatched_input_names, dest=unmatched_dest_names)

def associate_unrecognized_entities(
        alias_record: AliasRecord,
        name_match: Matcher[str, str],
        *,
        input_ids: Iterable[int],
        dest_alias_lists: Iterable[str | Sequence[str]],
  ) -> None:
    unmatched_input_names, unmatched_dest_names = get_unmatched_entities(
        alias_record,
        input_ids=input_ids,
        dest_alias_lists=dest_alias_lists
    )
    matched: dict[str, str] = name_match(
        unmatched_input_names,
        unmatched_dest_names
    )
    for input_name, dest_name in matched.items():
        alias_record.add_together(
            aliases=(input_name, dest_name),
            allow_new=False
        )

# endregion AliasRecord
