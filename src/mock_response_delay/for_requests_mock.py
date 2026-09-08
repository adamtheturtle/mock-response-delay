"""Delay ``requests-mock`` callbacks, and raise the ``requests``
timeout.
"""

import functools
import time
from collections.abc import Callable
from typing import Protocol, runtime_checkable

import requests
from beartype import BeartypeConf, beartype

from mock_response_delay._core import respond_after_delay


@runtime_checkable
class _RequestWithTimeout(Protocol):
    """The part of a ``requests-mock`` request which this module uses."""

    @property
    def timeout(
        self,
    ) -> tuple[float | None, float | None] | float | int | None:
        """The timeout passed to ``requests``."""


@beartype
def _read_timeout_seconds(*, request: _RequestWithTimeout) -> float | None:
    """The read timeout which ``requests`` applies to a request.

    Args:
        request: A request which ``requests-mock`` has given to a callback.

    Returns:
        The read timeout in seconds, or ``None`` if the request has no
        timeout.
    """
    match request.timeout:
        case (_, int() | float() as read_timeout):
            return float(read_timeout)
        case int() | float() as timeout:
            return float(timeout)
        case _:
            return None


@beartype(conf=BeartypeConf(is_pep484_tower=True))
def delayed_requests_mock_callback[
    RequestT: _RequestWithTimeout,
    ContextT,
    T,
](
    callback: Callable[[RequestT, ContextT], T],
    *,
    delay_seconds: float,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Callable[[RequestT, ContextT], T]:
    """Make a ``requests-mock`` callback answer as a slow server would.

    Give the result to ``requests_mock.Mocker.register_uri`` in place of a
    response callback.

    A request whose read timeout is shorter than the delay waits for the
    timeout and then raises :class:`requests.exceptions.Timeout`, as it
    would against a real slow server, and ``callback`` is not called.
    Any other request gets the response from ``callback`` after waiting
    for the delay.

    Args:
        callback: The ``requests-mock`` callback which makes the response.
        delay_seconds: How long the simulated server takes to respond.
        sleep_fn: What to call to wait. It is given the number of seconds
            to wait for. The default really sleeps. Give something else
            to record the waits, or to advance a fake clock, instead.

    Returns:
        A ``requests-mock`` callback.
    """

    def wrapped(request: RequestT, context: ContextT) -> T:
        """Respond to a request after the delay.

        Args:
            request: The request to respond to.
            context: The response context.

        Returns:
            The response from ``callback``.
        """
        return respond_after_delay(
            read_timeout_seconds=_read_timeout_seconds(request=request),
            delay_seconds=delay_seconds,
            sleep_fn=sleep_fn,
            make_timeout_error=requests.exceptions.Timeout,
            respond=functools.partial(callback, request, context),
        )

    return wrapped
