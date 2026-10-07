"""Config from .env plus real env vars (env vars win). Never logs values."""
import os
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_GOAL = "Come up with ideas and solutions I can personally implement and manage, solved through interviews."


class ConfigError(Exception):
    pass


def read_env_file(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        m = re.match(r"\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$", line)
        if not m:
            continue
        val = m.group(2).strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[m.group(1)] = val
    return out


def read_goal(agents_md: Path) -> str:
    """USER_GOAL lives in AGENTS.md; strip any '(DRAFT ...)' note."""
    if agents_md.exists():
        m = re.search(r"`USER_GOAL`:\s*(.+)", agents_md.read_text())
        if m:
            return re.sub(r"\s*\(DRAFT[^)]*\)\s*$", "", m.group(1)).strip()
    return DEFAULT_GOAL


@dataclass
class Config:
    gateway_key: str
    gateway_base: str
    judge: str
    jev_model: str
    chat_model: str
    github_token: str
    youtube_key: str
    edition_dir: Path
    state_dir: Path
    goal: str
    root: Path

    def require_gateway(self):
        if not self.gateway_key:
            raise ConfigError("AI_GATEWAY_API_KEY is missing. Run setup (skills/setup.md) or add it to .env.")


def load(root: Path | None = None, environ: dict | None = None) -> Config:
    root = Path(root or Path.cwd())
    env = read_env_file(root / ".env")
    env.update({k: v for k, v in (os.environ if environ is None else environ).items() if v})

    def get(key, default=""):
        return env.get(key, default).strip()

    judge = get("JUDGE", "jev").lower()
    if judge not in ("jev", "chat"):
        raise ConfigError(f"JUDGE must be 'jev' or 'chat', got '{judge}'.")
    return Config(
        gateway_key=get("AI_GATEWAY_API_KEY"),
        gateway_base=get("AI_GATEWAY_BASE_URL", "https://ai-gateway.vercel.sh").rstrip("/"),
        judge=judge,
        jev_model=get("JEV_MODEL", "typesafe-ai/jev"),
        chat_model=get("CHAT_MODEL", "moonshotai/kimi-k3"),
        github_token=get("GITHUB_TOKEN"),
        youtube_key=get("YOUTUBE_API_KEY"),
        edition_dir=(root / get("EDITION_DIR", "./editions")).resolve(),
        state_dir=(root / get("STATE_DIR", "./state")).resolve(),
        goal=read_goal(root / "AGENTS.md"),
        root=root,
    )
