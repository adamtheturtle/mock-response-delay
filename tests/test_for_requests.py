"""Tests for ``mock_response_delay.for_requests``."""

import time
from collections.abc import Callable
from http import HTTPStatus
from unittest import mock

import pytest
import requests
import responses
from requests import PreparedRequest

from mock_response_delay.for_requests import delayed_responses_callback

_URL = "https://example.com/slow"
_Response = tuple[int, dict[str, str], str]


def _hello(request: PreparedRequest) -> _Response:
    """Answer any request with a greeting."""
    del request
    return (HTTPStatus.OK, {}, "Hello")


def _requests_mock(
    *,
    delay_seconds: float,
    sleep_fn: Callable[[float], None],
) -> responses.RequestsMock:
    """A mock which answers ``_URL`` after a delay."""
    requests_mock = responses.RequestsMock()
    _ = requests_mock.add_callback(
        method="GET",
        url=_URL,
        callback=delayed_responses_callback(
            callback=_hello,
            delay_seconds=delay_seconds,
            sleep_fn=sleep_fn,
        ),
    )
    return requests_mock


class TestDelayedResponsesCallback:
    """Tests for ``delayed_responses_callback``."""

    @staticmethod
    def test_no_timeout() -> None:
        """A request with no timeout waits for an integer delay."""
        waits: list[float] = []
        with _requests_mock(delay_seconds=5, sleep_fn=waits.append):
            # Omitting the timeout is the behavior under test.
            # pylint: disable-next=missing-timeout
            response = requests.get(url=_URL)  # noqa: S113

        assert response.text == "Hello"
        assert waits == [5]

    @staticmethod
    def test_none_timeout() -> None:
        """An explicit ``None`` timeout waits for the delay."""
        waits: list[float] = []
        with _requests_mock(delay_seconds=5.0, sleep_fn=waits.append):
            # A ``None`` timeout is the behavior under test.
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
        """A request whose timeout is shorter than the delay times out
        after waiting for the timeout, not the delay.
        """
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
        """Only the read leg of a ``(connect, read)`` tuple is compared
        with the delay.
        """
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
        requests_mock = responses.RequestsMock()
        _ = requests_mock.add_callback(
            method="GET",
            url=_URL,
            callback=delayed_responses_callback(
                callback=callback,
                delay_seconds=5.0,
                sleep_fn=lambda _: None,
            ),
        )
        with (
            requests_mock,
            pytest.raises(expected_exception=requests.exceptions.Timeout),
        ):
            _ = requests.get(url=_URL, timeout=1.0)

        callback.assert_not_called()

    @staticmethod
    def test_request_not_from_responses() -> None:
        """Reject a request without the attributes added by responses."""
        callback = delayed_responses_callback(
            callback=_hello,
            delay_seconds=5.0,
            sleep_fn=lambda _: None,
        )
        request = requests.Request(method="GET", url=_URL).prepare()

        with pytest.raises(
            expected_exception=TypeError,
            match="request was not prepared by responses",
        ):
            _ = callback(request)

    @staticmethod
    def test_default_sleep() -> None:
        """By default, the delay is real."""
        # Windows timers are coarse, so allow a short sleep to end early.
        delay_seconds = 0.2
        minimum_elapsed_seconds = 0.1
        callback = delayed_responses_callback(
            callback=_hello,
            delay_seconds=delay_seconds,
        )
        requests_mock = responses.RequestsMock()
        _ = requests_mock.add_callback(
            method="GET",
            url=_URL,
            callback=callback,
        )

        with requests_mock:
            start = time.monotonic()
            _ = requests.get(url=_URL, timeout=1.0)
            elapsed = time.monotonic() - start

        assert elapsed >= minimum_elapsed_seconds
