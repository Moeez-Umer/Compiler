"""Give every test a hard time limit so a hang fails the test instead of freezing pytest (D-026)."""
import signal

import pytest

TEST_TIMEOUT_SECONDS = 10


class TimeoutExceeded(Exception):
    """Raised when a single test runs longer than TEST_TIMEOUT_SECONDS."""


@pytest.fixture(autouse=True)
def per_test_timeout():
    """Install a SIGALRM handler for the test, cancel it afterwards (no-op on Windows)."""
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def on_alarm(signum, frame):
        raise TimeoutExceeded(f"test exceeded {TEST_TIMEOUT_SECONDS} s")

    old_handler = signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(TEST_TIMEOUT_SECONDS)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
