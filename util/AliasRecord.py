import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame, Series

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]
from util.types import IndexFlag, DataBy_StudentSisId

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
        return val

    @property
    def all_aliases(self):
        return set[str]().union(
            iter(self._dict.values())
        )

    def add_at_id(self, id: int, alias: str | Iterable[str]) -> None:
        if isinstance(alias, str):
            aliases = (alias,)
        else:
            aliases = alias

        for item in aliases:
            if item in self.aliases_from_id(id):
                pass # set.update() will just have no effect
            elif item in self:
                raise ValueError(f"Alias {item} already exists (within following set: {self.all_aliases_of(item)}.")

        self._dict.setdefault(id, set()).update(aliases)

    def add_associated(self, aliases: Collection[str], allow_new: bool = True) -> None:
        ids = dict[int, set[str]]()
        last_id = None # heuristic shortcut for loop
        for alias in aliases:
            if last_id and alias in self.aliases_from_id(last_id):
                id = last_id
            else:
                try:
                    id = self.id_of(alias)
                except AliasNotFoundException:
                    continue
            last_id = id
            ids.setdefault(id, set()).add(alias)

        assert len(ids) >= 0
        if len(ids) == 0:
            if allow_new:
                id = self._new_id()
            else:
                raise AliasNotFoundException(aliases)
        elif len(ids) == 1:
            id = iter(ids.keys()).__next__()
        else: # len(ids) > 1
            list_dict = {k : list(v) for k, v in ids.items()}
            raise ValueError(f"Provided aliases match conflicting IDs."
                             f" {list_dict}.")

        self.add_at_id(id, aliases)

    @overload
    def add_bulk(self, records: Iterable[str | Collection[str]], allow_new: bool = True
     ) -> None:
        ...
    @overload
    def add_bulk(self, records: DataFrame[str], allow_new: bool = True
     ) -> None:
        ...
    @pa.check_types
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
            self.add_associated(aliases)

# endregion add/remove
# region lookup/translation

    def id_of(self, alias: str) -> int:
        for id, aliases in self._dict.items():
            if alias in aliases:
                return id
        raise AliasNotFoundException(alias)

    def aliases_from_id(self, id: int) -> set[str]:
        try:
            return self._dict[id]
        except KeyError:
            raise IdNotFoundException(id)

    def all_aliases_of(self, alias: str) -> set[str]:
        id = self.id_of(alias)
        return self.aliases_from_id(id)

    @overload
    def find_acceptable_alias(self, acceptable_aliases: list[str], *, id: int
      ) -> str | set[str] | None:
        ...
    @overload
    def find_acceptable_alias(self, acceptable_aliases: list[str], *, known_alias: str
      ) -> str | set[str] | None:
        ...
    def find_acceptable_alias(self, acceptable_aliases: list[str], *, id: (int | None) = None, known_alias: (str | None) = None):

        match id, known_alias:
            case None, None:
                raise ValueError("Must provide either id or known_alias.")
            case _, None:
                # find by id
                all_aliases = self.aliases_from_id(id)
            case None, _:
                # find by known_alias
                all_aliases = self.all_aliases_of(known_alias)
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

    def id_of_df[KT: Hashable | IndexFlag | pd.Series](
            self,
            df: pd.DataFrame,
            alias_col: KT | Sequence[KT],
            expect_new: bool = False,
            collect_new: bool = True,
    ) -> Series[int]:

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
            alias_cols = cast(Sequence[KT], alias_col)

        # Parameter asserts

        col_uniques = Counter(alias_cols)
        assert not any(
            count > 1
            for col_val, count in col_uniques.items()
        ), f"Duplicate column specified in alias_col. {str(col_uniques)}"

        for col in alias_cols:
            match col:
                case IndexFlag.Index:
                    pass
                case pd.Series():
                    assert col.index.equals(df.index) # pyright: ignore[reportUnknownMemberType] I can't modify pandas
                case Hashable():
                    assert col in df.columns

        id_series = Series[int](name="id", dtype=int, index=df.index)

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

        for row_idx in df.index: # pyright: ignore[reportAny] we don't care what the index type is
            priority_aliases = priority_aliases_df.loc[row_idx, :].squeeze(axis="columns")
            assert isinstance(priority_aliases, pd.Series)
            priority_aliases = priority_aliases.astype(str)

            id: int | None = None
            for alias in priority_aliases:
                if alias in self:
                    id = self.id_of(alias)
                    break
            if id is None:
                if expect_new:
                    id = self._new_id()
                else:
                    raise AliasNotFoundException(priority_aliases.to_list())

            if collect_new:
                self.add_at_id(id, priority_aliases)

            id_series.at[row_idx] = id

        return Series[int](id_series)

    @pa.check_types
    def reindex_by_id[KT: Hashable | IndexFlag | pd.Series](
            self,
            df: pd.DataFrame,
            alias_col: KT | Sequence[KT] = IndexFlag.Index,
            expect_new: bool = False,
            collect_new: bool = True,
            inplace: bool = False
    ) -> DataFrame[DataBy_StudentSisId]:
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
            expect_new:
                Whether to allow unrecognized entities
                (i.e. new IDs) to be created and recorded.
                If False, if no recognized aliases are
                be found for a row, raises AliasNotFoundException.
            collect_new:
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
            expect_new,
            collect_new
        )

        df.set_index(
            new_index,
            verify_integrity=True,
            inplace=True
        )

        assert starting_df is df # double-check in case of inplace=True
        return DataFrame[DataBy_StudentSisId](df)

# endregion DataFrame manipulation
