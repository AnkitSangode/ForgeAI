from solution import can_access

def test_owner_can_access():
    assert can_access("u1", "u1") is True

def test_other_user_denied():
    assert can_access("u1", "u2") is False

def test_admin_can_access():
    assert can_access("u1", "u2", is_admin=True) is True
