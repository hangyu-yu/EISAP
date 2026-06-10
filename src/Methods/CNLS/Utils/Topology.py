# Circuit topology expression engine.
#
# Lets a circuit be described as an expression over element names using two
# operators, so arbitrary series/parallel nesting is possible on top of the
# existing (series-only) elements:
#   '+'   series      Z = sum(Z_i)
#   '//'  parallel    Z = 1 / sum(1 / Z_i)        ('//' binds tighter than '+')
#   ()    grouping
#
# Leaves are element names exactly as they appear in Circuit.Z columns, e.g.
#   "RQ1 + RC2"                two arcs in series (equivalent to the default)
#   "(RQ1 + RC2) // L1"        an RQ+RC block in parallel with an inductor
#
# When Circuit.topology is None/empty the circuit keeps its default behaviour
# (sum of all element columns), so existing circuits are unaffected.

from functools import lru_cache
import numpy as np

# AST nodes (hashable tuples so the parse result can be cached):
#   ('leaf', name)
#   ('series', (child, child, ...))
#   ('parallel', (child, child, ...))


def _tokenize(expr):
    tokens = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
        elif c == '(' or c == ')' or c == '+':
            tokens.append(c)
            i += 1
        elif c == '/':
            if i + 1 < n and expr[i + 1] == '/':
                tokens.append('//')
                i += 2
            else:
                raise ValueError("Use '//' for parallel connection, not a single '/'.")
        elif c.isalnum() or c == '_':
            j = i
            while j < n and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            tokens.append(expr[i:j])
            i = j
        else:
            raise ValueError(f"Unexpected character '{c}' in topology expression.")
    return tokens


@lru_cache(maxsize=128)
def parse_topology(expr):
    """Parse a topology string into a hashable AST. Raises ValueError on bad syntax."""
    tokens = _tokenize(expr)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def expr_rule():
        # series := term ('+' term)*
        nonlocal pos
        terms = [term_rule()]
        while peek() == '+':
            pos += 1
            terms.append(term_rule())
        return terms[0] if len(terms) == 1 else ('series', tuple(terms))

    def term_rule():
        # term := factor ('//' factor)*
        nonlocal pos
        factors = [factor_rule()]
        while peek() == '//':
            pos += 1
            factors.append(factor_rule())
        return factors[0] if len(factors) == 1 else ('parallel', tuple(factors))

    def factor_rule():
        # factor := IDENT | '(' expr ')'
        nonlocal pos
        tok = peek()
        if tok is None:
            raise ValueError("Unexpected end of topology expression.")
        if tok == '(':
            pos += 1
            node = expr_rule()
            if peek() != ')':
                raise ValueError("Missing closing ')' in topology expression.")
            pos += 1
            return node
        if tok in ('+', '//', ')'):
            raise ValueError(f"Unexpected '{tok}' in topology expression.")
        pos += 1
        return ('leaf', tok)

    node = expr_rule()
    if pos != len(tokens):
        raise ValueError(f"Unexpected token '{tokens[pos]}' in topology expression.")
    return node


def topology_names(ast):
    """Return the list of element names referenced by the AST, in order."""
    kind = ast[0]
    if kind == 'leaf':
        return [ast[1]]
    names = []
    for child in ast[1]:
        names.extend(topology_names(child))
    return names


def _eval(ast, z_dict):
    kind = ast[0]
    if kind == 'leaf':
        name = ast[1]
        if name not in z_dict:
            raise ValueError(f"Topology references unknown element '{name}'.")
        return z_dict[name]
    children = [_eval(c, z_dict) for c in ast[1]]
    if kind == 'series':
        return sum(children)
    # parallel
    return 1.0 / sum(1.0 / z for z in children)


def evaluate(expr, z_dict):
    """Evaluate a topology expression against a {name: complex array} mapping.

    Every element name in z_dict must be used exactly once, so the result is a
    complete partition of the circuit (no element silently dropped or reused).
    """
    ast = parse_topology(expr)
    used = topology_names(ast)
    used_set = set(used)
    if len(used) != len(used_set):
        dup = [n for n in used_set if used.count(n) > 1]
        raise ValueError(f"Element(s) used more than once in topology: {sorted(dup)}.")
    available = set(z_dict.keys())
    missing = used_set - available
    if missing:
        raise ValueError(f"Topology references unknown element(s): {sorted(missing)}.")
    unused = available - used_set
    if unused:
        raise ValueError(f"Element(s) not placed in topology: {sorted(unused)}.")
    return np.asarray(_eval(ast, z_dict))
