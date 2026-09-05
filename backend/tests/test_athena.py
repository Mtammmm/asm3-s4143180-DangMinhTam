import pytest

from app.athena import build_query
from app.errors import ApiError


COLUMNS = [{"source": "City", "name": "city"}, {"source": "Revenue", "name": "revenue"}]


def test_contains_query_escapes_sql_literal():
    query = build_query("dataset_abc", COLUMNS, "city", "contains", "O'Reilly%")
    assert 'FROM "dataset_abc"' in query
    assert "O''Reilly%" in query
    assert "strpos(" in query
    assert "COUNT(*) OVER()" in query
    assert query.endswith("LIMIT 100")


def test_numeric_query_rejects_non_numeric_value():
    with pytest.raises(ApiError) as error:
        build_query("dataset_abc", COLUMNS, "revenue", "greater", "not-a-number")
    assert error.value.code == "INVALID_QUERY_VALUE"
