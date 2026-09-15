"""A safe scientific calculator tool for the agent."""

import ast
import math
import operator as op


class SafeMathEvaluator:
    """Safely evaluate math expressions using an AST whitelist."""

    _OPERATORS: dict[type, object] = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.FloorDiv: op.floordiv,
        ast.Mod: op.mod,
        ast.Pow: op.pow,
    }

    _UNARY_OPERATORS: dict[type, object] = {
        ast.UAdd: op.pos,
        ast.USub: op.neg,
    }

    _FUNCTIONS: dict[str, object] = {
        "sqrt": math.sqrt,
        "abs": abs,
        "ceil": math.ceil,
        "floor": math.floor,
        "round": round,
        "exp": math.exp,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
    }

    _CONSTANTS: dict[str, float] = {
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
            if isinstance(node.value, int | float):
                return node.value
            raise _EvalError(f"disallowed constant type: {type(node.value).__name__}")
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            func = self._OPERATORS.get(type(node.op))
            if func is None:
                raise _EvalError(f"disallowed operator: {type(node.op).__name__}")
            return func(left, right)  # type: ignore[operator]
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            func = self._UNARY_OPERATORS.get(type(node.op))
            if func is None:
                raise _EvalError(f"disallowed unary operator: {type(node.op).__name__}")
            return func(operand)  # type: ignore[operator]
        if isinstance(node, ast.Name):
            value = self._CONSTANTS.get(node.id)
            if value is None:
                raise _EvalError(f"unknown name '{node.id}'")
            return value
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise _EvalError("disallowed function call form")
            func_name = node.func.id
            func = self._FUNCTIONS.get(func_name)
            if func is None:
                raise _EvalError(f"unknown function '{func_name}'")
            if node.keywords:
                raise _EvalError("keyword arguments are not allowed")
            args = [self._eval_node(a) for a in node.args]
            return func(*args)  # type: ignore[operator]
        raise _EvalError(f"disallowed expression element: {type(node).__name__}")


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
