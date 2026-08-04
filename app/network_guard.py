from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
from dataclasses import dataclass


class NetworkGuardError(RuntimeError):
    """Raised when offline verification cannot be completed."""


@dataclass(frozen=True)
class NetworkAdapter:
    name: str
    description: str
    status: str
    interface_index: int | None
    hardware_interface: bool
    physical_medium: str

    @property
    def is_up(self) -> bool:
        return self.status.strip().lower() == "up"

    @property
    def searchable_name(self) -> str:
        return f"{self.name} {self.description} {self.physical_medium}".lower()

    @property
    def is_virtual(self) -> bool:
        markers = (
            "tailscale",
            "wireguard",
            "vpn",
            "tunnel",
            "tap-",
            "tap ",
            "wintun",
            "zerotier",
            "hyper-v",
            "vmware",
            "virtualbox",
            "loopback",
        )
        return (not self.hardware_interface) or any(
            marker in self.searchable_name for marker in markers
        )

    @property
    def is_wifi(self) -> bool:
        markers = ("wi-fi", "wifi", "wireless", "802.11", "native 802.11")
        return self.hardware_interface and any(
            marker in self.searchable_name for marker in markers
        )

    @property
    def is_ethernet(self) -> bool:
        return self.hardware_interface and not self.is_wifi and not self.is_virtual


@dataclass(frozen=True)
class DefaultRoute:
    interface_index: int | None
    destination_prefix: str
    next_hop: str
    address_family: str


@dataclass(frozen=True)
class OfflineVerification:
    adapters: tuple[NetworkAdapter, ...]
    default_routes: tuple[DefaultRoute, ...]
    reachable_endpoints: tuple[str, ...]
    error: str | None = None

    @property
    def active_wifi(self) -> tuple[NetworkAdapter, ...]:
        return tuple(
            adapter
            for adapter in self.adapters
            if adapter.is_up and adapter.is_wifi
        )

    @property
    def active_ethernet(self) -> tuple[NetworkAdapter, ...]:
        return tuple(
            adapter
            for adapter in self.adapters
            if adapter.is_up and adapter.is_ethernet
        )

    @property
    def active_virtual(self) -> tuple[NetworkAdapter, ...]:
        return tuple(
            adapter
            for adapter in self.adapters
            if adapter.is_up and adapter.is_virtual
        )

    @property
    def public_reachable(self) -> bool:
        return bool(self.reachable_endpoints)

    @property
    def physical_links_clear(self) -> bool:
        return not self.active_wifi and not self.active_ethernet

    @property
    def verified_offline(self) -> bool:
        return (
            self.error is None
            and self.physical_links_clear
            and not self.public_reachable
        )


def _powershell_executable() -> str:
    return "powershell.exe" if os.name == "nt" else "powershell"


def _encoded_command(script: str) -> list[str]:
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [
        _powershell_executable(),
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        encoded,
    ]


def _run_powershell(script: str, timeout: int = 20) -> str:
    try:
        result = subprocess.run(
            _encoded_command(script),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0
            ),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NetworkGuardError(
            f"PowerShell could not be executed: {exc}"
        ) from exc

    if result.returncode != 0:
        detail = (
            result.stderr
            or result.stdout
            or "Unknown PowerShell error"
        ).strip()
        raise NetworkGuardError(detail)

    return result.stdout.strip()


def _read_windows_network_state() -> tuple[
    tuple[NetworkAdapter, ...],
    tuple[DefaultRoute, ...],
]:
    if os.name != "nt":
        raise NetworkGuardError(
            "Offline verification is supported only on Windows."
        )

    script = r"""
$ErrorActionPreference = 'Stop'

$adapters = Get-NetAdapter |
    Where-Object {
        $_.Name -notmatch 'Loopback' -and
        $_.InterfaceDescription -notmatch 'Loopback'
    } |
    Select-Object `
        Name,
        InterfaceDescription,
        Status,
        ifIndex,
        HardwareInterface,
        NdisPhysicalMedium

$routes = Get-NetRoute |
    Where-Object {
        $_.DestinationPrefix -eq '0.0.0.0/0' -or
        $_.DestinationPrefix -eq '::/0'
    } |
    Select-Object `
        ifIndex,
        DestinationPrefix,
        NextHop,
        AddressFamily

[PSCustomObject]@{
    Adapters = @($adapters)
    Routes = @($routes)
} | ConvertTo-Json -Depth 5 -Compress
"""

    raw = _run_powershell(script)
    parsed = json.loads(raw)

    adapters_raw = parsed.get("Adapters") or []
    routes_raw = parsed.get("Routes") or []

    if isinstance(adapters_raw, dict):
        adapters_raw = [adapters_raw]
    if isinstance(routes_raw, dict):
        routes_raw = [routes_raw]

    adapters = tuple(
        NetworkAdapter(
            name=str(item.get("Name", "")),
            description=str(item.get("InterfaceDescription", "")),
            status=str(item.get("Status", "")),
            interface_index=(
                int(item["ifIndex"])
                if item.get("ifIndex") is not None
                else None
            ),
            hardware_interface=bool(item.get("HardwareInterface", False)),
            physical_medium=str(item.get("NdisPhysicalMedium", "")),
        )
        for item in adapters_raw
    )

    routes = tuple(
        DefaultRoute(
            interface_index=(
                int(item["ifIndex"])
                if item.get("ifIndex") is not None
                else None
            ),
            destination_prefix=str(item.get("DestinationPrefix", "")),
            next_hop=str(item.get("NextHop", "")),
            address_family=str(item.get("AddressFamily", "")),
        )
        for item in routes_raw
    )

    return adapters, routes


def _check_public_reachability(
    *,
    timeout: float = 0.45,
) -> tuple[str, ...]:
    # Direct IP tests deliberately avoid DNS. No secret has been displayed
    # when this function is called.
    endpoints = (
        ("1.1.1.1", 443),
        ("8.8.8.8", 443),
        ("9.9.9.9", 443),
    )
    reachable: list[str] = []

    for host, port in endpoints:
        try:
            with socket.create_connection(
                (host, port),
                timeout=timeout,
            ):
                reachable.append(f"{host}:{port}")
        except OSError:
            continue

    return tuple(reachable)


def verify_offline_environment() -> OfflineVerification:
    try:
        adapters, routes = _read_windows_network_state()
        reachable = _check_public_reachability()
        return OfflineVerification(
            adapters=adapters,
            default_routes=routes,
            reachable_endpoints=reachable,
        )
    except (
        NetworkGuardError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:
        return OfflineVerification(
            adapters=(),
            default_routes=(),
            reachable_endpoints=(),
            error=str(exc),
        )


@dataclass(frozen=True)
class LocalNetworkState:
    """Fast local-only state for the global UI badge."""

    online: bool
    active_physical_adapters: tuple[str, ...]
    error: str | None = None


def get_local_network_state() -> LocalNetworkState:
    """
    Read Windows adapter/link state without contacting any public endpoint.

    Virtual adapters such as Tailscale are informational and do not make the
    global badge report ONLINE by themselves.
    """
    try:
        adapters, _routes = _read_windows_network_state()
        active_physical = tuple(
            adapter.name
            for adapter in adapters
            if adapter.is_up and (adapter.is_wifi or adapter.is_ethernet)
        )
        return LocalNetworkState(
            online=bool(active_physical),
            active_physical_adapters=active_physical,
        )
    except (
        NetworkGuardError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:
        return LocalNetworkState(
            online=False,
            active_physical_adapters=(),
            error=str(exc),
        )
