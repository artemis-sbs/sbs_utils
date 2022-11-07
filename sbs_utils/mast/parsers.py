import re
import operator

class LayoutAreaNode:
    def __init__(self, token_type, value=None):
        self.token_type = token_type
        self.value = value
        self.children = []

# based on https://github.com/gnebehay/parser/blob/master/parser.py
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
    #AREA_LIST_TOKENS = "|".join(map(lambda a: f"({a})", rules.values()))
    AREA_LIST_TOKENS = r"[^\n]*"


    def lex(source):
        start = len(source)
        tokens=[]
        while(len(source)>0):
            match = False
            for token,rule in LayoutAreaParser.rules.items():
                m = re.match(rule,source)
                match = True
                if m is not None:
                    loc = m.span()
                    t = source[:loc[1]]
                    source = source[loc[1]:]
                    if token!= "ws":
                        tokens.append(LayoutAreaNode(token, t))
                    break
            if not match:
                raise Exception(f"Invalid syntax on token {source}")        

        tokens.append(LayoutAreaNode("eof", None))
        return tokens

    def match(tokens, token):
        if tokens[0].token_type == token:
            return tokens.pop(0)
        else:
            raise Exception('Invalid syntax on token {}'.format(tokens[0].token_type))        

    def parse_e(tokens):
        left_node = LayoutAreaParser.parse_e2(tokens)

        while tokens[0].token_type in ["plus", "minus"]:
            node = tokens.pop(0)
            node.children.append(left_node)
            node.children.append(LayoutAreaParser.parse_e2(tokens))
            left_node = node
            # if len(self.tokens)==0:
            #     return left_node
        return left_node

    def parse_e2(tokens):
        left_node = LayoutAreaParser.parse_values(tokens)
        while tokens[0].token_type in ["mul", "div"]:
            node = tokens.pop(0)
            node.children.append(left_node)
            node.children.append(LayoutAreaParser.parse_values(tokens))
            left_node = node
            # if len(self.tokens)==0:
            #     return left_node
        return left_node


    def parse_values(tokens):
        if tokens[0].token_type in ["pixels", "digits", "id"]:
            return tokens.pop(0)
        LayoutAreaParser.match(tokens,"lparen")
        expression = LayoutAreaParser.parse_e(tokens)
        LayoutAreaParser.match(tokens, "rparen")
        return expression

    def parse_list(tokens):
        expressions = []
        while len(tokens):
            expression = LayoutAreaParser.parse_e(tokens)
            expressions.append(expression)
            if tokens[0].token_type == "comma":
                tokens.pop(0)
                continue
            elif tokens[0].token_type == "eof":
                break
            else:
                raise Exception('Invalid syntax on token {}'.format(tokens[0].token_type))            
        return expressions

    operations = {
        "plus": operator.add,
        "minus": operator.sub,
        "mul": operator.mul,
        "div": operator.truediv
    }

    def compute(node, vars, aspect_ratio):
        match node.token_type:
            case "digits":
                return float(node.value)
            case "pixels":
                return (float(node.value[:-2])/aspect_ratio)*100
            case "id":
                return 12 #node.value

        left_result = LayoutAreaParser.compute(node.children[0], vars, aspect_ratio)
        right_result = LayoutAreaParser.compute(node.children[1], vars, aspect_ratio)
        operation = LayoutAreaParser.operations[node.token_type]
        return operation(left_result, right_result)




