"""
Pytest configuration for DocMind test suite.
Enforces offline test isolation by preventing live TCP connections to llama-server ports (8080, 8081, 8082).
"""
import socket
import pytest

FORBIDDEN_PORTS = {8080, 8081, 8082}


@pytest.fixture(autouse=True)
def guard_llama_server_sockets(monkeypatch):
    """
    Prevents any test from accidentally connecting to live llama-server instances on ports 8080, 8081, 8082.
    Ensures tests remain 100% isolated, deterministic, and offline.
    """
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def guarded_connect(sock_self, address):
        if isinstance(address, tuple) and len(address) >= 2:
            host, port = address[0], address[1]
            if port in FORBIDDEN_PORTS:
                raise RuntimeError(
                    f"Test isolation violation: unmocked live TCP connection attempt to {host}:{port}. "
                    "Ensure llama_client or network calls are properly mocked in test suites."
                )
        return original_connect(sock_self, address)

    def guarded_connect_ex(sock_self, address):
        if isinstance(address, tuple) and len(address) >= 2:
            host, port = address[0], address[1]
            if port in FORBIDDEN_PORTS:
                raise RuntimeError(
                    f"Test isolation violation: unmocked live TCP connection attempt to {host}:{port}. "
                    "Ensure llama_client or network calls are properly mocked in test suites."
                )
        return original_connect_ex(sock_self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
