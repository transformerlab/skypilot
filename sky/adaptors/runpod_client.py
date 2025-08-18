"""Thread-safe RunPod GraphQL API client used by SkyPilot.

This adaptor replaces the third-party runpod SDK to avoid import-time
configuration and provide per-request isolation.
"""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
import contextlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests import Response

API_URL = "https://api.runpod.io/graphql"


class QueryError(Exception):
    """Raised when the GraphQL API returns errors."""


class InvalidCredentialsError(Exception):
    """Raised when API credentials are invalid or missing."""


def _load_api_key_from_env_or_file() -> Optional[str]:
    """Resolve API key from env or config files.

    Resolution order:
    1) RUNPOD_API_KEY (explicit)
    2) RUNPOD_CONFIG_PATH (path to a config.toml with api_key)
    3) RUNPOD_CONFIG_DIR (directory containing config.toml)
    4) ~/.runpod/config.toml
    """
    # 1) Explicit env var always wins
    api_key = os.environ.get("RUNPOD_API_KEY")
    if api_key:
        return api_key

    # 2) Config path provided explicitly
    cfg_path_env = os.environ.get("RUNPOD_CONFIG_PATH")
    if cfg_path_env:
        cfg_path = Path(cfg_path_env).expanduser()
        if cfg_path.exists():
            try:
                content = cfg_path.read_text(encoding="utf-8")
                m = re.search(r"api_key\s*=\s*\"([^\"]+)\"", content)
                if m:
                    return m.group(1)
            except Exception:
                pass

    # 3) Config dir provided; look for config.toml inside
    cfg_dir_env = os.environ.get("RUNPOD_CONFIG_DIR")
    if cfg_dir_env:
        cfg_path = Path(cfg_dir_env).expanduser() / "config.toml"
        if cfg_path.exists():
            try:
                content = cfg_path.read_text(encoding="utf-8")
                m = re.search(r"api_key\s*=\s*\"([^\"]+)\"", content)
                if m:
                    return m.group(1)
            except Exception:
                pass

    # 4) Default location under the user's home directory
    config_path = Path(os.path.expanduser("~/.runpod/config.toml"))
    if not config_path.exists():
        return None
    try:
        content = config_path.read_text(encoding="utf-8")
        # Very simple parse: find api_key = "..." under any section
        m = re.search(r"api_key\s*=\s*\"([^\"]+)\"", content)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


_LOCAL = threading.local()


def _get_thread_api_key() -> Optional[str]:
    return getattr(_LOCAL, "api_key", None)


@contextlib.contextmanager
def api_key_context(api_key: Optional[str]):
    """Temporarily set an API key for the current thread.

    This key will be used by get_client() within the same thread, avoiding
    reliance on process-global environment variables.
    """
    if api_key is None:
        # No-op context
        yield
        return
    prev = getattr(_LOCAL, "api_key", None)
    _LOCAL.api_key = api_key
    try:
        yield
    finally:
        if prev is None and hasattr(_LOCAL, "api_key"):
            delattr(_LOCAL, "api_key")
        else:
            _LOCAL.api_key = prev


@lru_cache(maxsize=32)
def _client_for_key(api_key: str) -> "RunpodApiClient":
    return RunpodApiClient(api_key)


def get_client(api_key: Optional[str] = None) -> "RunpodApiClient":
    """Get a RunPod client, optionally injecting an explicit API key.

    If ``api_key`` is provided, a client bound to that key is returned.
    Otherwise, credentials are resolved from env/config files.
    """
    resolved = api_key or _get_thread_api_key() or _load_api_key_from_env_or_file()
    if not resolved:
        raise InvalidCredentialsError(
            "RUNPOD_API_KEY not set and ~/.runpod/config.toml missing.")
    return _client_for_key(resolved)


def run_graphql_query(query: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Execute a raw GraphQL query and return parsed JSON.

    Accepts an optional ``api_key`` to perform the request with explicit
    credentials instead of env/config discovery.
    """
    resp = get_client(api_key=api_key)._make_request({"query": query})
    return resp.json()


@dataclass
class RunpodApiClient:
    api_key: str
    _session: requests.Session | None = None
    _lock: threading.RLock = threading.RLock()

    def _get_session(self) -> requests.Session:
        with self._lock:
            if self._session is None:
                self._session = requests.Session()
        return self._session

    def validate_api_key(self) -> bool:
        try:
            # A lightweight query to validate credentials.
            self.get_user_details()
        except InvalidCredentialsError:
            return False
        return True

    def get_user_details(self) -> Dict[str, Any]:
        resp = self._make_request({
            "query": """
            query myself { myself { id email } }
            """
        })
        return resp.json()

    def get_network_volume(self, volume_id: str) -> Optional[Dict[str, Any]]:
        response = self._make_request({
            "query": """
            query getMyVolumes {
                myself {
                    networkVolumes { id name size dataCenter { id name } }
                }
            }
            """
        })
        network_volumes = response.json()["data"]["myself"][
            "networkVolumes"]
        for vol in network_volumes:
            if vol["id"] == volume_id:
                return vol
        return None

    def create_pod(
        self,
        name: str,
        image_name: str,
        gpu_type_id: Optional[str] = None,
        cloud_type: Optional[str] = None,
        support_public_ip: bool = True,
        start_ssh: bool = True,
        data_center_id: Optional[str] = None,
        country_code: Optional[str] = None,
        gpu_count: int = 1,
        volume_in_gb: int = 0,
        container_disk_in_gb: Optional[int] = None,
        min_vcpu_count: Optional[int] = None,
        min_memory_in_gb: Optional[int] = None,
        docker_args: str = "",
        ports: Optional[str] = None,
        volume_mount_path: Optional[str] = None,
        env: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        network_volume_id: Optional[str] = None,
        allowed_cuda_versions: Optional[List[str]] = None,
        bid_per_gpu: Optional[float] = None,
        instance_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        mutation = _generate_pod_deployment_mutation(
            name=name,
            image_name=image_name,
            gpu_type_id=gpu_type_id,
            cloud_type=cloud_type,
            support_public_ip=support_public_ip,
            start_ssh=start_ssh,
            data_center_id=data_center_id,
            country_code=country_code,
            gpu_count=gpu_count,
            volume_in_gb=volume_in_gb,
            container_disk_in_gb=container_disk_in_gb,
            min_vcpu_count=min_vcpu_count,
            min_memory_in_gb=min_memory_in_gb,
            docker_args=docker_args,
            ports=ports,
            volume_mount_path=volume_mount_path,
            env=env,
            template_id=template_id,
            network_volume_id=network_volume_id,
            allowed_cuda_versions=allowed_cuda_versions,
            bid_per_gpu=bid_per_gpu,
            instance_id=instance_id,
        )
        resp = self._make_request({"query": mutation})
        data = resp.json()["data"]
        return (data.get("podRentInterruptable")
                if bid_per_gpu is not None else
                data.get("podFindAndDeployOnDemand"))

    def terminate_pod(self, pod_id: str) -> Dict[str, Any]:
        resp = self._make_request({"query": _generate_pod_terminate_mutation(pod_id)})
        return resp.json()["data"]

    def add_container_registry_auth(self, name: str, username: str,
                                    password: str) -> str:
        resp = self._make_request({
            "query": f"""
            mutation {{
                saveRegistryAuth(input: {{ name: \"{name}\", username: \"{username}\", password: \"{password}\" }}) {{ id }}
            }}
            """
        })
        return resp.json()["data"]["saveRegistryAuth"]["id"]

    def delete_container_registry_auth(self, auth_id: str) -> None:
        self._make_request({
            "query": f"""
            mutation {{ deleteRegistryAuth(registryAuthId: \"{auth_id}\") }}
            """
        })

    def create_template(self,
                        name: str,
                        image_name: Optional[str],
                        registry_auth_id: str) -> str:
        # Based on runpod SDK behavior; image_name can be None to use auth only.
        image_field = (f"imageName: \"{image_name}\"," if image_name else "")
        resp = self._make_request({
            "query": f"""
            mutation {{
                createTemplate(input: {{ name: \"{name}\", {image_field} containerRegistryAuthId: \"{registry_auth_id}\" }}) {{ id }}
            }}
            """
        })
        return resp.json()["data"]["createTemplate"]["id"]

    def _make_request(self, data: Any = None) -> Response:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            response = self._get_session().request(
                method="POST",
                url=API_URL,
                json=data,
                headers=headers,
                timeout=120,
            )
            response.raise_for_status()
            j = response.json()
            if isinstance(j, dict) and "errors" in j:
                # Normalize a QueryError similar to runpod SDK
                # Preserve message if available
                msg = j["errors"][0].get("message", "GraphQL query error")
                # Some callers rely on catching QueryError
                raise QueryError(msg)
            return response
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (
                    requests.codes.forbidden, requests.codes.unauthorized):
                raise InvalidCredentialsError(e.response.text)
            raise

    def wait_for_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        start = time.time()
        wait_for_instance_interval = 5
        # Wait up to 20 minutes for image pull + start
        while time.time() - start < 20 * 60:
            query = _generate_pod_query(instance_id)
            pod = self._make_request({"query": query}).json()["data"]["pod"]
            if pod.get("runtime") is not None:
                return pod
            time.sleep(wait_for_instance_interval)
        return None


def _generate_pod_query(pod_id: str) -> str:
    return f"""
    query pod {{
        pod(input: {{podId: \"{pod_id}\"}}) {{ id runtime {{ ports {{ ip isIpPublic privatePort publicPort type }} }} machine {{ gpuDisplayName }} }}
    }}
    """


def _generate_pod_terminate_mutation(pod_id: str) -> str:
    return f"""
    mutation {{ podTerminate(input: {{ podId: \"{pod_id}\" }}) }}
    """


def _generate_pod_deployment_mutation(
    name: str,
    image_name: str,
    gpu_type_id: Optional[str] = None,
    cloud_type: Optional[str] = None,
    support_public_ip: bool = True,
    start_ssh: bool = True,
    data_center_id: Optional[str] = None,
    country_code: Optional[str] = None,
    gpu_count: Optional[int] = None,
    volume_in_gb: Optional[int] = None,
    container_disk_in_gb: Optional[int] = None,
    min_vcpu_count: Optional[int] = None,
    min_memory_in_gb: Optional[int] = None,
    docker_args: Optional[str] = None,
    ports: Optional[str] = None,
    volume_mount_path: Optional[str] = None,
    env: Optional[Dict[str, Any]] = None,
    template_id: Optional[str] = None,
    network_volume_id: Optional[str] = None,
    allowed_cuda_versions: Optional[List[str]] = None,
    bid_per_gpu: Optional[float] = None,
    instance_id: Optional[str] = None,
) -> str:
    fields: List[str] = []
    # Required
    fields.append(f'name: "{name}"')
    fields.append(f'imageName: "{image_name}"')
    # CPU instance uses instanceId, GPU uses gpuTypeId + others
    if instance_id is not None:
        fields.append(f'instanceId: "{instance_id}"')
    if gpu_type_id is not None:
        fields.append(f'gpuTypeId: "{gpu_type_id}"')
    if cloud_type is not None:
        fields.append(f"cloudType: {cloud_type}")
    if start_ssh:
        fields.append("startSsh: true")
    fields.append("supportPublicIp: true" if support_public_ip else "supportPublicIp: false")

    # Optional
    if bid_per_gpu is not None:
        fields.append(f"bidPerGpu: {bid_per_gpu}")
    if data_center_id is not None:
        fields.append(f'dataCenterId: "{data_center_id}"')
    if country_code is not None:
        fields.append(f'countryCode: "{country_code}"')
    if gpu_count is not None:
        fields.append(f"gpuCount: {gpu_count}")
    if volume_in_gb is not None:
        fields.append(f"volumeInGb: {volume_in_gb}")
    if container_disk_in_gb is not None:
        fields.append(f"containerDiskInGb: {container_disk_in_gb}")
    if min_vcpu_count is not None:
        fields.append(f"minVcpuCount: {min_vcpu_count}")
    if min_memory_in_gb is not None:
        fields.append(f"minMemoryInGb: {min_memory_in_gb}")
    if docker_args is not None:
        fields.append(f'dockerArgs: "{docker_args}"')
    if ports is not None:
        fields.append(f'ports: "{ports.replace(" ", "")}"')
    if volume_mount_path is not None:
        fields.append(f'volumeMountPath: "{volume_mount_path}"')
    if env is not None:
        env_string = ", ".join([f'{{ key: "{k}", value: "{v}" }}' for k, v in env.items()])
        fields.append(f"env: [{env_string}]")
    if template_id is not None:
        fields.append(f'templateId: "{template_id}"')
    if network_volume_id is not None:
        fields.append(f'networkVolumeId: "{network_volume_id}"')
    if allowed_cuda_versions is not None:
        allowed = ", ".join([f'"{v}"' for v in allowed_cuda_versions])
        fields.append(f"allowedCudaVersions: [{allowed}]")

    input_string = ", ".join(fields)
    pod_deploy = ("podFindAndDeployOnDemand" if bid_per_gpu is None else
                  "podRentInterruptable")
    return f"""
        mutation {{
          {pod_deploy}(input: {{ {input_string} }}) {{ id lastStatusChange imageName machine {{ podHostId }} }}
        }}
        """
