import socket
from app import desktop


def test_free_port_is_usable():
    port = desktop._free_port()
    assert isinstance(port, int) and 1024 < port < 65536
    # the returned port should be bindable
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", port))
    s.close()


def test_wait_until_up_false_for_closed_port():
    port = desktop._free_port()  # nothing listening
    assert desktop._wait_until_up(port, timeout=0.5) is False


def test_wait_until_up_true_when_listening():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    try:
        assert desktop._wait_until_up(port, timeout=2.0) is True
    finally:
        s.close()
