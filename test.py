import ast

import math

__version__ = "1.0"

ALLOWED_NAMES = {
    k: v for k, v in math.__dict__.items() if not k.startswith("__")
}

def evaluate(expression, locals):
    """Evaluate a math expression."""
    # Compile the expression
    code = compile(expression, "<string>", "eval")
    allowed = ALLOWED_NAMES | locals

    return eval(code, {"__builtins__": {}}, allowed)

def assign(rhs, value, locals):
    locals = {"__quest_value": value} | locals
    exec(f"""{rhs} = __quest_value""",{"__builtins__": {}}, locals)


class QuestData(object):
    def __init__(self, s):
        dictionary  = ast.literal_eval(s)
        #for dictionary in initial_data:
        for key in dictionary:
            setattr(self, key, dictionary[key])

x = 2
y =3

object_name = QuestData("""{"x":4, "y":7}""")
object_name.x = 12

v = evaluate("w.x * 50 -w.y", {"w": object_name})
assign("w.x", v, {"w": object_name})

#print(eval("x+y",vals))
print(object_name.x)

