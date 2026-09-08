|Build Status| |PyPI|

mock-response-delay
===================

.. contents::
   :local:

Simulate a slow server, and the client timeout it causes, in HTTP mocks.

``requests-mock``, ``responses`` and ``respx`` answer requests instantly, so a test of how code handles a slow server, or a timeout, has nothing to exercise.
This package wraps a mock's callback so that it answers as a server which takes a given number of seconds would.
A request whose read timeout is shorter than the delay waits for the timeout and then raises the same exception which the client library raises against a real slow server.
Any other request gets the response after waiting for the delay.

The waiting is done by a function which you can replace, so a test can record the waits, or advance a fake clock, instead of really sleeping.

Installation
------------

Install the extra for the client library which the code under test uses:

.. code-block:: shell

    pip install 'mock-response-delay[requests]'
    pip install 'mock-response-delay[httpx]'
    pip install 'mock-response-delay[httpx2]'

This requires Python |minimum-python-version|\+.

Usage
-----

``requests`` with ``requests-mock``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wrap a response callback before giving it to ``requests-mock``.
A request with a read timeout shorter than the delay raises ``requests.exceptions.Timeout``:

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

``requests`` with ``responses``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wrap a callback before giving it to ``responses``.
A request with a read timeout shorter than the delay raises ``requests.exceptions.Timeout``:

.. code-block:: python

    """Time out against a slow server."""

    import pytest
    import requests
    import responses
    from requests import PreparedRequest

    from mock_response_delay.for_requests import delayed_responses_callback


    def slow_callback(request: PreparedRequest) -> tuple[int, dict[str, str], str]:
        """Answer any request."""
        del request
        return (200, {}, "Hello")


    waits: list[float] = []

    with responses.RequestsMock() as mock:
        _registration = mock.add_callback(
            method="GET",
            url="https://example.com/",
            callback=delayed_responses_callback(
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

``requests`` accepts the timeout as one number, or as a ``(connect, read)`` tuple.
A slow server only affects the read leg, so only the read timeout is compared with the delay.

``httpx`` with ``respx`` or ``httpx.MockTransport``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wrap a handler before giving it to ``httpx.MockTransport``, or to ``respx`` as a side effect.
A request with a read timeout shorter than the delay raises ``httpx.ReadTimeout``:

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

``httpx2``
~~~~~~~~~~

``httpx2`` has its own request, response and exception classes, so it has its own module, which works in the same way with ``httpx2.MockTransport``:

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
~~~~~~~~~~~~~~~~~~~~~

``sleep_fn`` defaults to ``time.sleep``, so by default the delay is real.
The examples above record the waits instead, which keeps the test instant.
Something which advances a fake clock, such as a ``freezegun`` tick, works the same way.

Full documentation
------------------

See the `full documentation <https://adamtheturtle.github.io/mock-response-delay/>`__.

.. |Build Status| image:: https://github.com/adamtheturtle/mock-response-delay/actions/workflows/test.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/mock-response-delay/actions
.. |PyPI| image:: https://badge.fury.io/py/mock-response-delay.svg
    :target: https://badge.fury.io/py/mock-response-delay
.. |minimum-python-version| replace:: 3.12
