import pytest
from solution import use_resource

class Resource:
    def __init__(self):
        self.close_calls = 0
    def close(self):
        self.close_calls += 1

def test_closes_after_success():
    resource = Resource()
    assert use_resource(resource, lambda r: "ok") == "ok"
    assert resource.close_calls == 1

def test_closes_after_exception():
    resource = Resource()
    def fail(_):
        raise RuntimeError("boom")
    with pytest.raises(RuntimeError):
        use_resource(resource, fail)
    assert resource.close_calls == 1
