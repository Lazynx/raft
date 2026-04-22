from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAFT_", env_file=".env", extra="ignore")

    node_id: str = "node1"
    peers: str = ""
    host: str = "0.0.0.0"
    port: int = 8000

    election_timeout_min_ms: int = 150
    election_timeout_max_ms: int = 300
    heartbeat_interval_ms: int = 50
    http_timeout_s: float = 0.1
    self_url: str = ""

    @property
    def peer_urls(self) -> list[str]:
        return [p.strip() for p in self.peers.split(",") if p.strip()]


settings = Settings()
