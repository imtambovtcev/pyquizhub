import ast
import operator


class SafeEvaluator:
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
        ast.GtE: operator.ge
    }

    @staticmethod
    def eval_expr(expr, variables):
        """Safely evaluates a mathematical or logical expression."""
        def _eval(node):
            if isinstance(node, ast.BinOp):
                left = _eval(node.left)
                right = _eval(node.right)
                return SafeEvaluator.ALLOWED_OPERATORS[type(node.op)](left, right)
            elif isinstance(node, ast.Compare):
                left = _eval(node.left)
                # Only single comparisons are allowed
                right = _eval(node.comparators[0])
                return SafeEvaluator.ALLOWED_OPERATORS[type(node.ops[0])](left, right)
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
