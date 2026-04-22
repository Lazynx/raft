import pytest

from src.raft.enums import NodeState
from src.raft.models import LogEntry, RequestVoteRequest
from src.raft.node import RaftNode


async def test_grant_vote_valid_term(node: RaftNode):
    req = RequestVoteRequest(term=1, candidate_id="node2", last_log_index=-1, last_log_term=0)
    resp = await node.handle_request_vote(req)
    assert resp.vote_granted is True
    assert resp.term == 1
    assert node.voted_for == "node2"


async def test_deny_vote_stale_term(node: RaftNode):
    node.current_term = 5
    req = RequestVoteRequest(term=3, candidate_id="node2", last_log_index=-1, last_log_term=0)
    resp = await node.handle_request_vote(req)
    assert resp.vote_granted is False
    assert resp.term == 5


async def test_deny_vote_already_voted(node: RaftNode):
    node.current_term = 1
    node.voted_for = "node2"
    req = RequestVoteRequest(term=1, candidate_id="node3", last_log_index=-1, last_log_term=0)
    resp = await node.handle_request_vote(req)
    assert resp.vote_granted is False


async def test_grant_vote_same_candidate_idempotent(node: RaftNode):
    node.current_term = 1
    node.voted_for = "node2"
    req = RequestVoteRequest(term=1, candidate_id="node2", last_log_index=-1, last_log_term=0)
    resp = await node.handle_request_vote(req)
    assert resp.vote_granted is True


async def test_deny_vote_stale_log_lower_term(node: RaftNode):
    node.log = [LogEntry(term=2, command={})]
    req = RequestVoteRequest(term=3, candidate_id="node2", last_log_index=0, last_log_term=1)
    resp = await node.handle_request_vote(req)
    assert resp.vote_granted is False


async def test_deny_vote_stale_log_shorter(node: RaftNode):
    node.log = [LogEntry(term=1, command={}), LogEntry(term=1, command={})]
    req = RequestVoteRequest(term=2, candidate_id="node2", last_log_index=0, last_log_term=1)
    resp = await node.handle_request_vote(req)
    assert resp.vote_granted is False


async def test_higher_term_resets_voted_for(node: RaftNode):
    node.current_term = 2
    node.voted_for = "node2"
    node.state = NodeState.LEADER
    req = RequestVoteRequest(term=3, candidate_id="node3", last_log_index=-1, last_log_term=0)
    resp = await node.handle_request_vote(req)
    assert node.current_term == 3
    assert node.state == NodeState.FOLLOWER
    # voted_for was reset then possibly re-set to node3
    assert resp.vote_granted is True
    assert node.voted_for == "node3"


async def test_grant_vote_with_longer_candidate_log(node: RaftNode):
    node.log = [LogEntry(term=1, command={})]
    req = RequestVoteRequest(term=2, candidate_id="node2", last_log_index=1, last_log_term=1)
    resp = await node.handle_request_vote(req)
    assert resp.vote_granted is True
