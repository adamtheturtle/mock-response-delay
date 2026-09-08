Changelog
=========

.. towncrier release notes start

2026.09.08
----------

- Require callbacks returned by ``delayed_responses_callback`` to be invoked by ``responses`` rather than directly with an ordinary ``requests.PreparedRequest``.

- Use a local protocol for ``responses`` callback requests, allowing direct access to ``req_kwargs`` while the public upstream type is pending.

2026.09.07
----------

- Initial release: ``delayed_responses_callback``, ``delayed_httpx_handler`` and ``delayed_httpx2_handler``.
