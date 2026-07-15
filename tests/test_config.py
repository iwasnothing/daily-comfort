"""Tests for the config module."""

import os
import pytest
from unittest.mock import patch

from config import get_env, LLM_ENDPOINT, LLM_MODEL, APP_PORT


class TestGetEnv:
    """Tests for the get_env helper function."""

    def test_returns_env_var_when_set(self):
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            assert get_env("TEST_KEY", "default") == "test_value"

    def test_returns_default_when_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_env("NONEXISTENT_KEY_XYZ", "fallback") == "fallback"


class TestConfigDefaults:
    """Verify that configuration values are loaded (from .env or defaults)."""

    def test_llm_endpoint_is_loaded(self):
        assert isinstance(LLM_ENDPOINT, str) and len(LLM_ENDPOINT) > 0

    def test_llm_model_is_loaded(self):
        assert isinstance(LLM_MODEL, str) and len(LLM_MODEL) > 0

    def test_app_port_is_loaded(self):
        assert isinstance(APP_PORT, int) and APP_PORT > 0
