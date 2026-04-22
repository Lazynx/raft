from src.raft.enums import NodeState
from src.raft.models import AppendEntriesRequest, LogEntry
from src.raft.node import RaftNode


def _heartbeat(term: int = 1, leader_id: str = "node2") -> AppendEntriesRequest:
    return AppendEntriesRequest(
        term=term,
        leader_id=leader_id,
        prev_log_index=-1,
        prev_log_term=0,
        entries=[],
        leader_commit=-1,
    )


async def test_heartbeat_success(node: RaftNode):
    resp = await node.handle_append_entries(_heartbeat())
    assert resp.success is True
    assert node.state == NodeState.FOLLOWER
    assert node.current_leader == "node2"


async def test_reject_stale_term(node: RaftNode):
    node.current_term = 3
    resp = await node.handle_append_entries(_heartbeat(term=1))
    assert resp.success is False
    assert resp.term == 3


async def test_step_down_on_higher_term(node: RaftNode):
    node.current_term = 1
    node.state = NodeState.CANDIDATE
    resp = await node.handle_append_entries(_heartbeat(term=2))
    assert resp.success is True
    assert node.current_term == 2
    assert node.state == NodeState.FOLLOWER


async def test_reject_missing_prev_log(node: RaftNode):
    req = AppendEntriesRequest(
        term=1,
        leader_id="node2",
        prev_log_index=2,
        prev_log_term=1,
        entries=[],
        leader_commit=-1,
    )
    resp = await node.handle_append_entries(req)
    assert resp.success is False


async def test_reject_wrong_prev_term(node: RaftNode):
    node.current_term = 1
    node.log = [LogEntry(term=1, command={"x": 1})]
    req = AppendEntriesRequest(
        term=1,
        leader_id="node2",
        prev_log_index=0,
        prev_log_term=2,
        entries=[],
        leader_commit=-1,
    )
    resp = await node.handle_append_entries(req)
    assert resp.success is False
    assert len(node.log) == 0


async def test_append_entries_adds_to_log(node: RaftNode):
    node.current_term = 1
    req = AppendEntriesRequest(
        term=1,
        leader_id="node2",
        prev_log_index=-1,
        prev_log_term=0,
        entries=[LogEntry(term=1, command={"x": 1})],
        leader_commit=-1,
    )
    resp = await node.handle_append_entries(req)
    assert resp.success is True
    assert len(node.log) == 1
    assert node.log[0].command == {"x": 1}


async def test_advance_commit_applies_data(node: RaftNode):
    node.current_term = 1
    req = AppendEntriesRequest(
        term=1,
        leader_id="node2",
        prev_log_index=-1,
        prev_log_term=0,
        entries=[LogEntry(term=1, command={"hello": "world"})],
        leader_commit=0,
    )
    resp = await node.handle_append_entries(req)
    assert resp.success is True
    assert node.commit_index == 0
    assert node.last_applied == 0
    assert node.data == {"hello": "world"}


async def test_updates_term_on_higher_term(node: RaftNode):
    node.current_term = 1
    resp = await node.handle_append_entries(_heartbeat(term=5))
    assert node.current_term == 5


async def test_idempotent_same_entries(node: RaftNode):
    node.current_term = 1
    entry = LogEntry(term=1, command={"k": "v"})
    req = AppendEntriesRequest(
        term=1,
        leader_id="node2",
        prev_log_index=-1,
        prev_log_term=0,
        entries=[entry],
        leader_commit=-1,
    )
    await node.handle_append_entries(req)
    await node.handle_append_entries(req)
    assert len(node.log) == 1


async def test_overwrite_conflicting_entry(node: RaftNode):
    node.current_term = 2
    node.log = [LogEntry(term=1, command={"old": 1})]
    req = AppendEntriesRequest(
        term=2,
        leader_id="node2",
        prev_log_index=-1,
        prev_log_term=0,
        entries=[LogEntry(term=2, command={"new": 2})],
        leader_commit=-1,
    )
    resp = await node.handle_append_entries(req)
    assert resp.success is True
    assert len(node.log) == 1
    assert node.log[0].command == {"new": 2}
