Installation
------------

Install the extra for the client library which the code under test uses:

.. code-block:: console

   $ pip install 'mock-response-delay[requests]'
   $ pip install 'mock-response-delay[httpx]'
   $ pip install 'mock-response-delay[httpx2]'

This requires Python |minimum-python-version|\+.

Each client library has its own module, so that only the library which is used needs to be installed.
