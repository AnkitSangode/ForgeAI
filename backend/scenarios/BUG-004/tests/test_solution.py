import pytest
from solution import paginate

def test_pagination_slice():
    assert paginate(list(range(10)), 3, 2) == [2, 3, 4]

@pytest.mark.parametrize("limit, offset", [(0, 0), (101, 0), (-1, 0), (10, -1)])
def test_invalid_pagination(limit, offset):
    with pytest.raises(ValueError):
        paginate(list(range(10)), limit, offset)
