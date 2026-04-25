import asyncio
import json
from http.server import BaseHTTPRequestHandler
from typing import Any

from src.raft.enums import NodeState
from src.raft.models import (
    AppendEntriesRequest,
    DataResponse,
    HealthResponse,
    RequestVoteRequest,
    StatusResponse,
)


def make_handler(node: Any, loop: asyncio.AbstractEventLoop) -> type[BaseHTTPRequestHandler]:
    class RaftHandler(BaseHTTPRequestHandler):
        def _run(self, coro):
            return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=5)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length)) if length else {}

        def _send_json(self, status: int, data: dict) -> None:
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:
            pass

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send_json(200, HealthResponse(status="ok").to_dict())

            elif self.path == "/status":

                async def _status():
                    async with node._lock:
                        return StatusResponse(
                            node_id=node.node_id,
                            state=node.state,
                            term=node.current_term,
                            leader=node.current_leader,
                            log_length=len(node.log),
                            commit_index=node.commit_index,
                        ).to_dict()

                self._send_json(200, self._run(_status()))

            elif self.path == "/data":

                async def _data():
                    async with node._lock:
                        return DataResponse(
                            data=dict(node.data),
                            leader=node.current_leader,
                            term=node.current_term,
                        ).to_dict()

                self._send_json(200, self._run(_data()))

            else:
                self._send_json(404, {"detail": "not found"})

        def do_PUT(self) -> None:
            if self.path != "/data":
                self._send_json(404, {"detail": "not found"})
                return

            body = self._read_json()

            async def _get_state():
                async with node._lock:
                    return node.state, node.current_leader_url

            state, leader_url = self._run(_get_state())

            if state == NodeState.LEADER:
                try:
                    committed = self._run(node.append_command(body))
                except TimeoutError:
                    self._send_json(503, {"detail": "Could not achieve majority commit in time"})
                    return
                if not committed:
                    self._send_json(503, {"detail": "Lost leadership during commit"})
                    return

                async def _get_data():
                    async with node._lock:
                        return dict(node.data)

                self._send_json(200, {"data": self._run(_get_data()), "committed": True})
                return

            if leader_url is None:
                self._send_json(503, {"detail": "No leader known, try again shortly"})
                return

            from src.raft.http_client import HttpClient

            result = self._run(HttpClient(node.settings).proxy_write(leader_url, body))
            if isinstance(result, Exception):
                self._send_json(502, {"detail": f"Leader proxy failed: {result}"})
                return

            self._send_json(200, result)

        def do_POST(self) -> None:
            if self.path == "/raft/request-vote":
                req = RequestVoteRequest.from_dict(self._read_json())
                resp = self._run(node.handle_request_vote(req))
                self._send_json(200, resp.to_dict())

            elif self.path == "/raft/append-entries":
                req = AppendEntriesRequest.from_dict(self._read_json())
                resp = self._run(node.handle_append_entries(req))
                self._send_json(200, resp.to_dict())

            else:
                self._send_json(404, {"detail": "not found"})

    return RaftHandler
