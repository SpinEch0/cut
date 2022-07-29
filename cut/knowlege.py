#!/usr/bin/env python

import json
from clang.cindex import CursorKind
from clang.cindex import Index

from cut import log_parser


def _get_binop_operator(cursor):
    """Returns the operator token of a binary operator cursor.

    :param cursor: A cursor of kind BINARY_OPERATOR.
    :return:       The token object containing the actual operator or None.
    """
    children = list(cursor.get_children())
    operator_min_begin = (children[0].location.line, children[0].location.column)
    operator_max_end = (children[1].location.line, children[1].location.column)

    for token in cursor.get_tokens():
        if operator_min_begin < (token.extent.start.line, token.extent.start.column) and operator_max_end >= (
            token.extent.end.line,
            token.extent.end.column,
        ):
            return token

    return None  # pragma: no cover


def get_info(node) -> tuple:
    funcs = {}
    variables = {}
    typedefs = {}
    structs = {}

    for child in node.get_children():
        if child.kind == CursorKind.FUNCTION_DECL:
            args = {}
            for grand_child in child.get_children():
                # print(grand_child.kind, grand_child.spelling)
                if grand_child.kind == CursorKind.PARM_DECL:
                    args[grand_child.spelling] = grand_child.type.spelling
            if funcs.get(child.spelling) is None:
                funcs[child.spelling] = args
            else:
                if funcs[child.spelling] != args:
                    print("func redefination need to do something more..., ", child.spelling)
                    print(funcs[child.spelling])
                    print(args)
        elif child.kind == CursorKind.VAR_DECL:
            if variables.get(child.spelling) is None:
                variables[child.spelling] = child.type.spelling
            else:
                print("vars redefination need to do something more...", child.spelling)
                print(child.type.spelling)
        elif child.kind == CursorKind.TYPEDEF_DECL:
            if typedefs.get(child.spelling) is None:
                typedefs[child.spelling] = child.underlying_typedef_type.spelling
            else:
                print("typedefs redefination need to do something more...", child.spelling)
                print(child.underlying_typedef_type.spelling)
        elif child.kind == CursorKind.STRUCT_DECL:
            spelling = child.spelling
            if spelling == "":
                print("struct spelling null, use type spelling???")
                spelling = child.type.spelling
            if structs.get(spelling) is None:
                structs[child.spelling] = []
                for grand_child in child.get_children():
                    structs[child.spelling].append((grand_child.spelling, grand_child.type.spelling))
    return (funcs, variables, typedefs, structs)


class KnowlegeBase:
    def __init__(self, jfile: str) -> None:
        self._jfile = jfile
        self._init = False
        self._funcs = {}
        self._vars = {}
        self._typedefs = {}
        self._structs = {}

        jdata = json.load(open(self._jfile))
        actions, _ = log_parser.parse_unique_log(jdata, ".", compile_uniqueing="strict")
        index = Index.create()
        for act in actions:
            # print(act.source, act.analyzer_options)
            tu = index.parse(act.source, act.analyzer_options)
            # print(tu.cursor.spelling)
            self._funcs, self._vars, self._typedefs, self._structs = get_info(tu.cursor)

    def get_func_args(self, name: str):
        return self._funcs.get(name)

    def get_var_type(self, name: str):
        return self._vars.get(name)

    def get_typedef_type(self, name: str):
        return self._typedefs.get(name)


# if __name__ == "__main__":
#     knowlege = KnowlegeBase("codechecker_commands.json")
