import dataclasses
from typing import Any


@dataclasses.dataclass
class LogEntry:
    term: int
    command: dict[str, Any]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LogEntry":
        return cls(term=d["term"], command=d["command"])


@dataclasses.dataclass
class RequestVoteRequest:
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RequestVoteRequest":
        return cls(
            term=d["term"],
            candidate_id=d["candidate_id"],
            last_log_index=d["last_log_index"],
            last_log_term=d["last_log_term"],
        )


@dataclasses.dataclass
class RequestVoteResponse:
    term: int
    vote_granted: bool

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RequestVoteResponse":
        return cls(term=d["term"], vote_granted=d["vote_granted"])


@dataclasses.dataclass
class AppendEntriesRequest:
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: list[LogEntry]
    leader_commit: int
    leader_addr: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AppendEntriesRequest":
        return cls(
            term=d["term"],
            leader_id=d["leader_id"],
            prev_log_index=d["prev_log_index"],
            prev_log_term=d["prev_log_term"],
            entries=[LogEntry.from_dict(e) for e in d.get("entries", [])],
            leader_commit=d["leader_commit"],
            leader_addr=d.get("leader_addr", ""),
        )


@dataclasses.dataclass
class AppendEntriesResponse:
    term: int
    success: bool
    match_index: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AppendEntriesResponse":
        return cls(term=d["term"], success=d["success"], match_index=d["match_index"])


@dataclasses.dataclass
class DataResponse:
    data: dict[str, Any]
    leader: str | None
    term: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class StatusResponse:
    node_id: str
    state: str
    term: int
    leader: str | None
    log_length: int
    commit_index: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class HealthResponse:
    status: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
