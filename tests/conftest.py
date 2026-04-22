import pytest

from src.raft.config import Settings
from src.raft.node import RaftNode


@pytest.fixture
def settings():
    return Settings(
        node_id="node1",
        peers="http://node2:8000,http://node3:8000,http://node4:8000,http://node5:8000",
        election_timeout_min_ms=150,
        election_timeout_max_ms=300,
        heartbeat_interval_ms=50,
        http_timeout_s=0.1,
    )


@pytest.fixture
def node(settings):
    return RaftNode(settings)
