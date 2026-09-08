"""Simulate a slow server, and the client timeout it causes, in HTTP mocks.

Each supported client library has its own module, so that only the
library which is used needs to be installed:

* :mod:`mock_response_delay.for_requests` for ``responses`` callbacks.
* :mod:`mock_response_delay.for_requests_mock` for ``requests-mock`` callbacks.
* :mod:`mock_response_delay.for_httpx` for ``respx`` side effects and
  ``httpx`` transport handlers.
* :mod:`mock_response_delay.for_httpx2` for ``httpx2`` transport handlers.
"""
