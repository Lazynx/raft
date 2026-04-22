from typing import Any

import httpx

from src.raft.config import Settings
from src.raft.models import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    RequestVoteRequest,
    RequestVoteResponse,
)


class HttpClient:
    def __init__(self, settings: Settings) -> None:
        self._timeout = settings.http_timeout_s

    async def request_vote(
        self, peer_url: str, req: RequestVoteRequest
    ) -> RequestVoteResponse | Exception:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{peer_url}/raft/request-vote",
                    json=req.model_dump(),
                )
                resp.raise_for_status()
                return RequestVoteResponse.model_validate(resp.json())
        except Exception as exc:
            return exc

    async def append_entries(
        self, peer_url: str, req: AppendEntriesRequest
    ) -> AppendEntriesResponse | Exception:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{peer_url}/raft/append-entries",
                    json=req.model_dump(),
                )
                resp.raise_for_status()
                return AppendEntriesResponse.model_validate(resp.json())
        except Exception as exc:
            return exc

    async def proxy_write(
        self, leader_url: str, body: dict[str, Any]
    ) -> dict[str, Any] | Exception:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.put(f"{leader_url}/data", json=body)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            return exc
