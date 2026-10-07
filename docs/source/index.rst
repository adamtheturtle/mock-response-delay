|project|
=========

Simulate a slow server, and the client timeout it causes, in HTTP mocks
------------------------------------------------------------------------

.. code-block:: console

   $ pip install 'mock-response-delay[requests]'

This requires Python |minimum-python-version|\+.

``responses`` and ``respx`` answer requests instantly, so a test of how code handles a slow server, or a timeout, has nothing to exercise.
This package wraps a mock's callback so that it answers as a server which takes a given number of seconds would.
A request whose read timeout is shorter than the delay waits for the timeout and then raises the same exception which the client library raises against a real slow server.
Any other request gets the response after waiting for the delay.

See :doc:`usage` for each client library, and :doc:`api-reference` for the details.

Reference
---------

.. toctree::
   :maxdepth: 3

   installation
   usage
   api-reference
   contributing

.. toctree::
   :hidden:

   unreleased
   changelog
   release-process
