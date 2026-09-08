"""Delay ``httpx`` handlers, and raise the ``httpx`` timeout."""

import functools
import time
from collections.abc import Callable, Mapping

import httpx
from beartype import BeartypeConf, beartype

from mock_response_delay._core import respond_after_delay


@beartype
def _read_timeout_seconds(*, request: httpx.Request) -> float | None:
    """The read timeout which ``httpx`` applies to a request.

    Args:
        request: A request which an ``httpx`` client has given to a
            transport.

    Returns:
        The read timeout in seconds, or ``None`` if the request has no
        read timeout.
    """
    # An ``httpx`` client puts the timeout it will apply into the
    # ``timeout`` extension of each request, with one entry per leg.
    # A request which was not made through a client has no extensions.
    timeout_info: Mapping[str, float | None] = request.extensions.get(
        "timeout",
        {},
    )
    # A client given an integer timeout passes it on as an integer.
    read_timeout = timeout_info.get("read")
    return None if read_timeout is None else read_timeout * 1.0


@beartype(conf=BeartypeConf(is_pep484_tower=True))
def delayed_httpx_handler[T](
    handler: Callable[[httpx.Request], T],
    *,
    delay_seconds: float,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Callable[[httpx.Request], T]:
    """Make an ``httpx`` handler answer as a slow server would.

    Give the result to ``httpx.MockTransport`` in place of ``handler``,
    or to ``respx`` as a side effect.

    A request whose read timeout is shorter than the delay waits for the
    timeout and then raises :class:`httpx.ReadTimeout`, as it would
    against a real slow server, and ``handler`` is not called.  Any
    other request gets the response from ``handler`` after waiting for
    the delay.

    Args:
        handler: The handler which makes the response.
        delay_seconds: How long the simulated server takes to respond.
        sleep_fn: What to call to wait.  It is given the number of
            seconds to wait for.  The default really sleeps.  Give
            something else to record the waits, or to advance a fake
            clock, instead.

    Returns:
        An ``httpx`` handler.
    """

    def wrapped(request: httpx.Request) -> T:
        """Respond to a request after the delay.

        Args:
            request: The request to respond to.

        Returns:
            The response from ``handler``.
        """
        return respond_after_delay(
            read_timeout_seconds=_read_timeout_seconds(request=request),
            delay_seconds=delay_seconds,
            sleep_fn=sleep_fn,
            make_timeout_error=functools.partial(
                httpx.ReadTimeout,
                message="Response delay exceeded read timeout",
                request=request,
            ),
            respond=functools.partial(handler, request),
        )

    return wrapped
