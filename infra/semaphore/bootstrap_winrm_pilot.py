#!/usr/bin/env python3
"""Bootstrap a Semaphore project for the WinRM pilot."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct
import sys
import time
from pathlib import Path
from typing import Any

import requests


def env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value or ""


def generate_totp(secret: str, step: int = 30, digits: int = 6) -> str:
    key = base64.b32decode(secret, casefold=True)
    counter = struct.pack(">Q", int(time.time()) // step)
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % (10**digits):0{digits}d}"


class SemaphoreClient:
    def __init__(self, base_url: str, host_header: str, username: str, password: str, totp_secret: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.default_headers = {"Host": host_header, "Content-Type": "application/json"}
        self.username = username
        self.password = password
        self.totp_secret = totp_secret

    def _request(self, method: str, path: str, *, ok: tuple[int, ...] = (200,), **kwargs: Any) -> requests.Response:
        headers = kwargs.pop("headers", {})
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            headers={**self.default_headers, **headers},
            timeout=30,
            **kwargs,
        )
        if response.status_code not in ok:
            body = response.text[:1000]
            raise RuntimeError(f"{method} {path} failed: {response.status_code} {body}")
        return response

    def login(self) -> None:
        self._request(
            "POST",
            "/auth/login",
            ok=(200, 204),
            json={"auth": self.username, "password": self.password},
        )
        self._request(
            "POST",
            "/auth/verify",
            ok=(200, 204),
            json={"passcode": generate_totp(self.totp_secret)},
        )

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs).json()

    def post(self, path: str, payload: dict[str, Any], *, ok: tuple[int, ...] = (200, 201)) -> Any:
        response = self._request("POST", path, ok=ok, json=payload)
        return response.json() if response.text else None

    def put(self, path: str, payload: dict[str, Any], *, ok: tuple[int, ...] = (200, 204)) -> Any:
        response = self._request("PUT", path, ok=ok, json=payload)
        return response.json() if response.text else None


def load_inventory_hosts(path: Path) -> str:
    lines: list[str] = []
    in_group = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("[sharex_pilot]"):
            in_group = True
            lines.append(line)
            continue
        if in_group and line.startswith("["):
            break
        if in_group:
            lines.append(line)
    return "\n".join(lines) + "\n"


def find_by_name(items: list[dict[str, Any]], field: str, value: str) -> dict[str, Any] | None:
    for item in items:
        if item.get(field) == value:
            return item
    return None


def ensure_project(client: SemaphoreClient, name: str) -> dict[str, Any]:
    projects = client.get("/projects")
    project = find_by_name(projects, "name", name)
    if project:
        return project
    return client.post(
        "/projects",
        {
            "name": name,
            "alert": False,
            "alert_chat": "",
            "max_parallel_tasks": 0,
            "type": "",
            "demo": False,
        },
    )


def ensure_view(client: SemaphoreClient, project_id: int, title: str, position: int = 1) -> dict[str, Any]:
    views = client.get(f"/project/{project_id}/views")
    view = find_by_name(views, "title", title)
    payload = {"title": title, "project_id": project_id, "position": position}
    if view:
        client.put(f"/project/{project_id}/views/{view['id']}", {**payload, "id": view["id"]})
        return {**view, **payload}
    return client.post(f"/project/{project_id}/views", payload)


def ensure_key(
    client: SemaphoreClient,
    project_id: int,
    name: str,
    login: str,
    password: str,
) -> dict[str, Any]:
    keys = client.get(f"/project/{project_id}/keys?sort=name&order=asc")
    key = find_by_name(keys, "name", name)
    payload = {
        "name": name,
        "type": "login_password",
        "project_id": project_id,
        "override_secret": True,
        "login_password": {
            "login": login,
            "password": password,
        },
    }
    if key:
        client.put(f"/project/{project_id}/keys/{key['id']}", {**payload, "id": key["id"]})
        return {**key, **payload}
    return client.post(f"/project/{project_id}/keys", payload)


def ensure_repository(
    client: SemaphoreClient,
    project_id: int,
    name: str,
    git_url: str,
    branch: str,
    key_id: int,
) -> dict[str, Any]:
    repos = client.get(f"/project/{project_id}/repositories?sort=name&order=asc")
    repo = find_by_name(repos, "name", name)
    payload = {
        "name": name,
        "project_id": project_id,
        "git_url": git_url,
        "git_branch": branch,
        "ssh_key_id": key_id,
    }
    if repo:
        client.put(f"/project/{project_id}/repositories/{repo['id']}", {**payload, "id": repo["id"]})
        return {**repo, **payload}
    return client.post(f"/project/{project_id}/repositories", payload)


def ensure_inventory(client: SemaphoreClient, project_id: int, name: str, inventory: str) -> dict[str, Any]:
    inventories = client.get(f"/project/{project_id}/inventory?sort=name&order=asc")
    item = find_by_name(inventories, "name", name)
    payload = {
        "name": name,
        "project_id": project_id,
        "inventory": inventory,
        "type": "static",
    }
    if item:
        client.put(f"/project/{project_id}/inventory/{item['id']}", {**payload, "id": item["id"]})
        return {**item, **payload}
    return client.post(f"/project/{project_id}/inventory", payload)


def ensure_environment(client: SemaphoreClient, project_id: int, name: str, variables: dict[str, Any]) -> dict[str, Any]:
    environments = client.get(f"/project/{project_id}/environment?sort=name&order=asc")
    item = find_by_name(environments, "name", name)
    payload = {
        "name": name,
        "project_id": project_id,
        "password": "",
        "json": json.dumps(variables),
        "env": json.dumps({}),
        "secrets": [],
    }
    if item:
        client.put(f"/project/{project_id}/environment/{item['id']}", {**payload, "id": item["id"]})
        return {**item, **payload}
    return client.post(f"/project/{project_id}/environment", payload)


def ensure_template(
    client: SemaphoreClient,
    project_id: int,
    name: str,
    inventory_id: int,
    repository_id: int,
    environment_id: int,
    view_id: int,
    playbook: str,
    branch: str,
) -> dict[str, Any]:
    templates = client.get(f"/project/{project_id}/templates?sort=name&order=asc")
    template = find_by_name(templates, "name", name)
    payload = {
        "project_id": project_id,
        "inventory_id": inventory_id,
        "repository_id": repository_id,
        "environment_id": environment_id,
        "view_id": view_id,
        "name": name,
        "playbook": playbook,
        "arguments": "[]",
        "description": "Validate WinRM connectivity on pilot hosts",
        "allow_override_args_in_task": False,
        "limit": "",
        "suppress_success_alerts": False,
        "app": "ansible",
        "git_branch": branch,
        "survey_vars": [],
        "type": "",
        "autorun": False,
        "vaults": [],
    }
    if template:
        client.put(f"/project/{project_id}/templates/{template['id']}", {**payload, "id": template["id"]})
        return {**template, **payload}
    return client.post(f"/project/{project_id}/templates", payload)


def run_template(client: SemaphoreClient, project_id: int, template_id: int) -> dict[str, Any]:
    response = client.post(
        f"/project/{project_id}/tasks",
        {"template_id": template_id, "debug": False, "dry_run": False, "diff": False},
    )
    return response


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    inventory_path = Path(env("PILOT_INVENTORY_FILE", str(repo_root / "infra/ansible/inventories/pilot.ini")))
    playbook_path = env("PILOT_PLAYBOOK", "infra/ansible/playbooks/win_ping.yml")

    client = SemaphoreClient(
        base_url=env("SEMAPHORE_API_URL", "http://127.0.0.1/api"),
        host_header=env("SEMAPHORE_HOST_HEADER", "semaphore.homelab.local"),
        username=env("SEMAPHORE_USERNAME", "admin"),
        password=env("SEMAPHORE_PASSWORD", required=True),
        totp_secret=env("SEMAPHORE_TOTP_SECRET", required=True),
    )
    client.login()

    project = ensure_project(client, env("SEMAPHORE_PROJECT_NAME", "screenshot-audit"))
    project_id = project["id"]

    view = ensure_view(client, project_id, env("SEMAPHORE_VIEW_TITLE", "Pilot"), position=1)
    key = ensure_key(
        client,
        project_id,
        env("SEMAPHORE_REPO_KEY_NAME", "GitHub PAT"),
        env("GIT_REPO_USERNAME", required=True),
        env("GIT_REPO_TOKEN", required=True),
    )
    repo = ensure_repository(
        client,
        project_id,
        env("SEMAPHORE_REPOSITORY_NAME", "audit-screenshot"),
        env("GIT_REPO_URL", required=True),
        env("GIT_REPO_BRANCH", "main"),
        key["id"],
    )
    inventory = ensure_inventory(
        client,
        project_id,
        env("SEMAPHORE_INVENTORY_NAME", "sharex-pilot"),
        load_inventory_hosts(inventory_path),
    )
    environment = ensure_environment(
        client,
        project_id,
        env("SEMAPHORE_ENVIRONMENT_NAME", "sharex-pilot-winrm"),
        {
            "ansible_connection": env("WINRM_CONNECTION", "psrp"),
            "ansible_port": int(env("WINRM_PORT", "5985")),
            "ansible_psrp_auth": env("WINRM_PSRP_AUTH", "ntlm"),
            "ansible_psrp_cert_validation": env("WINRM_CERT_VALIDATION", "ignore"),
            "ansible_user": env("WINRM_USERNAME", required=True),
            "ansible_password": env("WINRM_PASSWORD", required=True),
        },
    )
    template = ensure_template(
        client,
        project_id,
        env("SEMAPHORE_TEMPLATE_NAME", "win_ping"),
        inventory["id"],
        repo["id"],
        environment["id"],
        view["id"],
        playbook_path,
        env("GIT_REPO_BRANCH", "main"),
    )

    result = {
        "project_id": project_id,
        "view_id": view["id"],
        "key_id": key["id"],
        "repository_id": repo["id"],
        "inventory_id": inventory["id"],
        "environment_id": environment["id"],
        "template_id": template["id"],
    }

    if env("RUN_TEMPLATE", "0") == "1":
        task = run_template(client, project_id, template["id"])
        result["task_id"] = task["id"]
        result["task_status"] = task["status"]

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
