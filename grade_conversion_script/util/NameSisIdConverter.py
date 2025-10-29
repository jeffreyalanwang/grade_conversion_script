from grade_conversion_script.util.types import DataBy_StudentSisId, SisId

import pandas as pd
import pandera.pandas as pa
from pandera.typing import DataFrame

from typing import * # pyright: ignore[reportWildcardImportFromLibrary]

class NameSisIdConverter:
    def __init__(self):
        self._name_to_sis: dict[str, SisId] = {}
        self._sis_to_name: dict[SisId, str] = {}

    def __str__(self):
        return str(self._name_to_sis)

    @property
    def names(self) -> set:
        return self._name_to_sis.keys()

    @property
    def sis_ids(self) -> set:
        return self._sis_to_name.keys()

    def add(self, *, name: str, sis_id: SisId):
        if (
            name in self._name_to_sis.keys()
            or sis_id in self._sis_to_name.keys()
        ) and not (
            name == self.to_name(sis_id)
        ):
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