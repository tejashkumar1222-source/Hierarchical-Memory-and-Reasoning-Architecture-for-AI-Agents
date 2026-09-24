"""
HMRA Safe AST Calculator Tool
"""

import ast
import operator as op
import math

ALLOWED_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

def eval_ast_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    elif isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
        left = eval_ast_node(node.left)
        right = eval_ast_node(node.right)
        if isinstance(node.op, ast.Pow) and (abs(left) > 1000 or abs(right) > 20):
            raise ValueError("Exponent too large for safe evaluation")
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise ValueError("Division by zero")
        return ALLOWED_OPERATORS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
        operand = eval_ast_node(node.operand)
        return ALLOWED_OPERATORS[type(node.op)](operand)
    raise ValueError(f"Unsupported math operation: {type(node).__name__}")

def safe_calculate(expression: str) -> float:
    """Evaluates an arithmetic expression safely using python AST parsing."""
    cleaned = expression.replace('^', '**').strip()
    parsed = ast.parse(cleaned, mode='eval')
    result = eval_ast_node(parsed.body)
    return round(result, 6)
