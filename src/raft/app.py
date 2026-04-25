import asyncio
import threading
from http.server import ThreadingHTTPServer

from src.raft.config import settings
from src.raft.node import RaftNode
from src.raft.router import make_handler


async def main() -> None:
    node = RaftNode(settings)
    loop = asyncio.get_event_loop()
    await node.start()

    handler_class = make_handler(node, loop)
    server = ThreadingHTTPServer((settings.host, settings.port), handler_class)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        await asyncio.Event().wait()
    finally:
        server.shutdown()
        await node.stop()
