from itertools import chain
import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame, Series

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
from grade_conversion_script.util.types import IndexFlag, AnyById, IterableOfStr

class IdNotFoundException(KeyError, Exception):
    def __init__(self, id, *args, **kwargs):
        super().__init__(f"ID {id} not found.", *args, **kwargs)

class AliasNotFoundException(KeyError, Exception):
    def __init__(self, alias: str | Iterable[str], *args, **kwargs):
        if isinstance(alias, str):
            message = f"Alias {id} not found."
        else:
            message = f"None of the following aliases were found: {alias}"
        super().__init__(message, *args, **kwargs)

class AliasRecord:
    '''
    Match various names for an entity to each other.
    '''

# region magic methods

    def __init__(self):

        self._dict: dict[int, set[str]] = {}
        ''' Associate a list of aliases with a unique integer ID. '''

        self._next_id = 400 # make the number noticeably different from a typical int

    def __str__(self):
        # improve readability
        list_dict = {
            k : list(v)
            for k, v in self._dict.items()
        }
        return str(list_dict)

    def __contains__(self, item) -> bool:
        if item in self._dict.keys():
            return True
        elif item in self.all_aliases:
            return True

        return False

# endregion magic methods
# region add/remove

    def _new_id(self):
        val = self._next_id
        self._next_id += 1
        self._dict[val] = set()
        return val

    def valid_id(self, id: int) -> bool:
        return id in self._dict.keys()

    @property
    def all_aliases(self):
        return set[str]().union(
            chain(*self._dict.values())
        )

    def add_at_id(self, id: int, alias: str | Iterable[str]) -> None:
        assert self.valid_id(id), f"Invalid ID {id}"

        if isinstance(alias, str):
            aliases = (alias,)
        else:
            aliases = alias

        for item in aliases:
            if item in self.all_aliases_of(id=id):
                pass # set.update() will just have no effect
            elif item in self:
                raise ValueError(f"Alias {item} already exists (within following set: {self.all_aliases_of(id=id)}.")

        self._dict[id].update(aliases)

    def add_single(self, alias: str | Iterable[str]) -> None:
        if isinstance(alias, str):
            id = self._new_id()
            self.add_at_id(id, alias)
        else:
            aliases = alias
            for alias in aliases:
                self.add_single(alias)

    def add_together(self, aliases: Collection[str], allow_new: bool = True) -> None:
        try:
            id = self.id_of_any(aliases)
        except AliasNotFoundException:
            if allow_new:
               id = self._new_id()
            else:
                raise

        self.add_at_id(id, aliases)

    @overload
    def add_bulk(self, records: Iterable[str | Collection[str]], allow_new: bool = True
     ) -> None:
        ...
    @overload
    def add_bulk(self, records: DataFrame[str], allow_new: bool = True
     ) -> None:
        ...

    def add_bulk(self, records: Iterable[str | Collection[str]] | DataFrame[str], allow_new: bool = True) -> None:
        aliases_by_entity: Iterable[Iterable[str]]
        if isinstance(records, DataFrame):
            aliases_by_entity = records.itertuples(index=False, name=None)
            assert all(
                isinstance(alias, str)
                for alias in aliases_by_entity
            )
        else:
            aliases_by_entity = (
                (element,) if isinstance(element, str)
                else element
                for element in records
            )

        for aliases in aliases_by_entity:
            self.add_together(aliases)

# endregion add/remove
# region lookup/translation

    @overload
    def id_of(self, alias: str) -> int:
        ...
    @overload
    def id_of(self, alias: IterableOfStr) -> list[int]:
        ...
    def id_of(self, alias: str | Iterable[str]) -> int | list[int]:
        if isinstance(alias, str):
            for id, aliases in self._dict.items():
                if alias in aliases:
                    return id
            raise AliasNotFoundException(alias)
        else: # Iterable
            aliases = alias
            return  [
                self.id_of(alias)
                for alias in aliases
            ]

    def id_of_any(
            self,
            aliases: Iterable[str]
    ) -> int:

        ids = dict[int, set[str]]()
        last_id: int | None = None # heuristic shortcut for loop
        for alias in aliases:
            if last_id and alias in self.all_aliases_of(id=last_id):
                id = last_id
                continue
            try:
                id = self.id_of(alias)
            except AliasNotFoundException:
                continue
            else: # we found a matching id
                last_id = id
                ids.setdefault(id, set()).add(alias)

        assert len(ids) >= 0
        if len(ids) == 0:
            raise AliasNotFoundException(aliases)
        elif len(ids) > 1:
            list_dict = {k : list(v) for k, v in ids.items()}
            raise ValueError(f"Provided aliases match conflicting IDs."
                             f" {list_dict}.")

        id = iter(ids.keys()).__next__()
        return id

    @overload
    def all_aliases_of(self, *, id: int
      ) -> set[str]:
        ...
    @overload
    def all_aliases_of(self, *, alias: str
      ) -> set[str]:
        ...
    def all_aliases_of(self, *, id: int | None = None, alias: str | None = None
      ) -> set[str]:
        match id, alias:
            case None, None:
                raise ValueError("Must provide either id or known_alias.")
            case _, None:
                # find by id
                try:
                    return self._dict[id]
                except KeyError as e:
                    raise IdNotFoundException(id) from e
            case None, _:
                # find by alias
                id = self.id_of(alias) # may raise
                return self.all_aliases_of(id=id)
            case _, _:
                raise ValueError("Must provide only one of the following: id, known_alias.")

    def best_effort_alias(self, rule: Callable[[str], bool], *, id: int) -> str:
        all_options = self.all_aliases_of(id=id)

        possible_names = filter(rule, all_options)
        backup_options = iter(all_options)
        try:
            return next(possible_names)
        except StopIteration:
            return next(backup_options)

    @overload
    def find_mutual_alias(self, acceptable_aliases: list[str], *, id: int
                          ) -> str | set[str] | None:
        ...
    @overload
    def find_mutual_alias(self, acceptable_aliases: list[str], *, known_alias: str
                          ) -> str | set[str] | None:
        ...
    def find_mutual_alias(self, acceptable_aliases: list[str], *, id: (int | None) = None, known_alias: (str | None) = None):

        match id, known_alias:
            case None, None:
                raise ValueError("Must provide either id or known_alias.")
            case _, None:
                # find by id
                all_aliases = self.all_aliases_of(id=id)
            case None, _:
                # find by known_alias
                all_aliases = self.all_aliases_of(alias=known_alias)
            case _, _:
                raise ValueError("Must provide only one of the following: id, known_alias.")

        matches = set(all_aliases).intersection(acceptable_aliases)

        if not matches:
            return None
        if len(matches) == 1:
            return matches.pop()
        else:
            return matches

# endregion lookup/translation
# region DataFrame manipulation

    @pa.check_types
    def id_of_df[KT: Hashable | IndexFlag | pd.Series](
            self,
            df: pd.DataFrame,
            alias_col: KT | Sequence[KT],
            expect_new_entities: bool = False,
            collect_new_aliases: bool = True,
    ) -> Series[int]:

        # alias_cols: alias_col guaranteed as a Sequence
        alias_cols: Sequence[KT]
        if (
            # can't check specifically for a generic like Sequence[KT]
            isinstance(alias_col, str)
            or alias_col is IndexFlag.Index
            or isinstance(alias_col, pd.Series)
            or not isinstance(alias_col, Sequence)
        ):
            alias_cols = ( cast(KT, alias_col), )
        else:
            alias_cols = alias_col
        alias_cols = cast(Sequence[KT], alias_cols)

        # Parameter asserts (all columns)
        col_uniques = Counter((
            col
            if not isinstance(col, pd.Series) else col.name
            for col in alias_cols
        ))
        assert not any(
            count > 1
            for col, count in col_uniques.items()
        ), f"Duplicate column specified in alias_col. {str(col_uniques)}"

        # Parameter asserts (by column)
        for col in alias_cols:
            match col:
                case pd.Series():
                    assert col.index.equals(df.index) # pyright: ignore[reportUnknownMemberType] I can't modify pandas
                case IndexFlag.Index:
                    pass
                case _:
                    assert col in df.columns, f"Column {col} not found in DataFrame:\n{df}."

        # priority_aliases_df: alias_cols formatted into a DataFrame
        priority_aliases_df = pd.concat(
            {
                i: (
                    df.index.to_series() if col is IndexFlag.Index
                        # ^ the resulting Series is indexed by its own values
                    else col if isinstance(col, pd.Series)
                    else df[col]
                )
                for i, col in enumerate(alias_cols)
            },
            axis='columns'
        )

        # Populate id_series

        id_series = pd.Series(name="id", dtype='Int16', index=df.index)

        for row_idx in df.index: # pyright: ignore[reportAny] we don't care what the index type is
            priority_aliases = priority_aliases_df.loc[row_idx, :]
            assert isinstance(priority_aliases, pd.Series)
            priority_aliases = cast(pd.Series, priority_aliases)
            priority_aliases = priority_aliases.astype(str)

            id: int | None = None
            for alias in priority_aliases:
                assert isinstance(alias, str)
                if alias in self:
                    id = self.id_of(alias)
                    break
            if id is None:
                if expect_new_entities:
                    id = self._new_id()
                else:
                    raise AliasNotFoundException(priority_aliases.to_list())

            if collect_new_aliases:
                self.add_at_id(id, priority_aliases)

            id_series.at[row_idx] = id

        assert 'int' in str(id_series.dtype).lower(), f"Bad output dtype: {id_series.dtype}"
        return Series[int](id_series.astype(int))

    @pa.check_types
    def reindex_by_id[KT: Hashable | IndexFlag | pd.Series](
            self,
            df: pd.DataFrame,
            alias_col: KT | Sequence[KT] = IndexFlag.Index,
            expect_new_entities: bool = False,
            collect_new_aliases: bool = True,
            inplace: bool = False
    ) -> DataFrame[AnyById]:
        '''
        Reindex a collection of entities (one per row)
        by their internal ID stored in this object,
        finding their IDs by looking for a recognized alias
        in `df`.

        Remarks:
            Does not require the index of `df` to be set before
            this method call.
        Args:
            df: The `DataFrame`.
            alias_col:
                A list of columns in `df`, in order so that the
                column most likely to match a recognized alias
                comes first.
                Value may be one of the following, or a mixed-type iterable:
                * The name of the column in `df` which holds
                  aliases that can refer to an entity.
                * A reference to util.types.IndexFlag.Index,
                  indicating to use the index of `df`.
                * A reference to a `Series` with the same
                  index as `df`.
            expect_new_entities:
                Whether to allow unrecognized entities
                (i.e. new IDs) to be created and recorded.
                If False, if no recognized aliases are
                be found for a row, raises AliasNotFoundException.
            collect_new_aliases:
                Whether to collect unrecognized aliases from
                any members of `alias_col`.
                They will be matched to any recognized alias
                in the same row, or to a newly created ID.
            inplace:
                If True, reindexes `df` in place.
        Returns:
            A DataFrame indexed by internal IDs.

        # TODO these doctests
        >>> name_aliases = AliasRecord()
        >>> converter.add(sis_id="name1",name="Student Name")

        >>> df1 = pd.DataFrame({
        ...             "id": ["name1",],
        ...             "st_name":["Student Name",]
        ...         })
        >>> converter.reindex_by_id(df1, "st_name", expect_new=True, collect_new=True)
                id       st_name
        id
        400  name1  Student Name
        '''
        if inplace:
            df = df.copy()
        starting_df = df

        new_index = self.id_of_df(
            df,
            alias_col,
            expect_new_entities,
            collect_new_aliases
        )

        df.set_index(
            new_index,
            verify_integrity=True,
            inplace=True
        )

        assert starting_df is df # double-check in case of inplace=True
        return DataFrame[AnyById](df)

# endregion DataFrame manipulation
