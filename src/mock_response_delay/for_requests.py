"""Delay ``responses`` callbacks, and raise the ``requests`` timeout."""

import functools
import time
from collections.abc import Callable
from typing import TypedDict

import requests
from beartype import BeartypeConf, beartype
from requests import PreparedRequest

from mock_response_delay._core import respond_after_delay


class _RequestsKeywordArguments(TypedDict, total=False):
    """Keyword arguments attached by ``responses``."""

    timeout: tuple[float | None, float | None] | float | int | None


@beartype
def _read_timeout_seconds(*, request: PreparedRequest) -> float | None:
    """The read timeout which ``requests`` applies to a request.

    Args:
        request: A request which ``responses`` has given to a callback.

    Returns:
        The read timeout in seconds, or ``None`` if the request has no
        timeout.
    """
    # ``responses`` attaches the keyword arguments of the ``requests``
    # call to the prepared request as ``req_kwargs``.  ``requests`` itself
    # does not, so the attribute is not in the ``requests`` type stubs,
    # and a request which was not made through ``responses`` does not
    # have it.
    req_kwargs: _RequestsKeywordArguments = getattr(  # pylint: disable=bad-builtin
        request,
        "req_kwargs",
        _RequestsKeywordArguments(),
    )
    timeout = req_kwargs.get("timeout")
    # ``requests`` accepts the timeout as a single number, which applies
    # to both connecting and reading, or as a ``(connect, read)`` tuple.
    # A slow server only affects the read leg.
    match timeout:
        case (_, int() | float() as read_timeout):
            return float(read_timeout)
        case int() | float():
            return float(timeout)
        case _:
            return None


@beartype(conf=BeartypeConf(is_pep484_tower=True))
def delayed_responses_callback[T](
    callback: Callable[[PreparedRequest], T],
    *,
    delay_seconds: float,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Callable[[PreparedRequest], T]:
    """Make a ``responses`` callback answer as a slow server would.

    Give the result to ``responses.RequestsMock.add_callback`` in place
    of ``callback``.

    A request whose read timeout is shorter than the delay waits for the
    timeout and then raises :class:`requests.exceptions.Timeout`, as it
    would against a real slow server, and ``callback`` is not called.
    Any other request gets the response from ``callback`` after waiting
    for the delay.

    Args:
        callback: The ``responses`` callback which makes the response.
        delay_seconds: How long the simulated server takes to respond.
        sleep_fn: What to call to wait.  It is given the number of
            seconds to wait for.  The default really sleeps.  Give
            something else to record the waits, or to advance a fake
            clock, instead.

    Returns:
        A ``responses`` callback.
    """

    def wrapped(request: PreparedRequest) -> T:
        """Respond to a request after the delay.

        Args:
            request: The request to respond to.

        Returns:
            The response from ``callback``.
        """
        return respond_after_delay(
            read_timeout_seconds=_read_timeout_seconds(request=request),
            delay_seconds=delay_seconds,
            sleep_fn=sleep_fn,
            make_timeout_error=requests.exceptions.Timeout,
            respond=functools.partial(callback, request),
        )

    return wrapped
