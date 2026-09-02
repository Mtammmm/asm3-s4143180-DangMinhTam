from csv_processor.main import analyze_csv


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
