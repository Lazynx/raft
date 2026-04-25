# Raft Distributed Consensus

A 5-node Raft consensus cluster implemented in pure Python (stdlib only). Five independent services share a single JSON object and keep it consistent through leader election and log replication — with no external runtime dependencies.

## Algorithm overview

**Leader election** — every node starts as a follower with a randomised election timeout (150–300 ms). When no heartbeat arrives in time, a follower becomes a candidate, increments its term, votes for itself, and broadcasts `RequestVote` RPCs. The first candidate to collect a majority of votes becomes leader for that term.

**Log replication** — only the leader accepts writes. It appends the command to its log and replicates the entry to followers via `AppendEntries` RPCs. Once a majority acknowledges the entry the leader commits it, applies it to the state machine, and lets followers know via the next heartbeat.

**Safety** — a follower only grants a vote if the candidate's log is at least as up-to-date as its own, ensuring a newly elected leader always has every committed entry.

**Fault tolerance** — the cluster remains available as long as a majority (≥ 3 of 5) of nodes are running. A follower write is proxied to the current leader automatically.

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/status` | Node state, term, leader, log stats |
| `GET` | `/data` | Read the current shared JSON object |
| `PUT` | `/data` | Write key/value pairs into the shared object |
| `POST` | `/raft/request-vote` | Internal: RequestVote RPC |
| `POST` | `/raft/append-entries` | Internal: AppendEntries RPC |

### Write example

```bash
curl -X PUT http://localhost:8001/data \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

Writes to any node are forwarded to the leader. The response arrives once the entry is committed by a majority.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAFT_NODE_ID` | `node1` | Unique node identifier |
| `RAFT_HOST` | `0.0.0.0` | Bind address |
| `RAFT_PORT` | `8000` | Bind port |
| `RAFT_SELF_URL` | `` | This node's public URL (used in heartbeats) |
| `RAFT_PEERS` | `` | Comma-separated peer URLs |
| `RAFT_ELECTION_TIMEOUT_MIN_MS` | `150` | Minimum election timeout |
| `RAFT_ELECTION_TIMEOUT_MAX_MS` | `300` | Maximum election timeout |
| `RAFT_HEARTBEAT_INTERVAL_MS` | `50` | Leader heartbeat interval |
| `RAFT_HTTP_TIMEOUT_S` | `0.1` | Per-RPC HTTP timeout |

## Quick start

```bash
make install   # uv sync --all-extras
make run       # single node on :8000 (becomes leader immediately)
```

### 5-node cluster locally

```bash
make up    # docker compose up -d  →  nodes on ports 8001-8005
make down  # docker compose down
```

Check cluster state:

```bash
for port in 8001 8002 8003 8004 8005; do
  curl -s http://localhost:$port/status | python3 -m json.tool
done
```

## Running tests

```bash
make test-unit          # unit tests (no server required)
make test-integration   # starts 5 subprocesses, full cluster tests
make test               # both
```

## Dependencies

**Runtime:** none — pure Python 3.12 stdlib (`asyncio`, `http.server`, `urllib.request`, `dataclasses`, `json`, `threading`, `os`)

**Dev:** `pytest`, `pytest-asyncio`, `ruff`

## Architecture

```
┌─────────────────────────────────────────┐
│  ThreadingHTTPServer  (main thread)      │
│  BaseHTTPRequestHandler per request      │
│  asyncio.run_coroutine_threadsafe ───┐   │
└─────────────────────────────────────│───┘
                                      │
┌─────────────────────────────────────▼───┐
│  asyncio event loop  (daemon thread)    │
│  RaftNode._run_loop()                   │
│  ├─ heartbeats every 50 ms (leader)     │
│  └─ election timeout 150-300 ms (rest)  │
└─────────────────────────────────────────┘
         │ urllib.request in executor
         ▼
    peer nodes (same structure)
```
