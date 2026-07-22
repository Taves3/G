from gnodes import *

class IRGenerator:
    #def __init__(self):
    #    self.encoding: dict[str, str] = {
    #        "assign" : "\x00",
    #        "declare": "\x01",
    #        "def"    : "\x02",
    #        "if"     : "\x03",
    #        "return" : "\x04",
    #        "call"   : "\x05",
    #        "forloop": "\x06",
    #    }
    def make(self, node: Node) -> str:
        methodname = f"make_{node.__class__.__name__}"
        method = getattr(self, methodname)
        return method(node)
    
    def make_NodeBody(self, node: NodeBody):
        body = f"{'|'.join([self.make(n) for n in node.children])}"
        return f"(module:(body:{body}))"
    
    def make_Declare(self, node: Declare):
        return f"(declare:(target:(raw:{self.make(node.target)}))|(kind:(raw:{node.kind}))|(value:{self.make(node.value)}))"

    def make_Name(self, node: Name):
        return node.target
    
    def make_List(self, node: List):
        l = "|".join([f"({i}:{self.make(element)})" for i, element in enumerate(node.elements)])
        return f"(list:{l})"
    
    def make_Constant(self, node: Constant):
        return f"(raw:{node.value})"

    def make_BinOp(self, node: BinOp):
        return f"(binop:(left:{self.make(node.left)})|(op:(raw:{node.op}))|(right:{self.make(node.right)}))"
    
    def make_FunctionDef(self, node: FunctionDef):
        body = f"{'|'.join([self.make(n) for n in node.body])}"
        return f"(def:(name:(raw:{self.make(node.name)}))|(rkind:(raw:{node.returnkind}))|(params:{self.make(node.params)})|(body:{body}))"

    def make_If(self, node: If):
        body = f"{'|'.join([self.make(n) for n in node.body])}"
        return f"(if:(condition:{self.make(node.condition)})|(body:{body}))"
    
    def make_Return(self, node: Return):
        return f"(return:(value:{self.make(node.value)}))"
    
    def make_Variable(self, node: Variable):
        return f"(var:(target:(raw:{node.target})))"

    def make_Call(self, node: Call):
        return f"(call:(func:{self.make(node.func)})|(args:{self.make(node.args)}))"
    
    def make_Arguments(self, node: Arguments):
        l = "|".join([f"({i}:{self.make(element)})" for i, element in enumerate(node.args)])
        return f"(arguments:(args:{l}))"
    
    def make_Attribute(self, node: Attribute):
        return f"(attribute:(target:{self.make(node.target)})|(attr:{self.make(node.attr)}))"
    
    def make_Empty(self, node: Empty):
        return ""
    
    def make_ForLoop(self, node: ForLoop):
        body = f"{'|'.join([self.make(n) for n in node.body])}"
        return f"(forloop:(condition:{self.make(node.condition)})|(body:{body}))"
    
    def make_Assign(self, node: Assign):
        return f"(assign:(name:(raw:{self.make(node.target)}))|(value:{self.make(node.value)}))"

    def make_In(self, node: In):
        return f"(in:(name:(raw:{self.make(node.name)}))|(target:(raw:{self.make(node.target)})))"

def make_ir(node: Node, pretty: bool = False):
    generator = IRGenerator()
    ir = generator.make(node)
    if not pretty:
        return ir
    
    lined = ""
    for char in ir:
        if char == ":":
            lined += char
            lined += "\n"
            continue
        if char == ")":
            lined += "\n"
        elif char == "|":
            lined += " | "
            continue
        lined += char
    
    prettified = ""
    indent = 0

    next_char = ""
    
    for i, char in enumerate(lined):
        if i + 1 < len(lined):
            next_char = lined[i + 1]

        if char == "(":
            indent += 1
        elif char == ")":
            indent -= 1
        elif char == "\n":
            if next_char == ")":
                i = "  " * (indent - 1) if (indent - 1) > 0 else ""
                prettified += f"\n{i}"
            else:
                i = "  " * indent if indent > 0 else ""
                prettified += f"\n{i}"
            continue
        prettified += char
    return prettified