"""A safe scientific calculator tool for the agent."""

import ast
import math
from collections.abc import Callable
from typing import ClassVar, cast


class SafeMathEvaluator:
    """Safely evaluate math expressions using an AST whitelist."""

    _OPERATORS: ClassVar[
        dict[type, Callable[[float | int, float | int], float | int]]
    ] = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a**b,
    }

    _UNARY_OPERATORS: ClassVar[dict[type, Callable[[float | int], float | int]]] = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    @staticmethod
    def _make_math_wrappers() -> dict[str, Callable[..., float | int]]:
        """Wrap math functions so they accept the args we permit at runtime."""

        def _float_float(func: Callable[[float], float]) -> Callable[..., float]:
            """Wrap a float -> float function and reject keyword arguments."""

            def wrapper(*args: object, **kwargs: object) -> float:
                if kwargs:
                    raise _EvalError("keyword arguments are not allowed")
                if len(args) != 1:
                    raise _EvalError(f"{func.__name__} expects exactly one argument")
                return func(float(cast(float | int | str, args[0])))

            return wrapper

        return {
            "sqrt": _float_float(math.sqrt),
            "abs": lambda *args: abs(args[0]),
            "ceil": _float_float(math.ceil),
            "floor": _float_float(math.floor),
            "round": lambda *args: round(*args),  # noqa: PLW0108
            "exp": _float_float(math.exp),
            "log": _float_float(math.log),
            "log10": _float_float(math.log10),
            "log2": _float_float(math.log2),
            "sin": _float_float(math.sin),
            "cos": _float_float(math.cos),
            "tan": _float_float(math.tan),
            "asin": _float_float(math.asin),
            "acos": _float_float(math.acos),
            "atan": _float_float(math.atan),
        }

    _FUNCTIONS: ClassVar[dict[str, Callable[..., float | int]]] = _make_math_wrappers()

    _CONSTANTS: ClassVar[dict[str, float]] = {
        "pi": math.pi,
        "e": math.e,
    }

    def evaluate(self, expression: str) -> str:
        """Evaluate a math expression string and return the result as a string.

        Args:
            expression: A math expression string, e.g. "2 + 3".

        Returns:
            The numeric result as a string, or an error message.

        """
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            return f"Error: {exc.msg}"
        try:
            result = self._eval_node(tree.body)
        except ZeroDivisionError:
            return "Error: division by zero"
        except ValueError as exc:
            return f"Error: {exc}"
        except _EvalError as exc:
            return f"Error: {exc}"
        return str(result)

    def _eval_node(self, node: ast.AST) -> float | int:
        """Recursively evaluate an AST node, raising _EvalError for disallowed nodes."""
        if isinstance(node, ast.Constant):
            return self._eval_constant(node)
        if isinstance(node, ast.BinOp):
            return self._eval_binop(node)
        if isinstance(node, ast.UnaryOp):
            return self._eval_unaryop(node)
        if isinstance(node, ast.Name):
            return self._eval_name(node)
        if isinstance(node, ast.Call):
            return self._eval_call(node)
        raise _EvalError(f"disallowed expression element: {type(node).__name__}")

    def _eval_constant(self, node: ast.Constant) -> float | int:
        """Return the numeric value of a constant node."""
        if isinstance(node.value, int | float):
            return node.value
        raise _EvalError(f"disallowed constant type: {type(node.value).__name__}")

    def _eval_binop(self, node: ast.BinOp) -> float | int:
        """Evaluate a binary operation node."""
        left = self._eval_node(node.left)
        right = self._eval_node(node.right)
        func = self._OPERATORS.get(type(node.op))
        if func is None:
            raise _EvalError(f"disallowed operator: {type(node.op).__name__}")
        return func(left, right)

    def _eval_unaryop(self, node: ast.UnaryOp) -> float | int:
        """Evaluate a unary operation node."""
        operand = self._eval_node(node.operand)
        func = self._UNARY_OPERATORS.get(type(node.op))
        if func is None:
            raise _EvalError(f"disallowed unary operator: {type(node.op).__name__}")
        return func(operand)

    def _eval_name(self, node: ast.Name) -> float | int:
        """Evaluate a name node against the constants whitelist."""
        value = self._CONSTANTS.get(node.id)
        if value is None:
            raise _EvalError(f"unknown name '{node.id}'")
        return value

    def _eval_call(self, node: ast.Call) -> float | int:
        """Evaluate a function call node against the functions whitelist."""
        if not isinstance(node.func, ast.Name):
            raise _EvalError("disallowed function call form")
        func_name = node.func.id
        func = self._FUNCTIONS.get(func_name)
        if func is None:
            raise _EvalError(f"unknown function '{func_name}'")
        if node.keywords:
            raise _EvalError("keyword arguments are not allowed")
        args = [self._eval_node(a) for a in node.args]
        return func(*args)


class _EvalError(Exception):
    """Internal error for disallowed or invalid expressions."""


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Supports arithmetic operators (+, -, *, /, //, %, **), unary operators,
    math functions (sqrt, sin, cos, tan, log, exp, abs, etc.), and constants
    (pi, e). Expressions are evaluated safely via an AST whitelist -- no
    arbitrary code execution.

    Args:
        expression: A math expression string, e.g. "2 + 3 * sqrt(16)".

    Returns:
        The numeric result as a string, or an error message if the
        expression is invalid or unsafe.

    """
    return SafeMathEvaluator().evaluate(expression)
