"""Tests for ``mock_response_delay.for_requests_mock``."""

from __future__ import annotations

import time
from collections.abc import Callable
from unittest import mock

import pytest
import requests
import requests_mock

from mock_response_delay.for_requests_mock import (
    delayed_requests_mock_callback,
)

_URL = "https://example.com/slow"


def _hello(
    request: requests_mock.Request,
    context: requests_mock.Context,
) -> str:
    """Answer any request with a greeting."""
    del request, context
    return "Hello"


def _requests_mock(
    *,
    delay_seconds: float,
    sleep_fn: Callable[[float], None],
) -> requests_mock.Mocker:
    """A mock which answers ``_URL`` after a delay."""
    requests_mocker = requests_mock.Mocker()
    _ = requests_mocker.get(
        url=_URL,
        text=delayed_requests_mock_callback(
            callback=_hello,
            delay_seconds=delay_seconds,
            sleep_fn=sleep_fn,
        ),
    )
    return requests_mocker


class TestDelayedRequestsMockCallback:
    """Tests for ``delayed_requests_mock_callback``."""

    @staticmethod
    def test_no_timeout() -> None:
        """A request with no timeout waits for the delay."""
        waits: list[float] = []
        with _requests_mock(delay_seconds=5.0, sleep_fn=waits.append):
            # Omitting the timeout is the behavior under test.
            # pylint: disable-next=missing-timeout
            response = requests.get(url=_URL)  # noqa: S113

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_none_timeout() -> None:
        """An explicit ``None`` timeout waits for the delay."""
        waits: list[float] = []
        with _requests_mock(delay_seconds=5.0, sleep_fn=waits.append):
            response = requests.get(url=_URL, timeout=None)  # noqa: S113

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_timeout_longer_than_delay() -> None:
        """A request whose timeout outlasts the delay gets the
        response.
        """
        waits: list[float] = []
        with _requests_mock(delay_seconds=5.0, sleep_fn=waits.append):
            response = requests.get(url=_URL, timeout=10.0)

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_timeout_equal_to_delay() -> None:
        """A request whose timeout equals the delay gets the response."""
        waits: list[float] = []
        with _requests_mock(delay_seconds=5.0, sleep_fn=waits.append):
            response = requests.get(url=_URL, timeout=5.0)

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_timeout_shorter_than_delay() -> None:
        """A request whose timeout is shorter than the delay times out."""
        waits: list[float] = []
        with (
            _requests_mock(delay_seconds=5.0, sleep_fn=waits.append),
            pytest.raises(expected_exception=requests.exceptions.Timeout),
        ):
            _ = requests.get(url=_URL, timeout=1.0)

        assert waits == [1.0]

    @staticmethod
    def test_integer_timeout() -> None:
        """An integer timeout is compared with the delay."""
        waits: list[float] = []
        with (
            _requests_mock(delay_seconds=5.0, sleep_fn=waits.append),
            pytest.raises(expected_exception=requests.exceptions.Timeout),
        ):
            _ = requests.get(url=_URL, timeout=1)

        assert waits == [1.0]

    @staticmethod
    def test_tuple_read_timeout_shorter_than_delay() -> None:
        """Only the read leg of a timeout tuple is compared."""
        waits: list[float] = []
        with (
            _requests_mock(delay_seconds=5.0, sleep_fn=waits.append),
            pytest.raises(expected_exception=requests.exceptions.Timeout),
        ):
            _ = requests.get(url=_URL, timeout=(10.0, 1.0))

        assert waits == [1.0]

    @staticmethod
    def test_tuple_read_timeout_longer_than_delay() -> None:
        """A short connect timeout does not cause a timeout."""
        waits: list[float] = []
        with _requests_mock(delay_seconds=5.0, sleep_fn=waits.append):
            response = requests.get(url=_URL, timeout=(1.0, 10.0))

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_tuple_without_read_timeout() -> None:
        """A tuple with no read timeout waits for the delay."""
        waits: list[float] = []
        with _requests_mock(delay_seconds=5.0, sleep_fn=waits.append):
            response = requests.get(url=_URL, timeout=(1.0, None))

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_callback_not_called_on_timeout() -> None:
        """The wrapped callback is not called when the request times
        out.
        """
        callback = mock.Mock(spec=_hello)
        requests_mocker = requests_mock.Mocker()
        _ = requests_mocker.get(
            url=_URL,
            text=delayed_requests_mock_callback(
                callback=callback,
                delay_seconds=5.0,
                sleep_fn=lambda _: None,
            ),
        )
        with (
            requests_mocker,
            pytest.raises(expected_exception=requests.exceptions.Timeout),
        ):
            _ = requests.get(url=_URL, timeout=1.0)

        callback.assert_not_called()

    @staticmethod
    def test_default_sleep() -> None:
        """By default, the delay is real."""
        delay_seconds = 0.2
        minimum_elapsed_seconds = 0.1
        requests_mocker = requests_mock.Mocker()
        _ = requests_mocker.get(
            url=_URL,
            text=delayed_requests_mock_callback(
                callback=_hello,
                delay_seconds=delay_seconds,
            ),
        )

        with requests_mocker:
            start = time.monotonic()
            _ = requests.get(url=_URL, timeout=1.0)
            elapsed = time.monotonic() - start

        assert elapsed >= minimum_elapsed_seconds
