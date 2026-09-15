# Design: `calculate` Agent Tool

**Date:** 2026-09-16
**Status:** Approved

## Purpose

Add a scientific calculator tool to the harness agent's tool set. The LLM agent can call `calculate(expression="...")` to evaluate a math expression string and get a numeric result back. This gives the agent a reliable way to perform arithmetic and scientific computations without relying on the shell or its own mental math.

## Scope

- **In scope:** A `calculate` tool function, a safe expression evaluator, registration in the tool set, and tests.
- **Out of scope:** Symbolic algebra, unit conversion, expression simplification, history/state, variables or assignment.

## Interface

```python
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Args:
        expression: A math expression string, e.g. "2 + 3 * sqrt(16)".

    Returns:
        The numeric result as a string, or an error message if the
        expression is invalid or unsafe.
    """
```

### Supported Operations

| Category     | Examples                                          |
| ------------ | ------------------------------------------------- |
| Arithmetic   | `+`, `-`, `*`, `/`, `//` (floor div), `%`, `**`   |
| Unary        | `-x`, `+x`                                        |
| Functions    | `sqrt`, `abs`, `sin`, `cos`, `tan`, `asin`,       |
|              | `acos`, `atan`, `log` (natural), `log10`,         |
|              | `log2`, `exp`, `ceil`, `floor`, `round`           |
| Constants    | `pi`, `e`                                         |

## Safety

The tool **never** uses `eval()` on user input. Instead it:

1. Parses the expression string with `ast.parse(expression, mode="eval")` into an AST.
2. Walks the AST recursively, evaluating only whitelisted node types:
   - `ast.Expression` (root)
   - `ast.BinOp` with operator in a whitelist (`Add`, `Sub`, `Mult`, `Div`, `FloorDiv`, `Mod`, `Pow`)
   - `ast.UnaryOp` with operator in a whitelist (`USub`, `UAdd`)
   - `ast.Call` where the function is an `ast.Name` matching a whitelisted math function
   - `ast.Constant` of type `int` or `float`
   - `ast.Name` matching a whitelisted constant (`pi`, `e`)
3. Any node not in the whitelist causes the tool to return an error string. This includes attribute access, subscripts, comprehensions, lambdas, and any other Python constructs.

The whitelisted functions are mapped to functions from the `math` module (and builtins for `abs` and `round`).

## Error Handling

The tool **never raises**. All error conditions return descriptive strings, consistent with the existing tool pattern (`str_replace` returns error strings rather than raising):

- **Parse error:** Malformed expression -> `"Error: <message>"`
- **Unknown function:** `"Error: unknown function 'foo'"`
- **Unknown name/constant:** `"Error: unknown name 'bar'"`
- **Disallowed node:** `"Error: disallowed expression element: <node type>"`
- **Division by zero:** `"Error: division by zero"`
- **Math domain error** (e.g. `sqrt(-1)`): `"Error: <message>"`
- **TypeError/ValueError from functions:** `"Error: <message>"`

## Components

### `tools/calculate.py`

- `SafeMathEvaluator` class (or equivalent module-level helpers) that holds the operator whitelist, function whitelist, and constant whitelist, and exposes an `evaluate(expression: str) -> str` method.
- `calculate(expression: str) -> str` -- the tool function, which delegates to the evaluator and returns the result or error string.

### `tools/tools.py` (modified)

- Import `calculate` from `tools.calculate`.
- Add `calculate` to `_TOOL_FUNCTIONS` list.

### `tests/test_calculate.py`

- Basic arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Unary operators
- Each whitelisted function at least once
- Constants: `pi`, `e`
- Complex expressions: `"2 + 3 * sqrt(16)"`
- Error cases: division by zero, unknown function, unknown name, disallowed node (attribute access, call to non-whitelisted), parse error, math domain error

## Data Flow

```
LLM agent
  |
  |  calculate(expression="2 + 3 * sqrt(16)")
  v
tools.calculate.calculate()
  |
  v
SafeMathEvaluator.evaluate()
  |  ast.parse  ->  walk AST  ->  compute result
  v
returns "8.0" (or error string)
  |
  v
back to agent
```

## Testing

Table-driven tests in `tests/test_calculate.py` following the project's existing test style. Covers:

1. **Happy path** -- each operator, each function, each constant, nested expressions.
2. **Error path** -- all error conditions listed above.
3. **Safety** -- expressions that would be dangerous with `eval()` (attribute access, builtins, names) are rejected.

Tests use `pytest` and plain assertions, matching `tests/test_permissions.py` conventions.