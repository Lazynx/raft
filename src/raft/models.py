from typing import Any

from pydantic import BaseModel


class LogEntry(BaseModel):
    term: int
    command: dict[str, Any]


class RequestVoteRequest(BaseModel):
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


class RequestVoteResponse(BaseModel):
    term: int
    vote_granted: bool


class AppendEntriesRequest(BaseModel):
    term: int
    leader_id: str
    leader_addr: str = ""
    prev_log_index: int
    prev_log_term: int
    entries: list[LogEntry]
    leader_commit: int


class AppendEntriesResponse(BaseModel):
    term: int
    success: bool
    match_index: int


class DataResponse(BaseModel):
    data: dict[str, Any]
    leader: str | None
    term: int


class StatusResponse(BaseModel):
    node_id: str
    state: str
    term: int
    leader: str | None
    log_length: int
    commit_index: int


class HealthResponse(BaseModel):
    status: str
