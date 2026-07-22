import typing

def parse_ir(ir: str) -> dict[str, typing.Any]:
    if ir[0] == "(" and ir[-1] == ")":
        ir = ir[1:-1]
        
    depth = 0
    recorded = ""

    split = ir.split(":", 1)
    name = split[0]

    if name == "raw":
        return {"raw": split[1]}

    fields = []
    textbody = split[1]
    
    if not textbody:
        return {name : fields}

    i = 0
    while i < len(textbody):
        char = textbody[i]
        if char == "(":
            depth += 1
            recorded += char

        elif char == ")":
            depth -= 1
            recorded += char

        else:
            if depth == 0:
                if char == "|":
                    fields.append(parse_ir(recorded))
                    recorded = ""
            else:
                recorded += char
        i += 1

    if recorded:
        fields.append(parse_ir(recorded))

    # raw, next question
    return {name : fields}

#print(parse_ir("(module:(body:(declare:(target:(raw:x))|(kind:(raw:int))|(value:(raw:5)))))"))