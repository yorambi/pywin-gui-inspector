import time
import pytest
from pywin_gui_inspector.live.cache import TTLCache


class TestTTLCache:
    def test_set_and_get_hit(self):
        c = TTLCache(ttl=60)
        c.set("k", "v")
        val, hit = c.get("k")
        assert hit is True
        assert val == "v"

    def test_missing_key_is_miss(self):
        c = TTLCache(ttl=60)
        val, hit = c.get("missing")
        assert hit is False
        assert val is None

    def test_expired_entry_is_miss(self):
        c = TTLCache(ttl=0.05)
        c.set("k", "v")
        time.sleep(0.1)
        _, hit = c.get("k")
        assert hit is False

    def test_clear_removes_all_entries(self):
        c = TTLCache(ttl=60)
        c.set("k1", "a")
        c.set("k2", "b")
        c.clear()
        assert c.get("k1")[1] is False
        assert c.get("k2")[1] is False

    def test_overwrite_refreshes_ttl(self):
        c = TTLCache(ttl=0.1)
        c.set("k", "v1")
        time.sleep(0.08)
        c.set("k", "v2")   # reset TTL
        time.sleep(0.06)   # would have expired with original TTL
        val, hit = c.get("k")
        assert hit is True
        assert val == "v2"

    def test_stores_any_value_type(self):
        c = TTLCache(ttl=60)
        c.set("list",  [1, 2, 3])
        c.set("dict",  {"a": 1})
        c.set("none",  None)
        assert c.get("list")[0] == [1, 2, 3]
        assert c.get("dict")[0] == {"a": 1}
        assert c.get("none")[0] is None