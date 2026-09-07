"""Tests for ``mock_response_delay.for_httpx``."""

import asyncio
from collections.abc import Callable
from http import HTTPStatus
from unittest import mock

import httpx
import pytest
import respx

from mock_response_delay.for_httpx import delayed_httpx_handler

_URL = "https://example.com/slow"


def _hello(request: httpx.Request) -> httpx.Response:
    """Answer any request with a greeting."""
    del request
    return httpx.Response(status_code=HTTPStatus.OK, text="Hello")


def _transport(
    *,
    delay_seconds: float,
    sleep_fn: Callable[[float], None],
) -> httpx.MockTransport:
    """A transport which answers after a delay."""
    return httpx.MockTransport(
        handler=delayed_httpx_handler(
            handler=_hello,
            delay_seconds=delay_seconds,
            sleep_fn=sleep_fn,
        ),
    )


class TestDelayedHttpxHandler:
    """Tests for ``delayed_httpx_handler``."""

    @staticmethod
    def test_no_timeout() -> None:
        """A request with no timeout waits for the delay."""
        waits: list[float] = []
        transport = _transport(delay_seconds=5.0, sleep_fn=waits.append)
        with httpx.Client(transport=transport) as client:
            response = client.get(url=_URL, timeout=None)

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_timeout_longer_than_delay() -> None:
        """A request whose timeout outlasts the delay gets the
        response.
        """
        waits: list[float] = []
        transport = _transport(delay_seconds=5.0, sleep_fn=waits.append)
        with httpx.Client(transport=transport) as client:
            response = client.get(url=_URL, timeout=10.0)

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_timeout_shorter_than_delay() -> None:
        """A request whose timeout is shorter than the delay times out
        after waiting for the timeout, not the delay.
        """
        waits: list[float] = []
        transport = _transport(delay_seconds=5.0, sleep_fn=waits.append)
        with (
            httpx.Client(transport=transport) as client,
            pytest.raises(expected_exception=httpx.ReadTimeout),
        ):
            client.get(url=_URL, timeout=1.0)

        assert waits == [1.0]

    @staticmethod
    def test_only_read_timeout_matters() -> None:
        """Only the read timeout is compared with the delay."""
        waits: list[float] = []
        transport = _transport(delay_seconds=5.0, sleep_fn=waits.append)
        timeout = httpx.Timeout(timeout=1.0, read=10.0)
        with httpx.Client(transport=transport) as client:
            response = client.get(url=_URL, timeout=timeout)

        assert response.text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_handler_not_called_on_timeout() -> None:
        """The wrapped handler is not called when the request times
        out.
        """
        handler = mock.Mock(spec=_hello)
        transport = httpx.MockTransport(
            handler=delayed_httpx_handler(
                handler=handler,
                delay_seconds=5.0,
                sleep_fn=lambda _: None,
            ),
        )
        with (
            httpx.Client(transport=transport) as client,
            pytest.raises(expected_exception=httpx.ReadTimeout),
        ):
            client.get(url=_URL, timeout=1.0)

        handler.assert_not_called()

    @staticmethod
    def test_request_not_from_client() -> None:
        """A request which a client did not make has no timeout."""
        waits: list[float] = []
        handler = delayed_httpx_handler(
            handler=_hello,
            delay_seconds=5.0,
            sleep_fn=waits.append,
        )
        request = httpx.Request(method="GET", url=_URL)

        assert handler(request).text == "Hello"
        assert waits == [5.0]

    @staticmethod
    def test_async_client() -> None:
        """The handler serves an asynchronous client."""
        waits: list[float] = []
        transport = _transport(delay_seconds=5.0, sleep_fn=waits.append)

        async def get() -> None:
            """Make a request which times out."""
            async with httpx.AsyncClient(transport=transport) as client:
                await client.get(url=_URL, timeout=1.0)

        with pytest.raises(expected_exception=httpx.ReadTimeout):
            asyncio.run(main=get())

        assert waits == [1.0]

    @staticmethod
    def test_respx_side_effect() -> None:
        """The handler is usable as a ``respx`` side effect."""
        waits: list[float] = []
        with respx.mock() as router:
            router.get(url=_URL).mock(
                side_effect=delayed_httpx_handler(
                    handler=_hello,
                    delay_seconds=5.0,
                    sleep_fn=waits.append,
                ),
            )
            with pytest.raises(expected_exception=httpx.ReadTimeout):
                httpx.get(url=_URL, timeout=1.0)
            response = httpx.get(url=_URL, timeout=10.0)

        assert response.text == "Hello"
        assert waits == [1.0, 5.0]
