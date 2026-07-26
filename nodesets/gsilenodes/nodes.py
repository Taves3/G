from __future__ import annotations

class Node:
    def __init__(self, children: list[Node], *, nodedata: NodeData):
        self.children = children
        self.data = nodedata

class NodeData:
    def __init__(self, lineno: int):
        self.lineno = lineno

class NodeBody(Node):
    def __repr__(self):
        return repr(self.children)
    
    def __str__(self):
        if not self.children:
            return ""
        return "\n".join(map(str, self.children))

class Assign(Node):
    def __init__(self, target: Node, value: Node, *, nodedata: NodeData):
        super().__init__([target, value], nodedata=nodedata)

        self.target = target
        self.value = value

    def __str__(self):
        return f"{self.target} = {self.value}"

class Declare(Node):
    def __init__(self, target: Node, kind: str, value: Node, *, nodedata: NodeData):
        super().__init__([target, value], nodedata=nodedata)

        self.target = target
        self.value = value

        self.kind = kind

    def __str__(self):
        if isinstance(self.value, Empty):
            return f"{self.kind} {self.target}"
        return f"{self.kind} {self.target} = {self.value}"

class Struct(Node):
    def __init__(self, name: str, body: NodeBody, *, nodedata: NodeData):
        super().__init__([body], nodedata=nodedata)
        self.name = name
        self.body = body
    
    def __str__(self):
        body = indent_text(str(self.body))
        return f"struct {self.name} {{\n{body}\n}}"

class Empty(Node):
    def __init__(self, *, nodedata: NodeData):
        super().__init__([], nodedata=nodedata)

    def __str__(self):
        return ""

class Call(Node):
    def __init__(self, func: Node, args: Arguments, *, nodedata: NodeData):
        super().__init__([func, args], nodedata=nodedata)
        self.func = func
        self.args = args

    def __repr__(self):
        return f"Call({self.func!r}, {self.args!r})"

    def __str__(self):
        return f"{self.func}{self.args}"

class Arguments(Node):
    def __init__(self, args: list[Node], *, nodedata: NodeData):
        super().__init__(args, nodedata=nodedata)
        self.args = args

    def __repr__(self):
        return f"Arguments({self.args!r})"

    def __str__(self):
        return f"({', '.join(map(str, self.args))})"

class Constant(Node):
    def __init__(self, value: str, *, nodedata: NodeData):
        super().__init__([], nodedata=nodedata)
        self.value = value

    def __str__(self):
        return f"{self.value}"

class FunctionDef(Node):
    def __init__(self, returnkind: str, name: Node, params: Arguments, body: list[Node], *, nodedata: NodeData):
        super().__init__(body + [name, params], nodedata=nodedata)
        self.returnkind = returnkind
        self.name = name
        self.params = params
        self.body = body

    def __str__(self):
        semilines = "\n".join(map(str, self.body))
        body = indent_text(semilines)
        return f"def {self.returnkind} {self.name}{self.params} {{\n{body}\n}}"

class List(Node):
    def __init__(self, elements: list[Node], *, nodedata: NodeData):
        super().__init__(elements, nodedata=nodedata)
        self.elements = elements
    
    def __str__(self):
        e = map(str, self.elements)
        i = ", ".join(e)
        return f"[{i}]"

class String(Node):
    def __init__(self, string: str, *, nodedata: NodeData):
        super().__init__([], nodedata=nodedata)
        self.string = string
    
    def __str__(self):
        return self.string

class If(Node):
    def __init__(self, condition: Node, body: list[Node], *, nodedata: NodeData):
        super().__init__(body + [condition], nodedata=nodedata)
        self.condition = condition
        self.body = body

    def __str__(self):
        semilines = "\n".join(map(str, self.body))
        body = indent_text(semilines)
        return f"if ({self.condition}) {{\n{body}\n}}"

class ForLoop(Node):
    def __init__(self, condition: Node, body: list[Node], *, nodedata: NodeData):
        super().__init__(body + [condition], nodedata=nodedata)
        self.condition = condition
        self.body = body

    def __str__(self):
        semilines = "\n".join(map(str, self.body))
        body = indent_text(semilines)
        return f"for ({self.condition}) {{\n{body}\n}}"

class In(Node):
    def __init__(self, name: Node, target: Node, *, nodedata: NodeData):
        super().__init__([name, target], nodedata=nodedata)
        self.name = name
        self.target = target
    
    def __str__(self):
        return f"{self.name} in {self.target}"

class Attribute(Node):
    def __init__(self, target: Node, attr: Node, *, nodedata: NodeData):
        super().__init__([target, attr], nodedata=nodedata)
        self.target = target
        self.attr = attr

    def __repr__(self):
        return f"Attribute({self.target!r}, {self.attr!r}, nodedata={self.data!r})"

    def __str__(self):
        return f"{self.target}.{self.attr}"

class Name(Node):
    def __init__(self, target: str, *, nodedata: NodeData):
        super().__init__([], nodedata=nodedata)
        self.target = target

    def __repr__(self):
        return f"Name({self.target!r}, nodedata={self.data!r})"

    def __str__(self):
        return f"{self.target}"

class Variable(Node):
    def __init__(self, target: str, *, nodedata: NodeData):
        super().__init__([], nodedata=nodedata)
        self.target = target

    def __repr__(self):
        return f"Variable({self.target!r}, nodedata={self.data!r})"

    def __str__(self):
        return f"{self.target}"

class Return(Node):
    def __init__(self, value: Node, *, nodedata: NodeData):
        super().__init__([value], nodedata=nodedata)
        self.value = value

    def __str__(self):
        return f"return {self.value}"

class BinOp(Node):
    def __init__(self, left: Node, op: str, right: Node, *, nodedata: NodeData):
        super().__init__([left, right], nodedata=nodedata)
        self.left = left
        self.op = op
        self.right = right
    
    def __str__(self):
        return f"{self.left} {self.op} {self.right}"

class Include(Node):
    def __init__(self, path: str, *, nodedata: NodeData):
        super().__init__([], nodedata=nodedata)
        self.path = path
    
    def __str__(self):
        return f"#include <{self.path}>"

class Template(Node):
    def __init__(self, names: list[str], *, nodedata: NodeData):
        super().__init__([], nodedata=nodedata)
        self.names = names
    
    def __str__(self):
        return f"template <{', '.join(self.names)}>"

def indent_text(text: str, levels: int = 1):
    indention = "    " * levels
    lines = text.split("\n")
    newlines = []
    for line in lines:
        newlines.append(f"{indention}{line}")
    return "\n".join(newlines)