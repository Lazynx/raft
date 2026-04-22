from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.raft.config import settings
from src.raft.node import RaftNode
from src.raft.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    node = RaftNode(settings)
    app.state.raft_node = node
    await node.start()
    try:
        yield
    finally:
        await node.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Raft Node",
        description="Raft distributed consensus — single node instance",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app
