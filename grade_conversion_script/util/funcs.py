import asyncio
from itertools import batched
import numbers as num
from secrets import randbits
from time import time_ns
from typing import Callable

from nicegui.element import Element
import pandas as pd

from typing import *
from pandas._typing import Scalar as pd_scalar

from grade_conversion_script.util import AliasRecord
from grade_conversion_script.util.custom_types import Matcher # pyright: ignore[reportWildcardImportFromLibrary]

# region Iteration

def multifilter[T](iterable: Iterable[T], *funcs: Callable[[T], bool]) -> Iterable[T]:
    ''' Pass an Iterable through multiple filters. '''
    def combined_filter(item: T) -> bool:
        return all(
            single_filter(item)
            for single_filter in funcs
        )
    return filter(combined_filter, iterable)

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
        raise ValueError(f"No matching item found in {iterable}.")
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
# region Async

async def wait_for_event[T0, *T, _, *U, __](
    callback_register_func: Callable[
        [
            Callable[[T0, *T], None],
        ],
        _
    ],
    error_register_func: Callable[
        [
            Callable[[*U], None]
        ],
        __
    ] | None = None
) -> tuple[T0, *T]:

    awaitable: asyncio.Future[tuple[T0, *T]]
    awaitable = asyncio.get_running_loop().create_future()
    event_done = False
    def event_callback(a: T0, *args: *T, **kwargs):
        nonlocal event_done, awaitable
        args_tuple = (a, *args, *kwargs.values())
        if not event_done:
            event_done = True
            awaitable.set_result(args_tuple)
    _ = callback_register_func(event_callback)

    if error_register_func is None:
        return await awaitable

    def event_error_callback(*args: *U, **kwargs):
        nonlocal event_done, awaitable
        if not event_done:
            event_done = True
            exception_data = (args, kwargs)
            awaitable.set_exception(
                Exception(exception_data)
            )
    _ = error_register_func(event_error_callback)

    return await awaitable

def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    try:
        _ = asyncio.create_task(coro)
    except RuntimeError:
        with asyncio.Runner() as runner:
            runner.run(coro)

# endregion Async
# region gui

def set_light_dark[*P](element: Element, on_resolve: Callable[[Element, *P], Any], if_light: tuple[*P], if_dark: tuple[*P]) -> None:
    async def async_by_light_dark(element: Element, on_resolve: Callable[[Element, *P], Any], if_light: tuple[*P], if_dark: tuple[*P]):
        dark_background = await element.get_computed_prop('dark')
        if dark_background:
            on_resolve(element, *if_dark)
        else:
            on_resolve(element, *if_light)

    run_async(async_by_light_dark(element, on_resolve, if_light, if_dark))

def unique_readable_html_safe(char_length: int = 5):
    # char_bit_size = 5
    # char_max_val + 1 = 32

    unique_bits = randbits(char_length * 5)

    result = list[str]()
    for _ in range(char_length):
        bit_chunk = unique_bits & ( (1 << 5) - 1 )
        unique_bits >>= 5

        if bit_chunk < 26:
            char = chr(bit_chunk + ord('a'))
            result.append(char)
        else:
            bit_chunk -= 26
            char = ('A', 'E', 'I', 'O', 'U', 'Y')[bit_chunk]
            result.append(char)

    return ''.join(result)

def truncate_exception_to_html(exception: Exception):
    lines = str(exception).splitlines()
    truncate_idx = next(
        (
            i
            for i, line in enumerate(lines)
            if 'traceback' in line.lower()
        ),
        10
    )
    truncated_html = '<br>'.join(
        [
            line[:100] + ('...' if len(line) > 100 else '')
            for line in lines[:truncate_idx]
        ] + (
            ['...', ]
            if len(lines) > truncate_idx else []
        )
    )
    return truncated_html


# endregion gui
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

    realigned = pd.concat(
        [to_realign, target_idx_by_origin_idx.rename('target_index')],
        join='inner', # only the rows in common between the two
        axis='columns'
    ).set_index(
        'target_index',
        drop=True
    ).squeeze(axis='columns')
    assert isinstance(realigned, (pd.Series, pd.DataFrame))
    realigned = realigned.reindex(index=target_ids.index)

    assert type(realigned) == type(to_realign)
    assert realigned.notna().all(None)  # pyright: ignore[reportArgumentType] pandas-stubs is wrong

    return realigned

# endregion pandas
# region AliasRecord

def best_effort_is_name(s: str) -> bool:
    '''
    Tries to check if a string is a name,
    as it would appear in Canvas or a
    web profile.

    >>> list = ['Name One (copy 1)', 'Name One (copy 2)', 'name1', "1"]
    >>> [best_effort_is_name(s) for s in list]
    [True, True, False, False]
    '''
    if '(' in s and ')' in s[s.index('(')+1:]:
        s = s[:s.index('(')] + s[s.rindex(')') + 1:]

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
        any(
            letter.isupper() # d'Angelo
            or not letter.isalpha()
            for letter in word
        )
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
        alias_record.id_together(matched_dest_aliases)
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
