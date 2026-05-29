"""Integration test: full gather flow."""

import pytest


@pytest.mark.integration
def test_gather_flow():
    """End-to-end gather flow test (requires emulator)."""
    pytest.skip("Integration test requires running emulator")
