import argparse
import enum
import re
from shutil import get_terminal_size
from math import floor, ceil
from itertools import chain
import sys, ctypes
if (sys.platform == "win32"):
    import ctypes.wintypes
else:
    import termios
import colorama

import numbers as num
import pandas as pd
from pandas._typing import Scalar as pd_scalar

from typing import *
import pandera.pandas as pa
from pandera.typing import DataFrame
from util.types import SisId, DataBy_StudentSisId

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

class NameSisIdConverter:
    def __init__(self):
        self._name_to_sis: dict[str, SisId] = {}
        self._sis_to_name: dict[SisId, str] = {}

    def __str__(self):
        return str(self._name_to_sis)
    
    @property
    def names(self):
        return self._name_to_sis.keys()
    
    @property
    def sis_ids(self):
        return self._sis_to_name.keys()
    
    def add(self, *, name: str, sis_id: SisId):
        if (name in self._name_to_sis.keys()
            or sis_id in self._sis_to_name.keys()):
            raise ValueError(f"Cannot add name/sis_id ({name}, {sis_id}). "
                             f"Call remove_name() or remove_sis_id() first.")
        self._name_to_sis[name] = sis_id
        self._sis_to_name[sis_id] = name

    def addFromCols(self, sis_ids: pd.Series, names: pd.Series):
        assert all(sis_ids.index == names.index)
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
        if 'student_name' in df.columns:
            df.sis_id.name = "old_student_name"

        df['student_name'] = \
            (
                df[sis_id_col] if sis_id_col is not None
                else df.index.to_series()
            ) \
            .apply(
                self.to_name,
            )
        df.set_index(
            'student_name',
            drop=True, # ends up with unchanged columns
            verify_integrity=True,
            inplace=True
        )

        if 'old_student_name' in df.columns:
            df.sis_id.name = "student_name"
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
        >>> converter.add(sis_id="name1",name="Student Name")

        >>> df1 = pd.DataFrame({
        ...             "id": ["name1",],
        ...             "st_name":["Student Name",]
        ...         })
        >>> converter.reindex_by_sis_id(df1, "st_name")
                   id       st_name
        sis_id                     
        name1   name1  Student Name

        >>> df2 = df1.drop("id", axis='columns', inplace=False)
        >>> df2 = df2.set_index("st_name", drop=False)
        >>> converter.reindex_by_sis_id(df2)
                     st_name
        sis_id              
        name1   Student Name
        '''
        df = df.copy()
        if 'sis_id' in df.columns:
            df.sis_id.name = "old_sis_id"

        df['sis_id'] = \
            (
                df[name_col] if name_col is not None
                else df.index.to_series()
            ) \
            .apply(
                self.to_sis_id
            )
        df.set_index(
            'sis_id',
            drop=True, # ends up with unchanged columns
            verify_integrity=True,
            inplace=True
        )

        if 'old_sis_id' in df.columns:
            df.sis_id.name = "sis_id"
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
    sis_ids_to_match = list(sis_ids_to_match) # we need its length
    names = list(names_to_match) # we need to mutate for internal processing
    for i, sis_id in enumerate(sis_ids_to_match):
        screen = ConsoleFrame(prompt_header=True)
        screen.print_header(f"Student name matching ({i}/{len(sis_ids_to_match)})")
        start_idx = 1
        screen.print_enumerated(names, start_idx)
        screen.display_complete()

        selection_idx = screen.prompt_selection_idx(
            start_idx,
            start_idx + len(names) - 1,
            allow_none=True,
            prompt_header=f"Which matches this username? {sis_id}"
        )
        selection_str = names.pop(selection_idx)

        out.add(name=selection_str, sis_id=sis_id)

def interactive_rubric_criteria_match(given_labels: Iterable[str], dest_labels: Iterable[str]) -> dict[str, str]:
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
        - keys: Members of `given_labels`.
        - vals: Members of `dest_labels`.
    '''
    given_labels = list(given_labels)
    dest_labels = list(dest_labels)
    assert len(given_labels) <= len(dest_labels)

    out = dict()
    dest_labels = list(dest_labels) # we need to mutate for internal processing
    for i, given_label in enumerate(given_labels):
        screen = ConsoleFrame(prompt_header=True)
        screen.print_header(f"Rubric criteria matching ({i}/{len(given_labels)})")
        start_idx = 1
        screen.print_enumerated(dest_labels, start_idx)
        screen.display_complete()

        selection_idx = screen.prompt_selection_idx(
            start_idx,
            start_idx + len(dest_labels) - 1,
            prompt_header="Which matches this input file result? {given_label}"
        )
        selection_str = dest_labels.pop(selection_idx - start_idx)

        out[given_label] = selection_str
    return out

def center_text(text: str, line_width: int, padding_char: str) -> str:
    ''' If it must, centered text will be one char closer to the left side. '''
    total_padding_len = line_width - len(text)
    left_padding = padding_char * floor(total_padding_len / 2)
    right_padding = padding_char * ceil(total_padding_len / 2)
    return f"{left_padding}{text}{right_padding}"

def wrap_line(text: str, max_width: int) -> Iterable[str]:
    remaining = text
    wrapped = list[str]()
    while remaining:

        if len(remaining) <= max_width:
            wrapped.append(remaining)
            remaining = ""
            break

        max_next_line = remaining[:max_width]

        splitting_char_idx = max_next_line.rfind(' ')        
        if splitting_char_idx == -1:
            # no good place to wrap;
            # give up and write to edge of terminal
            splitting_char_idx = len(max_next_line)

        wrapped.append(remaining[:splitting_char_idx])
        # splitting char gets removed
        remaining = remaining[splitting_char_idx + 1:]

    return wrapped

def get_cursor_pos() -> tuple[int, int]:
    # https://stackoverflow.com/questions/35526014/how-can-i-get-the-cursors-position-in-an-ansi-terminal
    
    if (sys.platform == "win32"): # TODO try getting rid of win32 references in this function, thanks to colorama.init()
        OldStdinMode = ctypes.wintypes.DWORD()
        OldStdoutMode = ctypes.wintypes.DWORD()
        kernel32 = ctypes.windll.kernel32
        kernel32.GetConsoleMode(kernel32.GetStdHandle(-10), ctypes.byref(OldStdinMode))
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 0)
        kernel32.GetConsoleMode(kernel32.GetStdHandle(-11), ctypes.byref(OldStdoutMode))
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    else:
        OldStdinMode = termios.tcgetattr(sys.stdin)
        _ = termios.tcgetattr(sys.stdin)
        _[3] = _[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, _)

    try:
        _ = ""
        sys.stdout.write("\x1b[6n")
        sys.stdout.flush()
        while not (_ := _ + sys.stdin.read(1)).endswith('R'):
            pass
        res = re.match(r".*\[(?P<y>\d*);(?P<x>\d*)R", _)
    finally:
        if(sys.platform == "win32"):
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), OldStdinMode)
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), OldStdoutMode)
        else:
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, OldStdinMode)
            
    if (res):
        x_str = res.group("x")
        y_str = res.group("y")
        return (int(x_str), int(y_str))
    return (-1, -1)

def set_cursor_pos(line: int, col: int) -> None:
    ensure_colorama_init()
    sys.stdout.write("\033[%d;%dH" % (line, col))

colorama_initialized = False
def ensure_colorama_init() -> None:
    global colorama_initialized

    if not colorama_initialized:
        colorama.init()
        colorama_initialized = True

class ConsoleFrame():
    '''
    Utility to print a TUI that takes up the whole screen,
    with header(s) and space for prompt at the bottom.
    '''

    def __init__(self, prompt_header=False):
        self._prompt_height = 2 # see _prompt()
        self._prompt_header_height = 1 if prompt_header else None
        self.display_finalized = False
        self.used_lines = 0

    @property
    def terminal_width(self) -> int:
        return get_terminal_size().columns

    @property
    def available_lines(self) -> int:
        ''' Does not include the final lines reserved for prompts. '''
        return get_terminal_size().lines - self.prompt_region_height

    @property
    def remaining_available_lines(self) -> int:
        return self.available_lines - self.used_lines
    
    @property
    def prompt_region_height(self) -> int:
        ''' Height of entire prompt region, including header. '''
        val = (self._prompt_height
               + (self._prompt_header_height or 0))
        return val

    @property
    def prompt_header_loc(self) -> int:
        ''' Line number where the prompt header should be printed. '''
        if self._prompt_header_height is None:
            raise Exception("Prompt headers must be enabled")
        else:
            last_display_line = self.available_lines - 1
            return last_display_line + 1

    def _print_at(self, text: str, loc: tuple[int, int]) -> None:
        original_cursor_pos = get_cursor_pos()
        set_cursor_pos(*loc)
        print(text, end=None)
        set_cursor_pos(*original_cursor_pos)

    def _display(self, text: str | Iterable[str], end_newline=True) -> None:
        ''' Increments used_lines. '''
        
        # acknowledge mandatory line breaks
        if isinstance(text, str):
            lines = text.splitlines()
        else:
            lines = chain.from_iterable(x.splitlines() for x in text)
        
        # wrap text with additional line breaks
        wrapped_lines = chain.from_iterable(
            wrap_line(x, self.terminal_width)
            for x in lines
        )

        # print each line one-by-one, increment self.used_lines by line count
        for line in wrapped_lines:
            print(line)
            self.used_lines += 1

    def _prompt(self, prompt_msg: str, check: Callable[[str], bool]) -> str:
        original_cursor_pos = get_cursor_pos()
        response = None
        while not response:
            prompt_loc = self.available_lines - 2
                # work around unavoidable newline after, from user hitting enter
            set_cursor_pos(prompt_loc, 0)
            response = input(f"{prompt_msg}: ")
            if not check(response):
                response = None
                set_cursor_pos(prompt_loc, 0)
                input("Invalid value. Try again. [enter]") #TODO terminal highlighting
        set_cursor_pos(*original_cursor_pos)
        return response

    def print_header(self, header_text: str) -> None:
        '''
        Prints at current location in terminal, not at the top.
        '''
        if self.display_finalized:
            raise Exception("Cannot print to a ConsoleFrame after calling `display_complete()`")
        if ( self.terminal_width ) >= ( 1 + 1 + len(header_text) + 1 + 1 ):
            text = center_text(f" {header_text} ", self.terminal_width, '=')
        else:
            wrapped_lines = wrap_line(header_text, self.terminal_width)
            centered_wrapped_lines = (
                center_text(line, self.terminal_width, ' ')
                for line in wrapped_lines
            )
            text = [
                *centered_wrapped_lines,
                '=' * self.terminal_width,
            ]
        self._display(text)

    def print_enumerated(self, items: Iterable[str], start_idx=0) -> None:
        '''
        Print `items`, each with a corresponding number,
        so that the user can pick one.
        '''
        if self.display_finalized:
            raise Exception("Cannot print to a ConsoleFrame after calling `display_complete()`")
        friendly_enumerated = enumerate(items, start=start_idx)
        print_items = [f"{i}) {text}"
                       for i, text in friendly_enumerated]
        
        max_item_len = max(len(s) for s in print_items)
        col_margin = 3
        col_width = max_item_len + col_margin

        col_shaped_items = (x.ljust(col_width) for x in print_items)

        max_col_count = floor(
            (self.terminal_width + (1 * col_margin)) 
            / col_width
        )
        min_row_count = ceil(len(print_items) / max_col_count)

        cols: list[list[str]] = []
        # each iteration builds one column
        for row_idx in range(max_col_count):
            col: list[str] = []
            # each iteration adds one row to this column
            for j in range(min_row_count):
                try:
                    next_item = next(col_shaped_items)
                except StopIteration:
                    break
                col.append(next_item)
            cols.append(col)

        # build rows so we can print
        rows: list[str] = []
        max_col_len = len(cols[0])
        for row_idx in range(0, max_col_len):
            row_items: list[str]
            row_items = [col[row_idx]
                         if row_idx < len(col) else ""
                         for col in cols]
            if "" in row_items:
                first_empty_col = row_items.index("")
                assert all( len(x) == 0
                            for x in row_items[first_empty_col:] )
            line = ''.join(items) # items are pre-padded
            rows.append(line)

        self._display(rows)

    def display_complete(self) -> None:
        '''
        Pad the rest of the empty space in the display with blank lines.
        This hides any terminal history before this ConsoleFrame.
        '''
        padding_count = (
            self.remaining_available_lines #TODO +1 is wrong
            + 1     # we include the last line
                    # (which is dedicated to prompt)
                    # so that we fill the whole terminal screen
                    # (hiding any terminal history).
        )
        self._display(
            "\n" * padding_count,
            end_newline=False
        )
        self.display_finalized = True

    def prompt_selection_idx(self,
                             min: int = 0, max: Optional[int] = None,
                             allow_none: bool = False,
                             prompt_header: Optional[str] = None) -> int:
        '''
        Args:
            min: Smallest allowable number (inclusive).
            max: Highest allowable number (inclusive).
        '''
        if prompt_header:                
            self._print_at(prompt_header,
                           (self.prompt_header_loc, 0))
        input_s = self._prompt(
            ("Select an option{0}"
             .format(
                " (or [enter] to ignore)" if allow_none else ""
             )),
            check = lambda attempt_s: (
                True if allow_none else (
                    attempt_s.isdigit()
                    and (
                        ( min <= int(attempt_s) )
                    )
                    and (
                        ( max >= int(attempt_s) )
                        if max is not None else True
                    )
                )
            )
        )
        return int(input_s)