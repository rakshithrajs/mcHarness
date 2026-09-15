"""Tests for the calculate tool."""

import math

import pytest

from tools.calculate import calculate
from tools.tools import OLLAMA_TOOLS, TOOLS


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3", "5"),
        ("10 - 4", "6"),
        ("3 * 4", "12"),
        ("15 / 4", "3.75"),
        ("2 + 3 * 4", "14"),
        ("(2 + 3) * 4", "20"),
    ],
)
def test_basic_arithmetic(expression: str, expected: str) -> None:
    """Test basic arithmetic operations."""
    assert calculate(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("15 // 4", "3"),
        ("15 % 4", "3"),
        ("2 ** 10", "1024"),
        ("-5", "-5"),
        ("+5", "5"),
        ("-(2 + 3)", "-5"),
    ],
)
def test_extended_arithmetic_and_unary(expression: str, expected: str) -> None:
    """Test floor division, modulo, power, and unary operators."""
    assert calculate(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("sqrt(16)", "4.0"),
        ("abs(-7)", "7"),
        ("ceil(3.2)", "4"),
        ("floor(3.8)", "3"),
        ("round(3.14159)", "3"),
        ("round(3.14159, 2)", "3.14"),
        ("exp(0)", "1.0"),
        ("log(1)", "0.0"),
        ("log10(1000)", "3.0"),
        ("log2(8)", "3.0"),
        ("sin(0)", "0.0"),
        ("cos(0)", "1.0"),
        ("tan(0)", "0.0"),
        ("asin(0)", "0.0"),
        ("acos(1)", "0.0"),
        ("atan(0)", "0.0"),
        ("sqrt(16) + 1", "5.0"),
        ("2 * abs(-3)", "6"),
    ],
)
def test_math_functions(expression: str, expected: str) -> None:
    """Test scientific math functions."""
    assert calculate(expression) == expected


def test_pi_constant() -> None:
    """Test that pi is available as a constant."""
    result = calculate("pi")
    assert result == str(math.pi)


def test_e_constant() -> None:
    """Test that e is available as a constant."""
    result = calculate("e")
    assert result == str(math.e)


def test_constant_in_expression() -> None:
    """Test that constants work inside expressions."""
    result = calculate("2 * pi")
    assert result == str(2 * math.pi)


@pytest.mark.parametrize(
    "expression",
    [
        "1 / 0",
        "5 % 0",
        "1 // 0",
    ],
)
def test_division_by_zero(expression: str) -> None:
    """Test that division by zero returns an error string."""
    assert calculate(expression) == "Error: division by zero"


def test_math_domain_error() -> None:
    """Test that a math domain error returns an error string."""
    assert calculate("sqrt(-1)").startswith("Error:")


def test_parse_error() -> None:
    """Test that a malformed expression returns an error string."""
    assert calculate("2 + +").startswith("Error:")


def test_unknown_function() -> None:
    """Test that an unknown function returns an error string."""
    assert calculate("foo(1)") == "Error: unknown function 'foo'"


def test_unknown_name() -> None:
    """Test that an unknown name returns an error string."""
    assert calculate("bar") == "Error: unknown name 'bar'"


def test_disallowed_attribute_access() -> None:
    """Test that attribute access is rejected (e.g. __import__)."""
    assert calculate("__import__('os')").startswith("Error:")


def test_disallowed_call_form() -> None:
    """Test that calling a non-name (e.g. a method) is rejected."""
    result = calculate("(1).bit_length()")
    assert result.startswith("Error:")


def test_disallowed_string_constant() -> None:
    """Test that string constants are rejected."""
    result = calculate("'hello'")
    assert result.startswith("Error:")


def test_disallowed_keyword_args() -> None:
    """Test that keyword arguments to functions are rejected."""
    result = calculate("round(3.14, ndigits=1)")
    assert result.startswith("Error:")


def test_no_arbitrary_code_execution() -> None:
    """Test that Python builtins cannot be invoked."""
    assert calculate("open('secret.txt')").startswith("Error:")


def test_calculate_is_registered_as_tool() -> None:
    """Test that calculate is registered in the TOOLS dispatch dict."""
    assert "calculate" in TOOLS
    assert TOOLS["calculate"] is calculate


def test_calculate_in_ollama_tools() -> None:
    """Test that calculate appears in the OLLAMA_TOOLS list."""
    tool_names = [t.function.name for t in OLLAMA_TOOLS]  # type: ignore[attr-defined]
    assert "calculate" in tool_names
