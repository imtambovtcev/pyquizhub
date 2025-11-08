"""
Provides safe expression evaluation capabilities for quiz conditions.

This module implements a restricted expression evaluator that safely handles
mathematical and logical expressions while preventing code injection and
access to unauthorized operations.
"""

import ast
import operator
from typing import Any, Dict
import logging
from pyquizhub.config.settings import get_logger

logger = get_logger(__name__)


class SafeEvaluator:
    """
    Safely evaluates mathematical and logical expressions with restricted operations.

    This class provides a secure way to evaluate expressions by:
    - Allowing only whitelisted operators
    - Preventing access to potentially dangerous builtins
    - Restricting variable access to provided context

    Attributes:
        ALLOWED_OPERATORS (dict): Mapping of AST operator nodes to Python operator functions
    """

    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda left, right: left in right,
    }

    @staticmethod
    def eval_expr(expr: str, variables: dict) -> any:
        """
        Safely evaluates a mathematical or logical expression.

        Args:
            expr (str): The expression to evaluate
            variables (dict): Variables available in the expression context

        Returns:
            any: Result of the expression evaluation

        Raises:
            ValueError: If expression contains unauthorized operations or variables

        Examples:
            >>> SafeEvaluator.eval_expr("2 + 2", {})
            4
            >>> SafeEvaluator.eval_expr("score > 10", {"score": 15})
            True
        """
        logger.debug(
            f"Evaluating expression: {expr} with variables: {variables}")

        def _eval(node):
            if isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                return SafeEvaluator.ALLOWED_OPERATORS[type(
                    node.op)](left, right)
            elif isinstance(node, ast.Compare):
                left = _eval(node.left)
                # Only single comparisons are allowed
                right = _eval(node.comparators[0])
                return SafeEvaluator.ALLOWED_OPERATORS[type(
                    node.ops[0])](left, right)
            elif isinstance(node, ast.Num):  # For Python 3.8 and earlier
                return node.n
            elif isinstance(node, ast.Constant):  # For Python 3.9+
                return node.value
            elif isinstance(node, ast.Name):
                # Handle JSON booleans: true/false
                if node.id == "true":
                    return True
                if node.id == "false":
                    return False
                if node.id in variables:
                    return variables[node.id]
                raise ValueError(f"Unauthorized variable: {node.id}")
            else:
                raise ValueError(f"Unsupported expression: {node}")

        tree = ast.parse(expr, mode='eval')
        return _eval(tree.body)
