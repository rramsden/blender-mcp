# tests for blender_rpc_tcp server
import json
import threading
import time
import socket

import pytest

# Import the server module (it will not start automatically)
from ..blender_rpc_tcp import start_tcp_server, stop_tcp_server, HOST, PORT


@pytest.fixture(scope="module")
def run_server():
    """Start the TCP server in a background thread for the duration of tests."""
    # Launch server thread (daemon so it exits when process ends)
    t = threading.Thread(target=start_tcp_server, daemon=True)
    t.start()
    # Give it a moment to bind
    time.sleep(0.5)
    yield
    # Stop the server explicitly
    stop_tcp_server()


def test_describe(run_server):
    """Test the describe method via TCP connection."""
    # Connect to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((HOST, PORT))

        # Send describe request
        req = {"jsonrpc": "2.0", "id": 1, "method": "describe", "params": {}}
        sock.send((json.dumps(req) + "\n").encode("utf-8"))

        # Receive response
        response = ""
        while True:
            chunk = sock.recv(1024).decode("utf-8")
            if not chunk:
                break
            response += chunk

            # If we have a complete line, we're done
            if "\n" in response:
                response = response.strip()
                break

        sock.close()

        resp = json.loads(response)
        assert resp["id"] == 1
        assert "methods" in resp["result"]
        # ensure execute method is advertised
        names = [m["name"] for m in resp["result"]["methods"]]
        assert "execute" in names
    except Exception as e:
        sock.close()
        raise e


def test_execute_simple(run_server):
    """Test the execute method via TCP connection."""
    # Connect to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((HOST, PORT))

        # Send execute request
        code = "result = 5 + 3"
        req = {"jsonrpc": "2.0", "id": 2, "method": "execute", "params": {"code": code}}
        sock.send((json.dumps(req) + "\n").encode("utf-8"))

        # Receive response
        response = ""
        while True:
            chunk = sock.recv(1024).decode("utf-8")
            if not chunk:
                break
            response += chunk

            # If we have a complete line, we're done
            if "\n" in response:
                response = response.strip()
                break

        sock.close()

        resp = json.loads(response)
        assert resp["id"] == 2
        assert resp["result"] == 8
    except Exception as e:
        sock.close()
        raise e


def test_server_shutdown(run_server):
    """Test that the server can be shut down properly."""
    # First verify server is running by making a request
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((HOST, PORT))

        # Send describe request
        req = {"jsonrpc": "2.0", "id": 3, "method": "describe", "params": {}}
        sock.send((json.dumps(req) + "\n").encode("utf-8"))

        # Receive response
        response = ""
        while True:
            chunk = sock.recv(1024).decode("utf-8")
            if not chunk:
                break
            response += chunk

            # If we have a complete line, we're done
            if "\n" in response:
                response = response.strip()
                break

        sock.close()

        resp = json.loads(response)
        assert resp["id"] == 3

        # Test that stop_tcp_server doesn't raise an exception
        # (This test verifies the shutdown function exists and doesn't crash)
        try:
            stop_tcp_server()
            # If we get here without exception, the test passes
            assert True
        except Exception:
            pytest.fail("stop_tcp_server() raised an exception")
    except Exception as e:
        sock.close()
        raise e
