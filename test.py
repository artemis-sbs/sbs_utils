import re

class LayoutAreaNode:
    def __init__(self, token_type, value=None):
        self.token_type = token_type
        self.value = value
        self.children = []

class LayoutAreaParser:
    rules = {
        "ws": r"[ \t]+",
        "pixels": r"\d+px",
        "digits": r"\d+(\.\d+)?",
        "id": r"[_a-zA-Z][_a-zA-Z0-9]*",
        "comma": r",",
        "plus": r"\+",
        "minus": r"\-",
        "mul": r"\*",
        "div": r"\/",
        "lparen": r"\(",
        "rparen": r"\)",
    }
    AREA_LIST_TOKENS = "|".join(map(lambda a: f"({a})", rules.values()))

    def __init__(self) -> None:
        self.tokens=[]

    def lex(self, source):
        while(len(source)>0):
            for token,rule in LayoutAreaParser.rules.items():
                m = re.match(rule,source)
                if m is not None:
                    loc = m.span()
                    t = source[:loc[1]]
                    source = source[loc[1]:]
                    if token!= "ws":
                        self.tokens.append(LayoutAreaNode(token, t))
                    break
        self.tokens.append(LayoutAreaNode("eof", None))

    def match(self, token):
        if self.tokens[0].token_type == token:
            return self.tokens.pop(0)
        else:
            raise Exception('Invalid syntax on token {}'.format(self.tokens[0].token_type))        

    def parse_e(self):
        left_node = self.parse_e2()

        while self.tokens[0].token_type in ["plus", "minus"]:
            node = self.tokens.pop(0)
            node.children.append(left_node)
            node.children.append(self.parse_e2())
            left_node = node
            # if len(self.tokens)==0:
            #     return left_node
        return left_node

    def parse_e2(self):
        left_node = self.parse_values()
        while self.tokens[0].token_type in ["mul", "div"]:
            node = self.tokens.pop(0)
            node.children.append(left_node)
            node.children.append(self.parse_values())
            left_node = node
            # if len(self.tokens)==0:
            #     return left_node
        return left_node


    def parse_values(self):
        if self.tokens[0].token_type in ["pixels", "digits", "id"]:
            return self.tokens.pop(0)
        self.match("lparen")
        expression = self.parse_e()
        self.match("rparen")
        return expression

    def parse_list(self):
        expressions = []
        while len(self.tokens):
            expression = self.parse_e()
            expressions.append(expression)
            if self.tokens[0].token_type == "comma":
                self.tokens.pop(0)
                continue
            elif self.tokens[0].token_type == "eof":
                break
            else:
                raise Exception('Invalid syntax on token {}'.format(self.tokens[0].token_type))            
        return expressions





import operator

operations = {
    "plus": operator.add,
    "minus": operator.sub,
    "mul": operator.mul,
    "div": operator.truediv
}

def compute(node):
    match node.token_type:
        case "digits":
            return float(node.value)
        case "pixels":
            return float(node.value[:-2])
        case "id":
            return 12 #node.value

    left_result = compute(node.children[0])
    right_result = compute(node.children[1])
    operation = operations[node.token_type]
    return operation(left_result, right_result)


ex = LayoutAreaParser()
ex.lex("""123px + 90, 90-23,(2*80)+2, 50 + x * y""")
#for node in ex.tokens:
#    print(f"{node.token_type} {node.value}")

asts = ex.parse_list()
for ast in asts:
    print (compute(ast))

print (AREA_LIST_TOKENS)


