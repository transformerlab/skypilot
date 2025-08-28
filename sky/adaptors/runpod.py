"""Compatibility wrapper for RunPod adaptor.

This module used to lazy-import the third-party ``runpod`` SDK. It now forwards
to ``sky.adaptors.runpod_client`` so the codebase consistently uses the
thread-safe, request-scoped GraphQL client without importing the old SDK.

Any imports like ``from sky.adaptors import runpod`` will resolve to the new
client API (run_graphql_query/get_client/QueryError/InvalidCredentialsError).
"""

# Re-export the new client API under this module to preserve compatibility.
from .runpod_client import (  # noqa: F401
    InvalidCredentialsError,
    QueryError,
    get_client,
    run_graphql_query,
)

