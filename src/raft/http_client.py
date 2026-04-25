import asyncio
import json
import urllib.request
from typing import Any

from src.raft.config import Settings
from src.raft.models import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    RequestVoteRequest,
    RequestVoteResponse,
)


def _sync_post(url: str, body: dict, timeout: float) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _sync_put(url: str, body: dict, timeout: float) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="PUT"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


async def _async_post(url: str, body: dict, timeout: float) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_post, url, body, timeout)


async def _async_put(url: str, body: dict, timeout: float) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_put, url, body, timeout)


class HttpClient:
    def __init__(self, settings: Settings) -> None:
        self._timeout = settings.http_timeout_s

    async def request_vote(
        self, peer_url: str, req: RequestVoteRequest
    ) -> RequestVoteResponse | Exception:
        try:
            data = await _async_post(f"{peer_url}/raft/request-vote", req.to_dict(), self._timeout)
            return RequestVoteResponse.from_dict(data)
        except Exception as exc:
            return exc

    async def append_entries(
        self, peer_url: str, req: AppendEntriesRequest
    ) -> AppendEntriesResponse | Exception:
        try:
            data = await _async_post(
                f"{peer_url}/raft/append-entries", req.to_dict(), self._timeout
            )
            return AppendEntriesResponse.from_dict(data)
        except Exception as exc:
            return exc

    async def proxy_write(
        self, leader_url: str, body: dict[str, Any]
    ) -> dict[str, Any] | Exception:
        try:
            return await _async_put(f"{leader_url}/data", body, timeout=5.0)
        except Exception as exc:
            return exc
