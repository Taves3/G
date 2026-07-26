from __future__ import annotations

from .datatypes import *
from nodesets.gsilenodes import *
import traceback
import os

# There desperately needs to be an interpreter error system, along with a error system in GScript. Just take after HotScript.

class Interpreter:
    def __init__(self, cwd: str | None = None, parser: typing.Callable[[str], NodeBody] | None = None):
        self.framestack: list[Frame] = []
        self.cwd: str = cwd or ""
        self.parser = parser
    
    @property
    def frame(self):
        return self.framestack[-1]

    @property
    def moduleframe(self):
        return self.framestack[0]

    def read_variable(self, name: str, do_error: bool = True):
        for frame in self.framestack[::-1]:
            if name in frame.locals:
                return frame.locals[name]
            
        if do_error:
            raise LookupError(f"Can't find variable {name}")

        return None

    def read_kind(self, name: str, do_error: bool = True):
        for frame in self.framestack[::-1]:
            if name in frame.var_kinds:
                return frame.var_kinds[name]
            
        if do_error:
            raise LookupError(f"Can't find variable kind {name}")

        return None

    def convert(self, value: str) -> ObjectType:
        if "." in value:
            return Float(value)
        return Integer(value)

    def add_frame(self):
        self.framestack.append(Frame())
    
    def pop_frame(self):
        return self.framestack.pop()

    def run_func(self, func: FunctionType, args: list):
        return func.call(self, args)

    def run_attribute(self, target: BaseType, attribute: str, args: list):
        return self.run_func(target.get_attribute(attribute, self), args)

    def interpret(self, nodebody: NodeBody, frame: Frame | None = None, pop_frame: bool = False):
        if not frame:
            self.add_frame()
        else:
            self.framestack.append(frame)

        self.frame.locals["console"] = ConsoleType(self.frame)
        self.frame.locals["print"] = BuiltInFunction("print", built_in_print)
        self.frame.locals["set_attribute"] = BuiltInFunction("set_attribute", built_in_set_attribute)
        self.frame.locals["get_attribute"] = BuiltInFunction("get_attribute", built_in_get_attribute)

        for node in nodebody.children:
            try:
                self.visit(node)
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                print(f"Exception on line {node.data.lineno + 1}: {e}")
                return 1
        
        if pop_frame:
            self.pop_frame()
            
        return 0

    def visit(self, node: Node):
        methodname = f"visit_{node.__class__.__name__}"
        method = getattr(self, methodname)
        return method(node)
    
    def visit_Include(self, node: Include):
        path = node.path
        if not os.path.isabs(path):
            # This isn't great for platform compatibillity but that can be fixed later.
            path = f"{self.cwd}/{path}"
        # This ignores path operators like "../a/b"
        # But they shouldn't be too difficult.
        # This also doesn't check whether the path even exists.

        with open(path, "r") as file:
            source = file.read()

        parsed = self.parser(source)
        
        child = Interpreter(cwd=self.cwd)
        exit_code = child.interpret(parsed)

        # ^ This entire portion needs to be error checked at runtime

        for name, value in child.moduleframe.locals.items():
            if name in self.moduleframe.locals:
                continue
            self.moduleframe.locals[name] = value

        for name, kind in child.moduleframe.var_kinds.items():
            if name in self.moduleframe.var_kinds:
                continue
            self.moduleframe.var_kinds[name] = kind
        
        self.moduleframe.modifier_stack = [*child.moduleframe.modifier_stack, *self.moduleframe.modifier_stack]

    def visit_Template(self, node: Template):
        self.frame.modifier_stack.append(TemplateMod(node.names))

    def visit_Attribute(self, node: Attribute):
        target = self.visit(node.target)
        attr = self.visit(node.attr)

        getter = target.get_attribute("__get_attribute__", self)
        return self.run_func(getter, [attr])

    def visit_Struct(self, node: Struct):
        self.frame.locals[node.name] = StructType(node)
        # screw inheritance, that should be done with... you guessed it, a library!
        # maybe i should do that.

    def visit_Assign(self, node: Assign):
        bv = self.visit(node.value)
        if isinstance(node.target, Attribute):
            target = self.visit(node.target.target)
            attr = self.visit(node.target.attr)
            setter = target.get_attribute("__set_attribute__", self)
            return self.run_func(setter, [attr, bv])
            # It's somewhat hacky but it is better than nothing.

        target = self.visit(node.target)
        declared = self.read_kind(target)

        if isinstance(bv, Float):
            value = bv
            if declared != "float":
                raise TypeError(f"Mismatched type {target}")
        elif isinstance(bv, Integer):
            value = bv
            if declared != "int":
                raise TypeError(f"Mismatched type {target}")
        else:
            match declared:
                case "float":
                    value = Float(bv)
                case "int":
                    value = Integer(bv)
                case _:
                    raise RuntimeError(f"Unknown Type {declared!r}")

        self.frame.locals[target] = value

    def visit_Declare(self, node: Declare):
        target = self.visit(node.target)
        # this should always be a name node, you can't really declare an attribute.

        self.frame.var_kinds[target] = node.kind

        if node.value == None:
            self.frame.locals[target] = NullType()
            return
        
        bv = self.visit(node.value)

        if isinstance(bv, Float):
            value = bv
        elif isinstance(bv, Integer):
            value = bv
        elif isinstance(bv, StringType):
            value = bv

        else:
            match node.kind:
                case "float":
                    value = Float(bv)
                case "int":
                    value = Integer(bv)
                case "string":
                    value = StringType(bv)
                case "function":
                    value = bv
                case _:
                    if self.read_variable(node.kind, do_error=False) != None:
                        value = bv
                    else:
                        raise RuntimeError(f"Unknown Type {node.kind!r}")

        self.frame.locals[target] = value

    def visit_String(self, node: String):
        return StringType(node.string)

    def visit_Name(self, node: Name):
        return node.target

    def visit_Variable(self, node: Variable):
        return self.read_variable(node.target)

    def visit_Constant(self, node: Constant):
        return self.convert(node.value)
    
    def visit_FunctionDef(self, node: FunctionDef):
        name = self.visit(node.name)
        func = ClientFunction(node, name, self.frame.modifier_stack, self.frame)

        self.frame.locals[name] = func
        self.frame.var_kinds[name] = FunctionType
        self.frame.modifier_stack.clear()

    def visit_BinOp(self, node: BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(left, str):
            left = self.convert(left)

        if isinstance(right, str):
            right = self.convert(right)

        # This needs to also just check whether left has the attribute, otherwise, check the right for the "r*" equivalent
        return self.run_func(left.get_attribute(node.op, self), [right])
    
    def visit_Call(self, node: Call):
        args = [self.visit(arg) for arg in node.args.args]
        func = self.visit(node.func)

        return self.run_func(func, args)
    
    def visit_Return(self, node: Return):
        raise ReturnSignal(self.visit(node.value))

    def visit_ForLoop(self, node: ForLoop):
        if isinstance(node.condition, In):
            target = self.visit(node.condition.target)
            name = self.visit(node.condition.name)

            iterator = self.run_attribute(target, "__iterate__", [])
            while self.run_attribute(iterator, "__bool__", []).value:
                self.frame.locals[name] = self.run_attribute(iterator, "__next__", [])
                for stmt in node.body:
                    self.visit(stmt)
        
    def visit_If(self, node: If):
        condition = self.visit(node.condition)
        
        if self.run_func(condition.get_attribute("truthy"), []).value:
            for stmt in node.body:
                self.visit(stmt)

def built_in_print(interpreter: Interpreter, args: list):
    log_func = interpreter.read_variable("console").get_attribute("log", interpreter)
    return interpreter.run_func(log_func, args)

def built_in_set_attribute(interpreter: Interpreter, args: list):
    this, name, value = args
    return this.set_attribute(name, value, interpreter)

def built_in_get_attribute(interpreter: Interpreter, args: list):
    this, name = args
    return this.get_attribute(name, interpreter)