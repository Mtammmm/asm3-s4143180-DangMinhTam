from csv_processor.main import analyze_csv, athena_columns


def test_semicolon_csv_is_aligned_into_columns():
    content = (
        "id;age;gender;height;weight\n"
        "0;18;1;93;42\n"
        "1;20;2;88;55\n"
    ).encode("utf-8")
    headers, rows, stats = analyze_csv(content)
    assert headers == ["id", "age", "gender", "height", "weight"]
    assert rows[0] == ["0", "18", "1", "93", "42"]
    assert stats == {"rows": 2, "columns": 5, "missingValues": 0, "completeness": 100}


def test_quoted_commas_remain_in_one_value():
    content = 'id,name,city\n1,"Morgan, Alex",Melbourne\n'.encode("utf-8")
    headers, rows, stats = analyze_csv(content)
    assert headers == ["id", "name", "city"]
    assert rows == [["1", "Morgan, Alex", "Melbourne"]]
    assert stats["columns"] == 3


def test_athena_column_names_are_safe_and_unique():
    assert athena_columns(["Order ID", "Order ID", "2026 Total", ""]) == [
        {"source": "Order ID", "name": "order_id"},
        {"source": "Order ID", "name": "order_id_2"},
        {"source": "2026 Total", "name": "column_3_2026_total"},
        {"source": "", "name": "column_4"},
    ]
