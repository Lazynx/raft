import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections.abc import Generator

import pytest

PORTS = {f"node{i}": 8000 + i for i in range(1, 6)}
BASE_URLS = {node_id: f"http://localhost:{port}" for node_id, port in PORTS.items()}
ALL_URLS = list(BASE_URLS.values())


def _make_env(node_id: str) -> dict[str, str]:
    port = PORTS[node_id]
    peers = ",".join(url for nid, url in BASE_URLS.items() if nid != node_id)
    return {
        **os.environ,
        "RAFT_NODE_ID": node_id,
        "RAFT_SELF_URL": f"http://localhost:{port}",
        "RAFT_PEERS": peers,
        "RAFT_PORT": str(port),
        "RAFT_HOST": "0.0.0.0",
        "RAFT_ELECTION_TIMEOUT_MIN_MS": "150",
        "RAFT_ELECTION_TIMEOUT_MAX_MS": "300",
        "RAFT_HEARTBEAT_INTERVAL_MS": "50",
        "RAFT_HTTP_TIMEOUT_S": "0.1",
    }


def _start_node(node_id: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "src.raft"],
        env=_make_env(node_id),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="module")
def cluster() -> Generator[dict[str, subprocess.Popen], None, None]:
    procs: dict[str, subprocess.Popen] = {}
    for node_id in PORTS:
        procs[node_id] = _start_node(node_id)

    _wait_all_healthy(ALL_URLS, timeout_s=15.0)
    yield procs

    for p in procs.values():
        if p.poll() is None:
            p.terminate()
    for p in procs.values():
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def _wait_all_healthy(urls: list[str], timeout_s: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_s
    ready = 0
    while time.monotonic() < deadline:
        ready = 0
        for url in urls:
            try:
                with urllib.request.urlopen(f"{url}/health", timeout=0.5) as r:
                    if r.status == 200:
                        ready += 1
            except Exception:
                pass
        if ready == len(urls):
            return
        time.sleep(0.1)
    raise RuntimeError(f"Only {ready}/{len(urls)} nodes became healthy within {timeout_s}s")


async def _async_request(
    method: str, url: str, body: dict | None, timeout: float
) -> tuple[int, dict]:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or 80
    path = parsed.path or "/"
    payload = json.dumps(body).encode() if body is not None else b""
    request_lines = [
        f"{method} {path} HTTP/1.1",
        f"Host: {host}:{port}",
        "Content-Type: application/json",
        f"Content-Length: {len(payload)}",
        "Connection: close",
        "",
        "",
    ]
    request_bytes = "\r\n".join(request_lines).encode() + payload
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    try:
        writer.write(request_bytes)
        await writer.drain()
        status_line = await reader.readline()
        status_code = int(status_line.decode().split()[1])
        resp_headers: dict[str, str] = {}
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break
            key, _, val = line.decode().partition(":")
            resp_headers[key.lower().strip()] = val.strip()
        content_length = int(resp_headers.get("content-length", "0"))
        body_bytes = await reader.readexactly(content_length) if content_length > 0 else b""
    finally:
        writer.close()
    return status_code, json.loads(body_bytes) if body_bytes else {}


async def _async_get(url: str, timeout: float = 1.0) -> tuple[int, dict]:
    return await _async_request("GET", url, None, timeout)


async def _async_put(url: str, body: dict, timeout: float = 5.0) -> tuple[int, dict]:
    return await _async_request("PUT", url, body, timeout)


async def wait_for_single_leader(urls: list[str], timeout_s: float = 5.0) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        leaders: list[str] = []
        for url in urls:
            try:
                status, body = await _async_get(f"{url}/status", timeout=0.5)
                if status == 200 and body.get("state") == "leader":
                    leaders.append(body["node_id"])
            except Exception:
                pass
        if len(leaders) == 1:
            return leaders[0]
        await asyncio.sleep(0.1)
    raise TimeoutError(f"No single leader elected within {timeout_s}s")


async def get_data(url: str) -> dict | None:
    try:
        status, body = await _async_get(f"{url}/data", timeout=1.0)
        return body if status == 200 else None
    except Exception:
        return None


async def put_data(url: str, body: dict) -> dict | None:
    try:
        status, resp = await _async_put(f"{url}/data", body, timeout=5.0)
        return resp if status == 200 else None
    except Exception:
        return None


async def wait_for_data(urls: list[str], key: str, value, timeout_s: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        found = 0
        for url in urls:
            d = await get_data(url)
            if d and d.get("data", {}).get(key) == value:
                found += 1
        if found == len(urls):
            return True
        await asyncio.sleep(0.1)
    return False


def _ensure_cluster_healthy(cluster: dict[str, subprocess.Popen]) -> None:
    for node_id, proc in cluster.items():
        if proc.poll() is not None:
            cluster[node_id] = _start_node(node_id)
    _wait_all_healthy(ALL_URLS, timeout_s=10.0)


async def test_single_leader_elected(cluster):
    leader_id = await wait_for_single_leader(ALL_URLS)
    assert leader_id is not None
    assert leader_id.startswith("node")


async def test_only_one_leader_at_a_time(cluster):
    for _ in range(10):
        leaders = []
        for url in ALL_URLS:
            try:
                status, body = await _async_get(f"{url}/status", timeout=0.5)
                if status == 200 and body["state"] == "leader":
                    leaders.append(body["node_id"])
            except Exception:
                pass
        assert len(leaders) <= 1, f"Multiple leaders: {leaders}"
        await asyncio.sleep(0.1)


async def test_write_to_leader_replicated_to_all(cluster):
    leader_id = await wait_for_single_leader(ALL_URLS)
    leader_url = BASE_URLS[leader_id]

    result = await put_data(leader_url, {"replicated_key": "replicated_value"})
    assert result is not None, f"Write to leader failed: {leader_url}"

    ok = await wait_for_data(ALL_URLS, "replicated_key", "replicated_value")
    assert ok, "Data was not replicated to all nodes within timeout"


async def test_write_to_follower_proxied_to_leader(cluster):
    leader_id = await wait_for_single_leader(ALL_URLS)
    follower_url = next(url for nid, url in BASE_URLS.items() if nid != leader_id)

    result = await put_data(follower_url, {"proxied_key": "proxied_value"})
    assert result is not None, "Follower should proxy write to leader and return 200"

    ok = await wait_for_data(ALL_URLS, "proxied_key", "proxied_value")
    assert ok, "Proxied write was not replicated to all nodes"


async def test_read_from_any_node_returns_latest(cluster):
    leader_id = await wait_for_single_leader(ALL_URLS)
    leader_url = BASE_URLS[leader_id]

    result = await put_data(leader_url, {"read_test": 42})
    assert result is not None

    await asyncio.sleep(0.3)

    values = []
    for url in ALL_URLS:
        d = await get_data(url)
        if d:
            values.append(d["data"].get("read_test"))

    assert all(v == 42 for v in values), f"Inconsistent reads: {values}"


async def test_kill_leader_new_leader_elected(cluster):
    leader_id = await wait_for_single_leader(ALL_URLS)
    cluster[leader_id].kill()
    cluster[leader_id].wait(timeout=3)

    surviving_urls = [url for nid, url in BASE_URLS.items() if nid != leader_id]
    new_leader = await wait_for_single_leader(surviving_urls, timeout_s=5.0)
    assert new_leader != leader_id

    cluster[leader_id] = _start_node(leader_id)
    _wait_all_healthy([BASE_URLS[leader_id]], timeout_s=8.0)
    await asyncio.sleep(0.5)


async def test_write_read_after_failover(cluster):
    _ensure_cluster_healthy(cluster)
    leader_id = await wait_for_single_leader(ALL_URLS, timeout_s=5.0)

    cluster[leader_id].kill()
    cluster[leader_id].wait(timeout=3)

    surviving_urls = [url for nid, url in BASE_URLS.items() if nid != leader_id]
    new_leader_id = await wait_for_single_leader(surviving_urls, timeout_s=5.0)
    new_leader_url = BASE_URLS[new_leader_id]

    result = await put_data(new_leader_url, {"failover_key": "ok"})
    assert result is not None, "Write after failover failed"

    ok = await wait_for_data(surviving_urls, "failover_key", "ok")
    assert ok, "Data not replicated after failover"

    cluster[leader_id] = _start_node(leader_id)
    _wait_all_healthy([BASE_URLS[leader_id]], timeout_s=8.0)
    await asyncio.sleep(0.5)


async def test_minority_cannot_commit(cluster):
    _ensure_cluster_healthy(cluster)
    await wait_for_single_leader(ALL_URLS, timeout_s=5.0)

    killed = list(PORTS.keys())[:3]
    for nid in killed:
        cluster[nid].kill()
        cluster[nid].wait(timeout=3)

    surviving_urls = [BASE_URLS[nid] for nid in PORTS if nid not in killed]

    write_succeeded = False
    for url in surviving_urls:
        result = await put_data(url, {"minority_write": True})
        if result is not None:
            write_succeeded = True
            break

    assert not write_succeeded, "Minority cluster should not be able to commit writes"

    for nid in killed:
        cluster[nid] = _start_node(nid)
    _wait_all_healthy([BASE_URLS[nid] for nid in killed], timeout_s=10.0)
    await asyncio.sleep(1.0)


async def test_rejoin_node_catches_up(cluster):
    _ensure_cluster_healthy(cluster)
    leader_id = await wait_for_single_leader(ALL_URLS, timeout_s=5.0)

    follower_id = next(nid for nid in PORTS if nid != leader_id)
    cluster[follower_id].kill()
    cluster[follower_id].wait(timeout=3)

    leader_url = BASE_URLS[leader_id]
    for i in range(5):
        r = await put_data(leader_url, {f"catchup_{i}": i})
        assert r is not None, f"Write {i} failed during follower downtime"

    cluster[follower_id] = _start_node(follower_id)
    _wait_all_healthy([BASE_URLS[follower_id]], timeout_s=8.0)

    await asyncio.sleep(1.5)

    data = await get_data(BASE_URLS[follower_id])
    assert data is not None
    for i in range(5):
        assert data["data"].get(f"catchup_{i}") == i, (
            f"catchup_{i} missing from rejoined node — got: {data['data']}"
        )
