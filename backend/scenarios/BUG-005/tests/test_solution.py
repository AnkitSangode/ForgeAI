from solution import unique_preserving_order

def test_preserves_first_occurrence_order():
    assert unique_preserving_order(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]

def test_empty_input():
    assert unique_preserving_order([]) == []
