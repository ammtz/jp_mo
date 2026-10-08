"""Tiny stdlib HTTP layer. Swappable so tests and --dry-run never touch the network."""
import json
import time
import urllib.error
import urllib.request

USER_AGENT = "jp_mo"


class HttpError(Exception):
    def __init__(self, status: int, message: str, headers: dict | None = None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.headers = headers or {}


class Http:
    def __init__(self, timeout: float = 20, retries: int = 1, sleep=time.sleep):
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleep

    def request(self, method: str, url: str, headers: dict | None = None, body=None, raw: bool = False):
        """Returns (status, headers, parsed JSON or text). Retries network errors and 5xx."""
        hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
        last = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    text = r.read().decode("utf-8", "replace")
                    return r.status, dict(r.headers), (text if raw else json.loads(text))
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "replace")[:300]
                last = HttpError(e.code, msg, dict(e.headers))
                if e.code < 500:
                    raise last
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last = HttpError(0, str(e))
            if attempt < self.retries:
                self.sleep(1)
        raise last

    def get_json(self, url, headers=None):
        return self.request("GET", url, headers)[2]

    def get_text(self, url, headers=None):
        return self.request("GET", url, headers, raw=True)[2]

    def post_json(self, url, body, headers=None):
        return self.request("POST", url, headers, body)[2]
