from typing import no_type_check
import pytest
import pandas as pd
from pandas.testing import assert_series_equal
from grade_conversion_script.util.AliasRecord import (
    AliasRecord,
    IdNotFoundException,
    AliasNotFoundException
)
from grade_conversion_script.util.custom_types import IndexFlag

class TestAliasRecordExceptions:
    """Test custom exception classes."""
    
    def test_id_not_found_exception(self):
        with pytest.raises(IdNotFoundException) as exc_info:
            raise IdNotFoundException(123)
        assert "ID 123 not found" in str(exc_info.value)
    
    def test_alias_not_found_exception_single(self):
        with pytest.raises(AliasNotFoundException) as exc_info:
            raise AliasNotFoundException("test_alias")
        assert "not found" in str(exc_info.value)
    
    def test_alias_not_found_exception_multiple(self):
        aliases = ["alias1", "alias2"]
        with pytest.raises(AliasNotFoundException) as exc_info:
            raise AliasNotFoundException(aliases)
        assert "None of the following aliases were found" in str(exc_info.value)


class TestAliasRecordBasics:
    """Test basic AliasRecord functionality."""
    
    def test_init(self):
        ar = AliasRecord()
        assert ar._next_id == 400
        assert ar._dict == {}
    
    def test_str(self):
        ar = AliasRecord()
        ar.add_new_entity("test")
        result = str(ar)
        assert "400" in result
        assert "test" in result
    
    def test_contains_id(self):
        ar = AliasRecord()
        ar.add_new_entity("test")
        assert 400 in ar
    
    def test_contains_alias(self):
        ar = AliasRecord()
        ar.add_new_entity("test")
        assert "test" in ar
    
    def test_not_contains(self):
        ar = AliasRecord()
        assert "nonexistent" not in ar
        assert 999 not in ar


class TestAliasRecordAddRemove:
    """Test adding and removing aliases."""
    
    def test_new_id(self):
        ar = AliasRecord()
        id1 = ar._new_id()
        id2 = ar._new_id()
        assert id1 == 400
        assert id2 == 401
    
    def test_all_aliases_empty(self):
        ar = AliasRecord()
        assert ar.all_aliases == set()
    
    def test_all_aliases_multiple(self):
        ar = AliasRecord()
        ar.add_together(["alias1", "alias2"])
        ar.add_together(["alias3"])
        assert ar.all_aliases == {"alias1", "alias2", "alias3"}
    
    def test_add_at_id_single_string(self):
        ar = AliasRecord()
        id = ar._new_id()
        ar.add_at_id(id, "test_alias")
        assert "test_alias" in ar.all_aliases_of(id=id)
    
    def test_add_at_id_multiple_strings(self):
        ar = AliasRecord()
        id = ar._new_id()
        ar.add_at_id(id, ["alias1", "alias2", "alias3"])
        aliases = ar.all_aliases_of(id=id)
        assert aliases == {"alias1", "alias2", "alias3"}
    
    def test_add_at_id_duplicate_same_id(self):
        ar = AliasRecord()
        id = ar._new_id()
        ar.add_at_id(id, "test")
        ar.add_at_id(id, "test")  # Should not raise
        assert ar.all_aliases_of(id=id) == {"test"}
    
    def test_add_at_id_duplicate_different_id(self):
        ar = AliasRecord()
        ar.add_at_id(ar._new_id(), "test")
        with pytest.raises(ValueError) as exc_info:
            ar.add_at_id(ar._new_id(), "test")
        assert "already exists" in str(exc_info.value)
    
    def test_add_associated_new_aliases(self):
        ar = AliasRecord()
        ar.add_together(["alias1", "alias2"], allow_new=True)
        # Should create a new ID
        id1 = ar.id_of("alias1")
        id2 = ar.id_of("alias2")
        assert id1 == id2
    
    def test_add_associated_existing_aliases(self):
        ar = AliasRecord()
        ar.add_new_entity("alias1")
        ar.add_together(["alias1", "alias2"], allow_new=True)
        assert ar.id_of("alias1") == 400
        assert ar.id_of("alias2") == 400
    
    def test_add_associated_not_allow_new(self):
        ar = AliasRecord()
        with pytest.raises(AliasNotFoundException):
            ar.add_together(["new_alias"], allow_new=False)
    
    def test_add_associated_conflicting_ids(self):
        ar = AliasRecord()
        ar.add_new_entity("alias1")
        ar.add_new_entity("alias2")
        with pytest.raises(ValueError) as exc_info:
            ar.add_together(["alias1", "alias2"], allow_new=True)
        assert "conflicting IDs" in str(exc_info.value)
    
    def test_add_bulk_strings(self):
        ar = AliasRecord()
        ar.add_bulk(["alias1", "alias2", "alias3"], allow_new=True)
        # Each should have its own ID
        assert ar.id_of("alias1") != ar.id_of("alias2")
        assert ar.id_of("alias2") != ar.id_of("alias3")
    
    def test_add_bulk_collections(self):
        ar = AliasRecord()
        ar.add_bulk([
            ["name1", "student1"],
            ["name2", "student2"]
        ], allow_new=True)
        assert ar.id_of("name1") == ar.id_of("student1")
        assert ar.id_of("name2") == ar.id_of("student2")
        assert ar.id_of("name1") != ar.id_of("name2")


class TestAliasRecordLookup:
    """Test lookup and translation methods."""
    
    def test_id_of_found(self):
        ar = AliasRecord()
        ar.add_new_entity("test")
        assert ar.id_of("test") == 400
    
    def test_id_of_not_found(self):
        ar = AliasRecord()
        with pytest.raises(AliasNotFoundException):
            ar.id_of("nonexistent")
    
    def test_aliases_from_id_found(self):
        ar = AliasRecord()
        ar.add_together(["alias1", "alias2"])
        assert ar.all_aliases_of(id=400) == {"alias1", "alias2"}
    
    def test_aliases_from_id_not_found(self):
        ar = AliasRecord()
        with pytest.raises(IdNotFoundException):
            ar.all_aliases_of(id=999)
    
    def test_all_aliases_of(self):
        ar = AliasRecord()
        ar.add_together(["alias1", "alias2", "alias3"])
        assert ar.all_aliases_of(alias="alias1") == {"alias1", "alias2", "alias3"}
        assert ar.all_aliases_of(alias="alias2") == {"alias1", "alias2", "alias3"}
    
    def test_find_acceptable_alias_by_id_single_match(self):
        ar = AliasRecord()
        ar.add_together(["alias1", "alias2", "alias3"])
        result = ar.find_mutual_alias(["alias2", "other"], id=400)
        assert result == "alias2"
    
    def test_find_acceptable_alias_by_id_multiple_matches(self):
        ar = AliasRecord()
        ar.add_together(["alias1", "alias2", "alias3"])
        result = ar.find_mutual_alias(["alias1", "alias2"], id=400)
        assert result == {"alias1", "alias2"}
    
    def test_find_acceptable_alias_by_id_no_match(self):
        ar = AliasRecord()
        ar.add_together(["alias1", "alias2"])
        result = ar.find_mutual_alias(["other1", "other2"], id=400)
        assert result is None
    
    def test_find_acceptable_alias_by_known_alias(self):
        ar = AliasRecord()
        ar.add_together(["alias1", "alias2", "alias3"])
        result = ar.find_mutual_alias(["alias2", "other"], known_alias="alias1")
        assert result == "alias2"

    @no_type_check
    def test_find_acceptable_alias_no_params(self):
        ar = AliasRecord()
        ar.add_together("test")
        with pytest.raises(ValueError) as exc_info:
            ar.find_mutual_alias(["test"])
        assert "Must provide either id or known_alias" in str(exc_info.value)

    @no_type_check
    def test_find_acceptable_alias_both_params(self):
        ar = AliasRecord()
        ar.add_together("test")
        with pytest.raises(ValueError) as exc_info:
            ar.find_mutual_alias(["test"], id=400, known_alias="test")
        assert "Must provide only one" in str(exc_info.value)


class TestAliasRecordDataFrame:
    """Test DataFrame manipulation methods."""
    
    def test_id_of_df_single_column(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        ar.add_new_entity("student2")
        
        df = pd.DataFrame({
            "name": ["student1", "student2"],
            "grade": [90, 85]
        })
        
        result = ar.id_of_df(df, "name", expect_new_entities=False, collect_new_aliases=False)
        expected = pd.Series([400, 401], name="id", dtype=int)
        assert_series_equal(result, expected, check_series_type=False)
    
    def test_id_of_df_multiple_columns_priority(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        
        df = pd.DataFrame({
            "name": ["student1"],
            "nickname": ["stu1"],
            "grade": [90]
        })
        
        # Should find by first column
        result = ar.id_of_df(df, ["nickname", "name"], expect_new_entities=False, collect_new_aliases=True)
        # Should collect the nickname as well
        assert ar.id_of("stu1") == 400
    
    def test_id_of_df_with_index(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        
        df = pd.DataFrame({
            "grade": [90]
        }, index=pd.Index(["student1"]))
        
        result = ar.id_of_df(df, IndexFlag.Index, expect_new_entities=False, collect_new_aliases=False)
        expected = pd.Series([400], name="id", dtype=int, index=pd.Index(["student1"]))
        assert_series_equal(result, expected, check_series_type=False)
    
    def test_id_of_df_expect_new(self):
        ar = AliasRecord()
        
        df = pd.DataFrame({
            "name": ["new_student"],
            "grade": [90]
        })
        
        result = ar.id_of_df(df, "name", expect_new_entities=True, collect_new_aliases=True)
        assert result[0] >= 400  # Should create new ID
        assert "new_student" in ar
    
    def test_id_of_df_not_expect_new_raises(self):
        ar = AliasRecord()
        
        df = pd.DataFrame({
            "name": ["new_student"],
            "grade": [90]
        })
        
        with pytest.raises(AliasNotFoundException):
            ar.id_of_df(df, "name", expect_new_entities=False, collect_new_aliases=False)
    
    def test_id_of_df_with_series(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        
        df = pd.DataFrame({
            "grade": [90]
        })
        external_series = pd.Series(["student1"], index=df.index)
        
        result = ar.id_of_df(df, external_series, expect_new_entities=False, collect_new_aliases=False)
        expected = pd.Series([400], name="id", dtype=int)
        assert_series_equal(result, expected, check_series_type=False)
    
    def test_reindex_by_id_basic(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        ar.add_new_entity("student2")
        
        df = pd.DataFrame({
            "name": ["student1", "student2"],
            "grade": [90, 85]
        })
        
        result = ar.reindex_by_id(df, "name", expect_new_entities=False, collect_new_aliases=False, inplace=False)
        assert list(result.index) == [400, 401]
        assert list(result["grade"]) == [90, 85]

    @no_type_check
    def test_reindex_by_id_with_index_flag(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        
        df = pd.DataFrame({
            "grade": [90]
        }, index=pd.Index(["student1"]))
        
        result = ar.reindex_by_id(df, IndexFlag.Index, expect_new_entities=False, collect_new_aliases=False, inplace=False)
        assert list(result.index) == [400]
    
    def test_reindex_by_id_expect_new(self):
        ar = AliasRecord()
        
        df = pd.DataFrame({
            "name": ["new_student"],
            "grade": [90]
        })
        
        result = ar.reindex_by_id(df, "name", expect_new_entities=True, collect_new_aliases=True, inplace=False)
        assert len(result) == 1
        assert "new_student" in ar
    
    def test_reindex_by_id_multiple_columns(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        
        df = pd.DataFrame({
            "name": ["student1"],
            "nickname": ["stu1"],
            "grade": [90]
        })
        
        result = ar.reindex_by_id(df, ["name", "nickname"], expect_new_entities=False, collect_new_aliases=True, inplace=False)
        assert list(result.index) == [400]
        # Should collect nickname
        assert ar.id_of("stu1") == 400


class TestAliasRecordEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_alias_collection(self):
        ar = AliasRecord()
        ar.add_together([], allow_new=True)
        # Should handle gracefully (may create ID or not, depending on implementation)
    
    def test_duplicate_column_in_id_of_df(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        
        df = pd.DataFrame({
            "name": ["student1"],
            "grade": [90]
        })
        
        # Should assert due to duplicate columns
        with pytest.raises(AssertionError):
            ar.id_of_df(df, ["name", "name"], expect_new_entities=False, collect_new_aliases=False)
    
    def test_multiple_same_aliases_different_rows(self):
        ar = AliasRecord()
        ar.add_new_entity("student1")
        
        df = pd.DataFrame({
            "name": ["student1", "student1"],
            "grade": [90, 85]
        })
        
        result = ar.id_of_df(df, "name", expect_new_entities=False, collect_new_aliases=False)
        assert list(result) == [400, 400]
