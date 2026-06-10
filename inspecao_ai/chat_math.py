import ast
import math
import operator
import re


SAFE_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

SAFE_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "pi": lambda: math.pi,
    "e": lambda: math.e,
}


def parece_calculo(texto):
    return texto.startswith("calcula") or bool(re.fullmatch(r"[\d\s\.\,\+\-\*\/\(\)\%\^a-zA-Z_]+", texto))


def avaliar_expressao_segura(texto):
    expr = texto.lower().replace("calcula", "").strip().replace("^", "**").replace(",", ".")
    if not expr:
        return None
    try:
        node = ast.parse(expr, mode="eval")
        valor = _eval_node(node.body)
        if isinstance(valor, float):
            return round(valor, 6)
        return valor
    except Exception:
        return None


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in SAFE_BIN_OPS:
        return SAFE_BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_UNARY_OPS:
        return SAFE_UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
        func = SAFE_FUNCTIONS[node.func.id]
        args = [_eval_node(arg) for arg in node.args]
        return func(*args)
    if isinstance(node, ast.Name) and node.id in {"pi", "e"}:
        return SAFE_FUNCTIONS[node.id]()
    raise ValueError("Expressão não suportada")
