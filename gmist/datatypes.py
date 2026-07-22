from __future__ import annotations

from .returnsignal import ReturnSignal
from gnodes import *
import typing

if typing.TYPE_CHECKING:
    from .interpreter import Interpreter

class Frame:
    def __init__(self):
        self.locals: dict[str, typing.Any] = {}
        self.var_kinds: dict[str, str] = {}
        self.modifier_stack: list[Node] = []

class BaseType:
    def __init__(self, frame: Frame | dict[str, BaseType]):
        if isinstance(frame, Frame):
            self.frame = frame
        else:
            self.frame = Frame()
            self.frame.locals = frame
    
        self.base_attribute("this", self)
        # Types need to have these functions
        # but the function type inherits the base type
        # which means that the function type uses function types
        # which is the problem.

        # Why does the base type need the function type?
        # Make this use attributes, like the legacy system
        # Wait, this already uses attributes, thats the frame
        # so what now?
        # I need functions to be introspectable,
        # but to introspect, they must be an object
        # but object's already use this, for a BASE IMPLEMENTATION
        # I need to get rid of the base implementation and put it somewhere else.
        # No because the interpreter always expects some attributes including "__get_attribute__" and "__set_attribute__" to both exist and be callable.
        # So do I just leave these attributes to be implemented by the classes inheriting this?
        # I guess so, if something goes wrong it isn't the end of the world.

        # Also not like this is going to be used, this is a base class.

    def get_attribute(self, name: str, interpreter: Interpreter):
        return self.frame.locals[name]

    def set_attribute(self, name: str, value: BaseType, interpreter: Interpreter):
        self.frame.locals[name] = value
        return NullType()

    def base_attribute(self, name: str, value: BaseType):
        if name not in self.frame.locals:
            self.frame.locals[name] = value

class ObjectType(BaseType):
    def __init__(self, frame: Frame | dict[str, BaseType], string: StringType | None = None):
        super().__init__(frame)
        self._string = string
        self.base_attribute("__string__"       , BuiltInFunction("__string__"       , self._default__string__       ))
        self.base_attribute("constructor"      , BuiltInFunction("constructor"      , self._default_constructor     ))
        self.base_attribute("__get_attribute__", BuiltInFunction("__get_attribute__", self._default__get_attribute__))
        self.base_attribute("__set_attribute__", BuiltInFunction("__set_attribute__", self._default__set_attribute__))

    def _default_constructor(self, interpreter: Interpreter, args: list):
        return NullType()

    def _default__get_attribute__(self, interpreter: Interpreter, args: list):
        return self.get_attribute(args[0], interpreter)

    def _default__set_attribute__(self, interpreter: Interpreter, args: list):
        return self.set_attribute(args[0], args[1], interpreter)

    def _default__string__(self, interpreter: Interpreter, args: list):
        return self._string or StringType("<Object>")

class FunctionType(BaseType):
    def call(self, interpreter: Interpreter, args: list) -> ObjectType: ...

class ClientFunction(FunctionType):
    def __init__(self, func: FunctionDef, name: str, modifiers: list[Modifier], frame: Frame):
        super().__init__({"name": StringType(name), "invoke": self})
        self.func = func
        self.name = name
        self.mods = modifiers
        self.frame = frame

    def _string(self, interpreter: Interpreter, args: list):
        return StringType(f"<Client Function {self.name!r}>")

    def _default__get_attribute__(self, interpreter: Interpreter, args: list):
        return self.get_attribute(args[0])

    def _default__set_attribute__(self, interpreter: Interpreter, args: list):
        return self.set_attribute(args[0], args[1])
    
    def call(self, interpreter: Interpreter, args: list):
        added_frame = False
        if self.frame != interpreter.frame:
            interpreter.framestack.append(self.frame)
            added_frame = True

        interpreter.add_frame()
        for param, arg in zip(self.func.params.args, args):
            kind, name = interpreter.visit(param).split(" ")
            interpreter.frame.locals[name] = arg
        
        output = NullType()
        try:
            for stmt in self.func.body:
                interpreter.visit(stmt)
        except ReturnSignal as signal:
            output = signal.value
        
        if not is_allowed(output):
            raise RuntimeError(f"{output} Is not allowed within simulation")
        
        interpreter.pop_frame()
        if added_frame:
            interpreter.pop_frame()
        return output

    def get_attribute(self, name: str, interpreter: Interpreter):
        match name:
            case "__string__":
                return BuiltInFunction("__string__", self._string)
            case "__get_attribute__":
                return BuiltInFunction("__get_attribute__", self._default__get_attribute__)
            case "__set_attribute__":
                return BuiltInFunction("__set_attribute__", self._default__set_attribute__)
        return self.frame.locals[name]

class BuiltInFunction(FunctionType):
    def __init__(
            self,
            name: str,
            implementation: typing.Callable[[Interpreter, list], typing.Any]
        ):
        super().__init__({"invoke": self})
        self.func = implementation
        self.name = name

    def _string(self, interpreter: Interpreter, args: list):
        return StringType(f"<Built-In Function {self.name!r}>")

    def _default__get_attribute__(self, interpreter: Interpreter, args: list):
        return self.get_attribute(args[0], interpreter)

    def _default__set_attribute__(self, interpreter: Interpreter, args: list):
        return self.set_attribute(args[0], args[1], interpreter)
    
    def call(self, interpreter: Interpreter, args: list):
        value = self.func(interpreter, args)
        if is_allowed(value):
            return value
        raise RuntimeError(f"{value} Is not allowed within simulation")

    def get_attribute(self, name: str, interpreter: Interpreter):
        if name not in self.frame.locals:
            match name:
                case "name":
                    self.frame.locals[name] = StringType(self.name)
                case "__string__":
                    self.frame.locals[name] = BuiltInFunction("__string__", self._string)
                case "__get_attribute__":
                    self.frame.locals[name] = BuiltInFunction("__get_attribute__", self._default__get_attribute__)
                case "__set_attribute__":
                    self.frame.locals[name] = BuiltInFunction("__set_attribute__", self._default__set_attribute__)
        return self.frame.locals[name]

class StructType(FunctionType):
    def __init__(self, struct: Struct):
        super().__init__(Frame())
        self.struct = struct

    def _string(self, interpreter: Interpreter, args: list):
        return StringType(f"<Struct {self.struct.name!r}>")

    def _default__get_attribute__(self, interpreter: Interpreter, args: list):
        return self.get_attribute(args[0], interpreter)

    def _default__set_attribute__(self, interpreter: Interpreter, args: list):
        return self.set_attribute(args[0], args[1], interpreter)
    
    def call(self, interpreter: Interpreter, args: list):
        interpreter.add_frame()

        for stmt in self.struct.body.children:
            interpreter.visit(stmt)
        
        instance = ObjectType(interpreter.pop_frame())
        interpreter.run_func(instance.get_attribute("constructor", interpreter), args)
        return instance

    def get_attribute(self, name: str, interpreter: Interpreter):
        if name not in self.frame.locals:
            match name:
                case "__string__":
                    self.frame.locals[name] = BuiltInFunction("__string__", self._string)
                case "__get_attribute__":
                    self.frame.locals[name] = BuiltInFunction("__get_attribute__", self._default__get_attribute__)
                case "__set_attribute__":
                    self.frame.locals[name] = BuiltInFunction("__set_attribute__", self._default__set_attribute__)
        return self.frame.locals[name]

class StringType(BaseType):
    def __init__(self, value: str):
        super().__init__(Frame())
        self.value = value

    def _string(self, interpreter: Interpreter, args: list):
        return self

    def _default__get_attribute__(self, interpreter: Interpreter, args: list):
        return self.get_attribute(args[0], interpreter)

    def _default__set_attribute__(self, interpreter: Interpreter, args: list):
        return self.set_attribute(args[0], args[1], interpreter)

    def get_attribute(self, name: str, interpreter: Interpreter):
        if name not in self.frame.locals:
            match name:
                case "__string__":
                    self.frame.locals[name] = BuiltInFunction("__string__", self._string)
                case "__get_attribute__":
                    self.frame.locals[name] = BuiltInFunction("__get_attribute__", self._default__get_attribute__)
                case "__set_attribute__":
                    self.frame.locals[name] = BuiltInFunction("__set_attribute__", self._default__set_attribute__)
        return self.frame.locals[name]

class NullType(ObjectType):
    def __init__(self):
        super().__init__({}, StringType("null"))

class ConsoleType(ObjectType):
    def __init__(self, frame: Frame):
        super().__init__(frame, StringType("<Console>"))
        self.base_attribute("log", BuiltInFunction("log", self.log))
        self.text = ""

    def log(self, interpreter: Interpreter, args: list):
        arg = args[0]
        self.text += f"{stringify(arg, interpreter)}\n"
        return NullType()

class Integer(ObjectType):
    def __init__(self, value: int):
        super().__init__({
            "+": BuiltInFunction("+", self.add),
            "-": BuiltInFunction("-", self.sub),

            "*": BuiltInFunction("*", self.mult),
            "**": BuiltInFunction("**", self.pow),
            "/": BuiltInFunction("/", self.div),

            "<": BuiltInFunction("<", self.lt),
            ">": BuiltInFunction(">", self.gt),
            "==": BuiltInFunction("==", self.eq),
            "!=": BuiltInFunction("!=", self.ne),
            "<=": BuiltInFunction("<=", self.lte),
            ">=": BuiltInFunction(">=", self.gte),

            "truthy": BuiltInFunction("truthy", self.truthy)
        }, StringType(f"{int(value)}"))
        self.value = int(value)
    
    def lt(self, interpreter: Interpreter, args: list):
        return Boolean(self.value < args[0].value)

    def gt(self, interpreter: Interpreter, args: list):
        return Boolean(self.value > args[0].value)

    def eq(self, interpreter: Interpreter, args: list):
        return Boolean(self.value == args[0].value)

    def ne(self, interpreter: Interpreter, args: list):
        return Boolean(self.value != args[0].value)

    def lte(self, interpreter: Interpreter, args: list):
        return Boolean(self.value <= args[0].value)

    def gte(self, interpreter: Interpreter, args: list):
        return Boolean(self.value >= args[0].value)

    def truthy(self, interpreter: Interpreter, args: list):
        return Boolean(self.value > 0)

    def add(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Integer(self.value + arg.value)

        if isinstance(arg, Float):
            return Integer(self.value + arg.value)

    def sub(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Integer(self.value - arg.value)

        if isinstance(arg, Float):
            return Integer(self.value - arg.value)
        
    def mult(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Integer(self.value * arg.value)
        
        if isinstance(arg, Float):
            return Integer(self.value * arg.value)

    def pow(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Integer(self.value ** arg.value)
        
        if isinstance(arg, Float):
            return Integer(self.value ** arg.value)

    def div(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Integer(self.value / arg.value)
        
        if isinstance(arg, Float):
            return Integer(self.value / arg.value)

class Float(ObjectType):
    def __init__(self, value: float):
        super().__init__({
            "+": BuiltInFunction("+", self.add),
            "-": BuiltInFunction("-", self.sub),

            "*": BuiltInFunction("*", self.mult),
            "**": BuiltInFunction("**", self.pow),
            "/": BuiltInFunction("/", self.div),

            "<": BuiltInFunction("<", self.lt),
            ">": BuiltInFunction(">", self.gt),
            "==": BuiltInFunction("==", self.eq),
            "!=": BuiltInFunction("!=", self.ne),
            "<=": BuiltInFunction("<=", self.lte),
            ">=": BuiltInFunction(">=", self.gte),

            "truthy": BuiltInFunction("truthy", self.truthy)
        }, StringType(f"{float(value)}"))
        self.value = float(value)
    
    def lt(self, interpreter: Interpreter, args: list):
        return Boolean(self.value < args[0].value)

    def gt(self, interpreter: Interpreter, args: list):
        return Boolean(self.value > args[0].value)

    def eq(self, interpreter: Interpreter, args: list):
        return Boolean(self.value == args[0].value)

    def ne(self, interpreter: Interpreter, args: list):
        return Boolean(self.value != args[0].value)

    def lte(self, interpreter: Interpreter, args: list):
        return Boolean(self.value <= args[0].value)

    def gte(self, interpreter: Interpreter, args: list):
        return Boolean(self.value >= args[0].value)

    def truthy(self, interpreter: Interpreter, args: list):
        return Boolean(self.value > 0)

    def add(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Float(self.value + arg.value)

        if isinstance(arg, Float):
            return Float(self.value + arg.value)

    def sub(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Float(self.value - arg.value)
        
        if isinstance(arg, Float):
            return Float(self.value - arg.value)
    
    def mult(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Float(self.value * arg.value)
        
        if isinstance(arg, Float):
            return Float(self.value * arg.value)

    def pow(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Float(self.value ** arg.value)
        
        if isinstance(arg, Float):
            return Float(self.value ** arg.value)

    def div(self, interpreter: Interpreter, args: list):
        arg = args[0]
        if isinstance(arg, Integer):
            return Float(self.value / arg.value)
        
        if isinstance(arg, Float):
            return Float(self.value / arg.value)

class ListType(ObjectType):
    def __init__(self, elements: list[ObjectType]):
        super().__init__({}, StringType(""))
        self.elements: list[ObjectType] = elements
    
    def get_attribute(self, name: str, interpreter: Interpreter):
        match name:
            case "length":
                return Integer(len(self.elements))
            case "string":
                strung = [stringify(element, interpreter) for element in self.elements]
                return StringType(f"[{', '.join(strung)}]")
            case "__iterate__":
                return BuiltInFunction("__iterate__", self.iterate)
    
    def iterate(self, interpreter: Interpreter, args: list):
        return self

class Boolean(ObjectType):
    def __init__(self, value: bool):
        super().__init__({
            "truthy": BuiltInFunction("truthy", self.truthy)
        }, StringType(f"{value}"))
        self.value = value
    
    def truthy(self, interpreter: Interpreter, args: list):
        return self

class Modifier: ...
class TemplateMod(Modifier):
    def __init__(self, names: str):
        self.names = names

def stringify(t: ObjectType, interpreter: Interpreter) -> str:
    return interpreter.run_func(t.get_attribute("__string__", interpreter), []).value

def is_allowed(value: BaseType | typing.Any) -> bool:
    base = value.__class__.__base__
    while True:
        if base == BaseType:
            return True
        if base == object:
            break
        base = base.__base__
    return False