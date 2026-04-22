from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.raft.models import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    DataResponse,
    HealthResponse,
    RequestVoteRequest,
    RequestVoteResponse,
    StatusResponse,
)

router = APIRouter()


def get_node(request: Request):
    return request.app.state.raft_node


@router.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/status")
async def get_status(node=Depends(get_node)) -> StatusResponse:
    async with node._lock:
        return StatusResponse(
            node_id=node.node_id,
            state=node.state,
            term=node.current_term,
            leader=node.current_leader,
            log_length=len(node.log),
            commit_index=node.commit_index,
        )


@router.get("/data")
async def get_data(node=Depends(get_node)) -> DataResponse:
    async with node._lock:
        return DataResponse(
            data=dict(node.data),
            leader=node.current_leader,
            term=node.current_term,
        )


@router.put("/data")
async def put_data(request: Request, node=Depends(get_node)) -> dict[str, Any]:
    body: dict[str, Any] = await request.json()

    async with node._lock:
        state = node.state
        leader_url = node.current_leader_url

    if state == "leader":
        try:
            committed = await node.append_command(body)
        except TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not achieve majority commit in time",
            )
        if not committed:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Lost leadership during commit",
            )
        async with node._lock:
            return {"data": dict(node.data), "committed": True}

    # Proxy to leader
    if leader_url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No leader known, try again shortly",
        )

    from src.raft.http_client import HttpClient

    result = await HttpClient(node.settings).proxy_write(leader_url, body)
    if isinstance(result, Exception):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Leader proxy failed: {result}",
        )
    return result


@router.post("/raft/request-vote")
async def request_vote(
    req: RequestVoteRequest,
    node=Depends(get_node),
) -> RequestVoteResponse:
    return await node.handle_request_vote(req)


@router.post("/raft/append-entries")
async def append_entries(
    req: AppendEntriesRequest,
    node=Depends(get_node),
) -> AppendEntriesResponse:
    return await node.handle_append_entries(req)


