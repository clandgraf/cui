
from cui_emacs.util import LispException

def advance_index(string, idx):
    idx += 1
    if idx >= len(string):
        raise LispException('Unexpected end of input')
    return idx

def skip_whitespace(string, idx):
    while idx < len(string) and string[idx] == ' ':
        idx += 1
    return idx

escape_table = {
    '\\': '\\',
    'n':  '\n',
    't':  '\t',
    '"':  '"',
    'r':  ''
}

def parse_string(string, idx):
    parsed_str = ''
    while True:
        if string[idx] == '"':
            return parsed_str, idx + 1
        elif string[idx] == '\\':
            idx = advance_index(string, idx)
            unescaped = escape_table.get(string[idx])
            if unescaped is None:
                raise LispException('Unknown escape sequence %s' % chr(string[idx]))
            parsed_str += unescaped
        else:
             parsed_str += string[idx]
        idx = advance_index(string, idx)

def parse_number(string, idx):
    number = 0
    while True:
        if not string[idx].isdigit():
            return number, idx

        number = number * 10 + int(string[idx])
        advance_index(string, idx)

def parse_list(string, idx):
    lst = []
    while idx < len(string):
        idx = skip_whitespace(string, idx)
        if string[idx] == ')':
            return lst, idx + 1
        obj, idx = parse_expression(string, idx)
        lst.append(obj)
    raise LispException('End of input while parsing list')

def parse_expression(string, idx=0):
    idx = skip_whitespace(string, idx)
    if string[idx] == '(':
        return parse_list(string, idx + 1)
    elif string[idx] == '"':
        return parse_string(string, idx + 1)
    elif string[idx].isdigit():
        return parse_number(string, idx + 1)
    else:
        raise LispException('Unexpected token: %s (%s)' % (string[idx], idx))

def parse_return_value(string):
    obj, idx = parse_expression(string)
    idx = skip_whitespace(string, idx)
    if idx != len(string):
        raise LispException('Not all input consumed')
    return obj
