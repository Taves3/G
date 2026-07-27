from ..executors import gmist
from ..parsers import gsile

def run(code: str, cwd: str) -> tuple[int, gmist.Interpreter]:
    parsed = gsile.parse(code)
    interpreter = gmist.Interpreter(cwd, gsile.parse)
    code = interpreter.interpret(parsed)
    return code, interpreter