from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def load_local_env(env_path: str = ".env") -> None:
    path = Path(env_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class SupabaseConfig:
    url: str
    key: str
    schema: str = "public"


def get_supabase_config(prefer_service_role: bool = False) -> SupabaseConfig | None:
    load_local_env()

    url = (
        os.getenv("SUPABASE_URL", "").strip()
        or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    ).rstrip("/")
    if not url:
        return None

    keys = [
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
        os.getenv("SUPABASE_ANON_KEY", "").strip()
        or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "").strip(),
        os.getenv("SUPABASE_KEY", "").strip(),
    ]
    if not prefer_service_role:
        keys = [keys[1], keys[0], keys[2]]

    key = next((item for item in keys if item), "")
    if not key:
        return None

    schema = os.getenv("SUPABASE_SCHEMA", "public").strip() or "public"
    return SupabaseConfig(url=url, key=key, schema=schema)


class SupabaseRestClient:
    def __init__(self, config: SupabaseConfig):
        self.config = config

    @classmethod
    def from_env(cls, prefer_service_role: bool = False) -> "SupabaseRestClient":
        config = get_supabase_config(prefer_service_role=prefer_service_role)
        if config is None:
            raise RuntimeError(
                "Supabase configuration is missing. Set SUPABASE_URL and a key in .env or the shell."
            )
        return cls(config)

    def _headers(self, content: bool = False, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.config.key,
            "Authorization": f"Bearer {self.config.key}",
            "Accept": "application/json",
            "Accept-Profile": self.config.schema,
        }
        if content:
            headers["Content-Type"] = "application/json"
            headers["Content-Profile"] = self.config.schema
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request(
        self,
        method: str,
        resource: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
        query_string = ""
        if query:
            query_string = urllib.parse.urlencode(query, doseq=True, safe="(),:*")

        url = f"{self.config.url}/rest/v1/{resource}"
        if query_string:
            url = f"{url}?{query_string}"

        payload = None
        if body is not None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=payload,
            headers=self._headers(content=body is not None, prefer=prefer),
            method=method,
        )

        try:
            with urllib.request.urlopen(request) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Supabase REST request failed ({exc.code}): {detail}") from exc

        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))

    def select_rows(
        self,
        resource: str,
        *,
        query: dict[str, Any] | None = None,
        paginate: bool = True,
        page_size: int = 1000,
    ) -> list[dict[str, Any]]:
        base_query = dict(query or {})
        if not paginate:
            result = self._request("GET", resource, query=base_query)
            return result or []

        offset = 0
        rows: list[dict[str, Any]] = []
        while True:
            page_query = dict(base_query)
            page_query["limit"] = page_size
            page_query["offset"] = offset
            page = self._request("GET", resource, query=page_query) or []
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += page_size
        return rows

    def insert_rows(
        self,
        resource: str,
        rows: list[dict[str, Any]],
        *,
        upsert: bool = False,
        on_conflict: str | None = None,
        returning: str = "representation",
    ) -> Any:
        if not rows:
            return []

        prefer_bits = [f"return={returning}"]
        if upsert:
            prefer_bits.append("resolution=merge-duplicates")

        query: dict[str, Any] = {}
        if on_conflict:
            query["on_conflict"] = on_conflict

        return self._request(
            "POST",
            resource,
            query=query,
            body=rows,
            prefer=",".join(prefer_bits),
        )

    def update_rows(
        self,
        resource: str,
        values: dict[str, Any],
        *,
        query: dict[str, Any],
        returning: str = "representation",
    ) -> Any:
        return self._request(
            "PATCH",
            resource,
            query=query,
            body=values,
            prefer=f"return={returning}",
        )
