"""The delay and timeout logic which every client library shares."""

from collections.abc import Callable, Mapping
from typing import TypeGuard

from beartype import BeartypeConf, beartype


def _is_object_mapping(
    value: object,
    /,
) -> TypeGuard[Mapping[object, object]]:
    """Return whether a value is a mapping with arbitrary contents."""
    return isinstance(value, Mapping)


def read_timeout_from_extension(*, timeout_info: object) -> float | None:
    """Read a numeric read timeout from an HTTP request extension."""
    if not _is_object_mapping(timeout_info):
        return None
    read_timeout = timeout_info.get("read")
    return (
        float(read_timeout) if isinstance(read_timeout, (int, float)) else None
    )


@beartype(conf=BeartypeConf(is_pep484_tower=True))
def respond_after_delay[T](
    *,
    read_timeout_seconds: float | None,
    delay_seconds: float,
    sleep_fn: Callable[[float], None],
    make_timeout_error: Callable[[], BaseException],
    respond: Callable[[], T],
) -> T:
    """Respond as a server which takes ``delay_seconds`` to answer would.

    A client gives up on a slow server once its read timeout passes, so
    a delay longer than the read timeout means the client waits for the
    timeout and then raises, and never sees the response.  A shorter
    delay means the client waits for the delay and then gets the
    response.

    Args:
        read_timeout_seconds: How long the client waits for a response
            before giving up, or ``None`` if it waits forever.
        delay_seconds: How long the simulated server takes to respond.
        sleep_fn: What to call to wait.  It is given the number of
            seconds to wait for, which is the read timeout when the
            client gives up and the delay otherwise.
        make_timeout_error: What to call to make the error which the
            client raises when it gives up.
        respond: What to call to get the response.  It is not called when
            the client gives up, because a server which has not yet
            answered has not yet done anything which the client can
            observe.

    Returns:
        The response.

    Raises:
        BaseException: The error from ``make_timeout_error`` when the
            delay is longer than the read timeout.
    """
    if (
        read_timeout_seconds is not None
        and delay_seconds > read_timeout_seconds
    ):
        sleep_fn(read_timeout_seconds)
        raise make_timeout_error()

    response = respond()
    sleep_fn(delay_seconds)
    return response
