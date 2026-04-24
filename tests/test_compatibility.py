"""Tests for compatibility checker."""
import importlib.metadata
from unittest.mock import patch
import pytest

from compatibility.checker import (
    check_aider, check_anthropic, check_mcp, _parse_version
)


def test_parse_version_basic():
    assert _parse_version("0.50.0") == (0, 50, 0)
    assert _parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_prerelease():
    assert _parse_version("0.52.0a1") == (0, 52, 0)


def test_check_aider_installed_compatible():
    with patch("importlib.metadata.version", return_value="0.52.1"):
        result = check_aider()
    assert result["installed"]
    assert result["compatible"]
    assert result["version"] == "0.52.1"


def test_check_aider_too_old():
    with patch("importlib.metadata.version", return_value="0.49.0"):
        result = check_aider()
    assert result["installed"]
    assert not result["compatible"]


def test_check_aider_not_installed():
    with patch("importlib.metadata.version",
               side_effect=importlib.metadata.PackageNotFoundError("aider-chat")):
        result = check_aider()
    assert not result["installed"]
    assert not result["compatible"]


def test_check_anthropic_installed():
    with patch("importlib.metadata.version", return_value="0.40.0"):
        result = check_anthropic()
    assert result["compatible"]


def test_check_mcp_installed():
    with patch("importlib.metadata.version", return_value="1.0.0"):
        result = check_mcp()
    assert result["compatible"]
