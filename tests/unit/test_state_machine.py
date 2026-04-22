import pytest

from src.raft.models import LogEntry
from src.raft.node import RaftNode


async def test_apply_single_entry(node: RaftNode):
    node.log = [LogEntry(term=1, command={"key": "value"})]
    node.commit_index = 0
    node._apply_committed()
    assert node.data == {"key": "value"}
    assert node.last_applied == 0


async def test_apply_multiple_entries(node: RaftNode):
    node.log = [
        LogEntry(term=1, command={"a": 1}),
        LogEntry(term=1, command={"b": 2}),
        LogEntry(term=1, command={"c": 3}),
    ]
    node.commit_index = 2
    node._apply_committed()
    assert node.data == {"a": 1, "b": 2, "c": 3}
    assert node.last_applied == 2


async def test_apply_overwrite_key(node: RaftNode):
    node.log = [
        LogEntry(term=1, command={"x": 1}),
        LogEntry(term=1, command={"x": 99}),
    ]
    node.commit_index = 1
    node._apply_committed()
    assert node.data == {"x": 99}


async def test_partial_commit(node: RaftNode):
    node.log = [
        LogEntry(term=1, command={"a": 1}),
        LogEntry(term=1, command={"b": 2}),
        LogEntry(term=1, command={"c": 3}),
    ]
    node.commit_index = 1
    node._apply_committed()
    assert node.data == {"a": 1, "b": 2}
    assert node.last_applied == 1
    assert "c" not in node.data


async def test_no_double_apply(node: RaftNode):
    node.log = [LogEntry(term=1, command={"x": 1})]
    node.commit_index = 0
    node._apply_committed()
    node.data["x"] = 999
    node._apply_committed()
    # Should not re-apply the first entry
    assert node.data["x"] == 999
    assert node.last_applied == 0


async def test_no_apply_when_nothing_committed(node: RaftNode):
    node.log = [LogEntry(term=1, command={"x": 1})]
    node.commit_index = -1
    node._apply_committed()
    assert node.data == {}
    assert node.last_applied == -1


async def test_merge_partial_update(node: RaftNode):
    node.data = {"existing": "yes"}
    node.log = [LogEntry(term=1, command={"new_key": "new_val"})]
    node.commit_index = 0
    node._apply_committed()
    assert node.data == {"existing": "yes", "new_key": "new_val"}
