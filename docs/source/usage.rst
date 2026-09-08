Usage
=====

Each function takes the callback or handler which makes the response, and returns one which answers as a server which takes ``delay_seconds`` to respond would.

A request whose read timeout is shorter than the delay waits for the timeout, by calling ``sleep_fn`` with the timeout, and then raises the exception which the client library raises against a real slow server.
The wrapped callback is not called, because a server which has not yet answered has not yet done anything which the client can observe.

Any other request gets the response from the wrapped callback after waiting for the delay, by calling ``sleep_fn`` with the delay.

``requests`` with ``requests-mock``
-----------------------------------

:func:`~mock_response_delay.for_requests_mock.delayed_requests_mock_callback` wraps a ``requests-mock`` response callback.
A request with a read timeout shorter than the delay raises :class:`requests.exceptions.Timeout`:

.. code-block:: python

    """Time out against a slow server."""

    from __future__ import annotations

    import pytest
    import requests
    import requests_mock

    from mock_response_delay.for_requests_mock import (
        delayed_requests_mock_callback,
    )


    def slow_callback(
        request: requests_mock.Request,
        context: requests_mock.Context,
    ) -> str:
        """Answer any request."""
        del request, context
        return "Hello"


    waits: list[float] = []

    with requests_mock.Mocker() as mock:
        _matcher: object = mock.get(
            url="https://example.com/",
            text=delayed_requests_mock_callback(
                callback=slow_callback,
                delay_seconds=5.0,
                sleep_fn=waits.append,
            ),
        )

        with pytest.raises(expected_exception=requests.exceptions.Timeout):
            _response = requests.get(url="https://example.com/", timeout=1.0)

        response = requests.get(url="https://example.com/", timeout=10.0)

    assert response.text == "Hello"
    assert waits == [1.0, 5.0]

``requests-mock`` copies the timeout passed to ``requests`` onto the request object it gives to a callback.
That public ``timeout`` property is where the read timeout is read from.

``requests`` accepts the timeout as one number, which applies to both connecting and reading, or as a ``(connect, read)`` tuple.
A slow server only affects the read leg, so only the read timeout is compared with the delay.
A request with no timeout waits for the whole delay.

``httpx`` with ``respx`` or ``httpx.MockTransport``
---------------------------------------------------

:func:`~mock_response_delay.for_httpx.delayed_httpx_handler` wraps an ``httpx`` handler, which is anything that takes an ``httpx.Request`` and returns an ``httpx.Response``.
Give the result to ``httpx.MockTransport``, or to ``respx`` as a side effect.
A request with a read timeout shorter than the delay raises :class:`httpx.ReadTimeout`:

.. code-block:: python

    """Time out against a slow server."""

    import httpx
    import pytest

    from mock_response_delay.for_httpx import delayed_httpx_handler


    def slow_handler(request: httpx.Request) -> httpx.Response:
        """Answer any request."""
        del request
        return httpx.Response(status_code=200, text="Hello")


    waits: list[float] = []
    transport = httpx.MockTransport(
        handler=delayed_httpx_handler(
            handler=slow_handler,
            delay_seconds=5.0,
            sleep_fn=waits.append,
        ),
    )

    with httpx.Client(transport=transport) as client:
        with pytest.raises(expected_exception=httpx.ReadTimeout):
            _response = client.get(url="https://example.com/", timeout=1.0)

        response = client.get(url="https://example.com/", timeout=10.0)

    assert response.text == "Hello"
    assert waits == [1.0, 5.0]

With ``respx``, give the wrapped handler as the side effect of a route:

.. code-block:: python

    """Time out against a slow server which ``respx`` mocks."""

    import httpx
    import pytest
    import respx

    from mock_response_delay.for_httpx import delayed_httpx_handler


    def slow_handler(request: httpx.Request) -> httpx.Response:
        """Answer any request."""
        del request
        return httpx.Response(status_code=200, text="Hello")


    waits: list[float] = []

    with respx.mock() as router:
        _route = router.get(url="https://example.com/").mock(
            side_effect=delayed_httpx_handler(
                handler=slow_handler,
                delay_seconds=5.0,
                sleep_fn=waits.append,
            ),
        )

        with pytest.raises(expected_exception=httpx.ReadTimeout):
            _response = httpx.get(url="https://example.com/", timeout=1.0)

    assert waits == [1.0]

An ``httpx`` client puts the timeout it will apply into the ``timeout`` extension of each request, with one entry per leg.
That is where the read timeout is read from, so a request which was not made through a client is treated as having no timeout.
The same handler serves ``httpx.AsyncClient``.

``httpx2``
----------

``httpx2`` has its own request, response and exception classes, so :func:`~mock_response_delay.for_httpx2.delayed_httpx2_handler` is a separate function which works in the same way, with ``httpx2.MockTransport``:

.. code-block:: python

    """Time out against a slow server."""

    import httpx2
    import pytest

    from mock_response_delay.for_httpx2 import delayed_httpx2_handler


    def slow_handler(request: httpx2.Request) -> httpx2.Response:
        """Answer any request."""
        del request
        return httpx2.Response(status_code=200, text="Hello")


    waits: list[float] = []
    transport = httpx2.MockTransport(
        handler=delayed_httpx2_handler(
            handler=slow_handler,
            delay_seconds=5.0,
            sleep_fn=waits.append,
        ),
    )

    with httpx2.Client(transport=transport) as client:
        with pytest.raises(expected_exception=httpx2.ReadTimeout):
            _response = client.get(url="https://example.com/", timeout=1.0)

        response = client.get(url="https://example.com/", timeout=10.0)

    assert response.text == "Hello"
    assert waits == [1.0, 5.0]

Controlling the clock
---------------------

``sleep_fn`` defaults to :func:`time.sleep`, so by default the delay is real.
The examples above record the waits instead, which keeps the test instant.
Something which advances a fake clock, such as a ``freezegun`` tick, works the same way.
