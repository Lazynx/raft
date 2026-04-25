import os


class Settings:
    def __init__(
        self,
        node_id: str | None = None,
        peers: str | None = None,
        host: str | None = None,
        port: int | None = None,
        election_timeout_min_ms: int | None = None,
        election_timeout_max_ms: int | None = None,
        heartbeat_interval_ms: int | None = None,
        http_timeout_s: float | None = None,
        self_url: str | None = None,
    ):
        self.node_id = node_id if node_id is not None else os.environ.get("RAFT_NODE_ID", "node1")
        self.peers = peers if peers is not None else os.environ.get("RAFT_PEERS", "")
        self.host = host if host is not None else os.environ.get("RAFT_HOST", "0.0.0.0")
        self.port = port if port is not None else int(os.environ.get("RAFT_PORT", "8000"))
        self.election_timeout_min_ms = (
            election_timeout_min_ms
            if election_timeout_min_ms is not None
            else int(os.environ.get("RAFT_ELECTION_TIMEOUT_MIN_MS", "150"))
        )
        self.election_timeout_max_ms = (
            election_timeout_max_ms
            if election_timeout_max_ms is not None
            else int(os.environ.get("RAFT_ELECTION_TIMEOUT_MAX_MS", "300"))
        )
        self.heartbeat_interval_ms = (
            heartbeat_interval_ms
            if heartbeat_interval_ms is not None
            else int(os.environ.get("RAFT_HEARTBEAT_INTERVAL_MS", "50"))
        )
        self.http_timeout_s = (
            http_timeout_s
            if http_timeout_s is not None
            else float(os.environ.get("RAFT_HTTP_TIMEOUT_S", "0.1"))
        )
        self.self_url = self_url if self_url is not None else os.environ.get("RAFT_SELF_URL", "")

    @property
    def peer_urls(self) -> list[str]:
        return [p.strip() for p in self.peers.split(",") if p.strip()]


settings = Settings()
