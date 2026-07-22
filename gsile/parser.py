from __future__ import annotations
from gnodes import *
import string

__all__ = ["Parser"]

types = [list(set([
    *string.ascii_letters,
    *"1234567890.", *"_"
])), "+-*/=<>", "()", "[]"]

class ParserContext:
    def __init__(self, source: str, lines: list[str], line_starts: dict[int, int], parent: ParserContext | None = None):
        self.parent: ParserContext | None = parent

        self.char: int = 0
        self.line: int = 0

        self.source: str = source
        self.lines: list[str] = lines
        self.line_starts: dict[int, int] = line_starts

class Parser:
    def __init__(self):
        self.contextstack: list[ParserContext] = []
        self.binop_precedence = {
            "**": 4,
            "*": 3,
            "/": 3,
            "+": 2,
            "-": 2,
            "==": 1,
            "<=": 1,
            ">=": 1,
            "<": 1,
            ">": 1,
        }
    
    @property
    def ctx(self):
        return self.contextstack[-1]

    def add_stack(self, source: str, lines: list[str], line_starts: dict[int, int]):
        if len(self.contextstack) > 0:
            self.contextstack.append(ParserContext(source, lines, line_starts, self.ctx))
        else:
            self.contextstack.append(ParserContext(source, lines, line_starts))

    def pop_stack(self):
        self.contextstack.pop()

    def skiplines(self, lines: int):
        self.ctx.line += lines
        self.ctx.char = self.ctx.line_starts[self.ctx.line]
    
    def get_between(self, left: str, right: str, start_char: int, skiplines: bool = False):
        depth = 0
        ldel = -1
        rdel = -1
        num_lines = 0

        for i, char in enumerate(self.ctx.source[start_char:]):
            if char == left:
                depth += 1
                if ldel == -1:
                    ldel = i + start_char + 1
            elif char == right:
                depth -= 1
                if depth == 0:
                    rdel = i + start_char
                    break
            
            elif char == "\n":
                num_lines += 1
        
        if ldel == -1 or rdel == -1:
            raise RuntimeError(f"{ldel} {rdel}")

        if skiplines:
            self.skiplines(num_lines)
        
        return self.ctx.source[ldel:rdel]

    def clear(self):
        self.contextstack.clear()

    def get_node_data(self) -> NodeData:
        return NodeData(self.ctx.line)

    def parse(self, source: str) -> NodeBody:
        lines = []
        line_starts = {0:0}
        line = 0

        temp = ""
        source += "\n"
        for i, char in enumerate(source):
            if char in "\n;":
                lines.append(temp.strip())
                temp = ""

                line += 1
                line_starts[line] = i + 1
            temp += char

        self.add_stack(source, lines, line_starts)
        ctx = self.ctx

        numlines = len(ctx.lines)

        nodes = []
        while ctx.line < numlines:
            line = ctx.lines[ctx.line]
            line = line.strip()

            # I definitely need to add comments to GScript, it is just sad.

            node = self.parse_line(line)
            if node != None:
                nodes.append(node)
            ctx.line += 1
            ctx.char = ctx.line_starts[ctx.line]
        self.pop_stack()
        return NodeBody(nodes, nodedata=NodeData(-1))

    def is_num(self, string: str) -> bool:
        for char in string:
            if char not in "1234567890.":
                return False
        return True

    def parse_line(self, line: str):
        if not line: return

        for i, char in enumerate(line):
            if char == "{":
                break
            if char == "}":
                line = line[i:]
                break

        if not line: return

        if line.startswith("struct"):
            return self.parse_struct(line)

        if line.startswith("def"):
            return self.parse_func(line)

        if line.startswith("template"):
            return self.parse_template(line)
        
        if line.startswith("for"):
            return self.parse_for(line)
        
        if line.startswith("return"):
            return Return(self.parse_expr(line[6:]), nodedata=self.get_node_data())

        if line.startswith("#"):
            split = line[1:].split(" ")
            return self.parse_instruction(line, split)

        if line.startswith("if"):
            return self.parse_if_stmt(line)

        if "=" in line:
            left, right = line.split("=")
            splitleft = left.strip().split(" ")
            
            if len(splitleft) == 2:
                kind = " ".join(splitleft[:-1])
                target = splitleft[-1]
                return Declare(Name(target, nodedata=self.get_node_data()), kind, self.parse_expr(right), nodedata=self.get_node_data())
            
            target = splitleft[-1]
            if "." in target:
                return Assign(self.parse_attribute(target), self.parse_expr(right), nodedata=self.get_node_data())
            return Assign(Name(target, nodedata=self.get_node_data()), self.parse_expr(right), nodedata=self.get_node_data())
        
        split = line.split(" ")
        if len(split) == 2:
            return Declare(Name(split[1], nodedata=self.get_node_data()), split[0], Empty(nodedata=self.get_node_data()), nodedata=self.get_node_data())
        
        return self.parse_expr(line)

    def parse_template(self, line: str):
        arg_text = self.get_between("<", ">", line.index("<"))
        args = [arg.strip() for arg in arg_text.split(",")]

        return Template(args, nodedata=self.get_node_data())

    def parse_for(self, line: str):
        condition = self.get_between("(", ")", self.ctx.char + line.index("("))

        bodytext = self.get_between("{", "}", self.ctx.char, True)
        body = self.parse(bodytext).children

        return ForLoop(self.parse_expr(condition), body, nodedata=self.get_node_data())

    def parse_if_stmt(self, line: str):
        condition = self.get_between("(", ")", self.ctx.char + line.index("("))

        bodytext = self.get_between("{", "}", self.ctx.char, skiplines=True)
        body = self.parse(bodytext).children

        return If(self.parse_expr(condition), body, nodedata=self.get_node_data())

    def parse_struct(self, line: str):
        split = line.split(" ")
        name = split[1]

        bodytext = self.get_between("{", "}", self.ctx.char + len(" ".join(split[:2])), skiplines=True)
        body = self.parse(bodytext)

        return Struct(name, body, nodedata=self.get_node_data())

    def parse_instruction(self, line: str, split: list[str]):
        instruction = split[0]
        match instruction:
            case "include":
                lcaret = line.index("<")
                path = self.get_between("<", ">", lcaret + self.ctx.char)
                return Include(path, nodedata=self.get_node_data())

    def parse_list(self, expr: str):
        expr = expr.replace(" ", "")
        expr = expr[1:-1]
        return List([self.parse_expr(e) for e in expr.split(",")], nodedata=self.get_node_data())

    def parse_string(self, expr: str):
        if expr[0] == '"' and expr[-1] == '"':
            expr = expr[1:-1]

        escaped = True
        result = []
        for char in expr:
            if char == "\\":
                escaped = not escaped
            
            if escaped:
                result.append(char)
                continue
            
            match char:
                case "n":
                    result.pop()
                    result.append("\n")
                case _:
                    result.append(char)
            
        return String("".join(result), nodedata=self.get_node_data())

    def parse_expr(self, expr: str):
        expr = expr.strip()
        if not expr:
            return Empty()
        
        if expr[0] == '"' and expr[-1] == '"':
            return self.parse_string(expr)

        if self.is_num(expr):
            return Constant(expr, nodedata=self.get_node_data())
        
        if "in" in expr:
            split = expr.split(" ")
            if len(split) == 3:
                if split[1] == "in":
                    return In(Name(split[0], nodedata=self.get_node_data()), self.parse_expr(split[2]), nodedata=self.get_node_data())

        if expr[0] == "[" and expr[-1] == "]":
            return self.parse_list(expr)
        
        if expr[0] == "(" and expr[-1] == ")":
            expr = expr[1:-1]
        
        tokens = self.tokenize_expr(expr)

        if not tokens:
            return

        is_expr = False
        for token in tokens:
            if token in self.binop_precedence:
                is_expr = True
                break

        if not is_expr:
            return self.parse_part(expr)

        max_prec = 9999
        low_i = -1
        for i, token in enumerate(tokens):
            if token in self.binop_precedence:
                prec = self.binop_precedence[token]
                if prec < max_prec:
                    max_prec = prec
                    low_i = i
        
        left = ''.join(tokens[:low_i])
        right = ''.join(tokens[1+low_i:])
        op = tokens[low_i]
        
        return BinOp(self.parse_expr(left), op, self.parse_expr(right), nodedata=self.get_node_data())

    def parse_part(self, expr: str):
        expr = expr.strip()
        if not expr:
            return
        
        if self.is_num(expr):
            return Constant(expr)
        
        attr = False
        depth = 0
        for char in expr:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            
            if depth == 1:
                if char == "(":
                    return self.parse_call(expr)
                
            elif depth == 0:
                if char == ".":
                    attr = True
        
        if attr:
            target = ""
            for char in expr:
                if char in "() \n":
                    return self.parse_attribute(target)
                target += char
            return self.parse_attribute(target)

        return Variable(expr, nodedata=self.get_node_data())
    
    def parse_attribute(self, expr: str):
        expr = expr.strip()
        if "." not in expr:
            return self.parse_expr(expr)
        
        indices = []
        for i, char in enumerate(expr):
            if char == ".":
                indices.append(i)

        dot = indices[-1]
        target = expr[:dot]
        attr = expr[dot+1:]

        return Attribute(self.parse_expr(target), Name(attr, nodedata=self.get_node_data()), nodedata=self.get_node_data())

    def parse_call(self, expr: str):
        lparen = -1
        rparen = -1

        depth = 0
        for i, char in enumerate(expr):
            if char == "(":
                depth += 1
                if lparen == -1:
                    lparen = i + 1

        for i, char in enumerate(expr):
            if char == ")":
                depth -= 1
                if depth == 0:
                    rparen = i
                    break
        
        name = expr[:lparen - 1]

        argstext = expr[lparen:rparen].strip()
        if argstext:
            args = [self.parse_expr(a) for a in argstext.split(",")]
        else:
            args = []

        return Call(self.parse_expr(name), Arguments(args, nodedata=self.get_node_data()), nodedata=self.get_node_data())

    def parse_func(self, line: str):
        parts = line.split(" ")
        specification = " ".join(parts[2:])
        rkind = parts[1]

        lparen = 0
        rparen = 0

        name = ""
        for i, char in enumerate(specification):
            if char == "(":
                lparen = i + 1
                break
            name += char

        for i, char in enumerate(specification):
            if char == ")":
                rparen = i
                break
        
        param_text = specification[lparen:rparen]
        params = Arguments([Name(p.strip(), nodedata=self.get_node_data()) for p in param_text.split(",")], nodedata=self.get_node_data())

        bodytext = self.get_between("{", "}", self.ctx.char + rparen, skiplines=True)
        body = self.parse(bodytext).children
        
        return FunctionDef(rkind, Name(name, nodedata=self.get_node_data()), params, body, nodedata=self.get_node_data())
    
    def tokenize_expr(self, expr: str):
        expr = expr.strip()
        if not expr:
            return []

        def get_type(expr: str) -> int:
            for i, t in enumerate(types):
                if expr in t:
                    return i
            raise RuntimeError(f"expr {expr!r}")

        stripped = expr.replace(" ", "")

        delimited = ""
        last = None
        in_call = False

        depth = 0
        is_in_string = False
        for char in stripped:
            if char == "(" and not is_in_string:
                depth += 1
                if last != 0:
                    delimited += ";"
                else:
                    delimited += "("
                    if depth == 1: in_call = True
                continue

            if char == ")" and not is_in_string:
                depth -= 1
                if in_call:
                    delimited += ")"
                if depth == 0:
                    delimited += ";"
                continue

            if char == '"':
                is_in_string = not is_in_string
                if is_in_string and depth == 0:
                    delimited += ";"
                delimited += char

                if (not is_in_string) and depth == 0:
                    delimited += ";"
                continue

            if last == None:
                last = get_type(char)
                delimited += char
                continue

            if depth == 0 and not is_in_string:
                ctype = get_type(char)
                if last != ctype:
                    delimited += ";"
                last = ctype

            delimited += char

        return delimited.split(";")

def parse(text: str) -> NodeBody:
    parser = Parser()
    return parser.parse(text)