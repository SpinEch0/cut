import cfile
from pycparser import c_ast, c_generator
from typing import Dict, List
import hashlib


def create_int_decl(name):
    ty = c_ast.TypeDecl(declname=name, quals=[], align=None, type=c_ast.IdentifierType(names=["int"]))
    return c_ast.Decl(
        name=name,
        quals=[],
        align=[],
        storage=[],
        funcspec=[],
        type=ty,
        init=c_ast.Constant(type="int", value="0"),
        bitsize=None,
    )


def create_var_decl(name, type_str):
    ty = c_ast.TypeDecl(declname=name, quals=[], align=None, type=c_ast.IdentifierType(names=[type_str]))
    return c_ast.Decl(name=name, quals=[], align=[], storage=[], funcspec=[], type=ty, init=None, bitsize=None)


def create_loop_cond(name, value):
    return c_ast.BinaryOp(op="<", left=c_ast.ID(name), right=c_ast.Constant(type="int", value=value))


def reverse_lookup(d, v):
    for k in d:
        if d[k] == v:
            return k
    return None


def rfind_nth_char(string: str, n: int, c: str):
    loc = string.rfind(c)
    if n == 1:
        return loc
    else:
        while n > 1 and loc != -1:
            loc = string.rfind(c, 0, loc - 1)
            n = n - 1
    return loc


def rewriteCase(case: dict, knowlege) -> None:
    model_params = case["parameters"]
    model_str = case["model"]
    model_str = model_str.replace("#x", "0x")
    model_str = model_str.split("\n")
    value_dict = {}
    call_names = {}
    call_values = {}
    type_dict = case["types"]
    for item in model_str:
        item = item.split("->")
        if len(item) > 1:
            value_dict[item[0].strip(" ")] = item[1].strip(" ")
    for (a, b) in list(model_params.items()):
        if b.startswith("__builtin"):
            if a in model_params.keys():
                model_params.pop(a)
            if a in value_dict.keys():
                value_dict.pop(a)
            if a in type_dict.keys():
                type_dict.pop(a)

    for (a, b) in list(model_params.items()):
        if a.startswith("conj_$") and b in knowlege._funcs.keys():
            if a in model_params.keys():
                call_names[a] = model_params[a]
                model_params.pop(a)
            if a in value_dict.keys():
                call_values[a] = value_dict[a]
                value_dict.pop(a)
    ret = {}
    ret["parameters"] = model_params
    ret["values"] = value_dict
    ret["types"] = type_dict
    ret["call_names"] = call_names
    ret["call_values"] = call_values
    # print(ret)
    return ret


def is_ref(sym_name, pure_name):
    loc = sym_name.find("[")
    if loc != -1:
        sym_name = sym_name[:loc]
    loc = sym_name.find(")")
    if loc != -1:
        sym_name = sym_name[loc + 1 :]
    sym_name = sym_name.strip(" )")
    return sym_name == pure_name


# global var, casehash
case_hash = {}


class TestCase:
    def __init__(self, name, case_desc, knowlege) -> None:
        self._func_name = name
        self._case_desc = rewriteCase(case_desc, knowlege)
        self._case_desc["size_hint"] = {}
        self._case_desc["asts"] = {}

        self._duplicated = False
        self._knowlege = knowlege
        self._candidate_type = {}
        hash_str = name + str(self._case_desc["values"])
        sha = hashlib.sha256(bytes(hash_str, "utf-8"))
        case_num = len(case_hash)
        if sha in case_hash.keys():
            self._duplicated = True
        else:
            case_hash[sha] = case_num + 1
        self._case_id = case_num + 1
        self._compound_stmt = c_ast.Compound([])

    def real_type(self, orig: str) -> str:
        orig_type = orig.strip(" *")
        strip = orig[len(orig_type) :]
        real_type = self._knowlege.get_typedef_type(orig_type)
        while real_type:
            orig_type = real_type
            real_type = self._knowlege.get_typedef_type(orig_type)
        return orig_type + strip

    def get_ref_max_index(self, sym_name, ref_level):
        max_index = 1
        if ref_level == 0:
            id_name = reverse_lookup(self._case_desc["parameters"], sym_name)
            if self._case_desc["size_hint"].get(id_name):
                max_index = max(max_index, self._case_desc["size_hint"].get(id_name))
                return max_index
        loc = sym_name.find("[")
        if loc != -1:
            sym_name = sym_name[:loc]
        for key, value in self._case_desc["parameters"].items():
            if is_ref(value, sym_name) and value.count("[") == ref_level:
                index = self._case_desc["size_hint"].get(key)
                if index:
                    max_index = max(max_index, int(index))
        return max_index

    def generate_func(self):
        if self._duplicated:
            return None
        func_type = c_ast.TypeDecl(
            declname="test_" + self._func_name + "_" + str(self._case_id),
            quals=[],
            align=None,
            type=c_ast.IdentifierType(["void"]),
        )
        func_decl = c_ast.FuncDecl(args=None, type=func_type)

        func_name = c_ast.Decl(
            name=func_type.declname,
            quals=[],
            align=[],
            storage=[],
            funcspec=None,
            type=func_decl,
            init=None,
            bitsize=None,
        )
        # var decls
        func_args = self._knowlege.get_func_args(self._func_name)
        if func_args is None:
            print("error can not find")
            return None

        for name, ty in func_args.items():
            self._compound_stmt.block_items.append(create_var_decl(name, ty))

        for item in list(self._case_desc["parameters"].items()):
            ast = self.traverse_translation(item[1])
            self._case_desc["parameters"][item[0]] = c_generator.CGenerator().visit(ast)
            self._case_desc["asts"][item[0]] = ast

        # malloc
        asts = self.generate_memory()
        self._compound_stmt.block_items.extend(asts)

        # assign
        for item in list(self._case_desc["values"].items()):
            sym_name = self._case_desc["parameters"][item[0]]
            if not self._case_desc["types"][item[0]].endswith("*"):
                assign = c_ast.Assignment("=", c_ast.ID(sym_name), c_ast.Constant("string", item[1]))
                self._compound_stmt.block_items.append(assign)

        # call dut
        arg_expr = c_ast.ExprList([])
        for name, ty in func_args.items():
            arg_expr.exprs.append(c_ast.ID(name))
        call = c_ast.FuncCall(c_ast.ID(self._func_name), arg_expr)
        self._compound_stmt.block_items.append(call)
        call_free = c_ast.FuncCall(c_ast.ID("myfree"), None)
        self._compound_stmt.block_items.append(call_free)

        func_def = c_ast.FuncDef(decl=func_name, param_decls=None, body=self._compound_stmt)

        # print(c_generator.CGenerator().visit(self._compound_stmt))
        return c_generator.CGenerator().visit(func_def)

    def generate_malloc_call(self, type, count):
        size = c_ast.UnaryOp("sizeof", c_ast.ID(type))
        arg = c_ast.BinaryOp("*", size, c_ast.Constant("int", count))
        return c_ast.FuncCall(c_ast.ID("mymalloc"), arg)

    def generate_memory_ast(self, sym_name, ty, ptr_num, ref_level):
        asts = []
        max_index = self.get_ref_max_index(sym_name, ref_level)
        loc = rfind_nth_char(ty, ref_level + 1, "*")
        if loc == -1:
            print("error!!!!!!!!!!!!")
            return None
        type = ty[: loc - 1]
        if ref_level == 0:
            assign = c_ast.Assignment("=", c_ast.ID(sym_name), self.generate_malloc_call(type, max_index))
            asts.append(assign)
            ast = None
            if ref_level + 1 < ptr_num:
                ast = self.generate_memory_ast(sym_name, ty, ptr_num, ref_level + 1)
                asts.extend(ast)
            return asts
        else:
            loop_var = "cam_loop_" + str(ref_level)
            loop_sym = sym_name + "[" + loop_var + "]"

            ast = None
            if ref_level + 1 < ptr_num:
                ast = self.generate_memory_ast(loop_sym, ty, ptr_num, ref_level + 1)

            loop_array_ref = c_ast.ArrayRef(c_ast.ID(sym_name), subscript=c_ast.ID(loop_var))

            loop_assign = c_ast.Assignment("=", loop_array_ref, self.generate_malloc_call(type, max_index))
            compound = c_ast.Compound([loop_assign])
            if not ast:
                compound.block_items.append(ast)
            return [
                c_ast.For(
                    c_ast.DeclList([create_int_decl(loop_var)]),
                    create_loop_cond(loop_var, max_index),
                    c_ast.UnaryOp(op="p++", expr=c_ast.ID(loop_var)),
                    compound,
                )
            ]

    def generate_memory(self):
        memory_asts = []
        for arg, argt in self._case_desc["types"].items():
            if argt.endswith("*"):
                sym_name = self._case_desc["parameters"][arg]
                if not sym_name.endswith("]"):
                    ptr_num = argt.count("*")
                    asts = self.generate_memory_ast(sym_name, argt, ptr_num, 0)
                    memory_asts.extend(asts)
        return memory_asts

    # ugly code, LR parser?
    def traverse_translation(self, param):
        if param.startswith("Element{"):
            if param[-1] == "}":
                param = param[8:-1]
                loc1 = param.rfind(",")
                type = param[loc1 + 1 :]
                loc2 = param.rfind(",", 0, loc1)

                value = param[loc2 + 1 : loc1].split(" ")[0]

                sym = self.traverse_translation(param[:loc2])
                sym_str = c_generator.CGenerator().visit(sym)
                key = reverse_lookup(self._case_desc["parameters"], sym_str)
                parent_type = "unkown"
                if key in self._case_desc["types"]:
                    parent_type = self._case_desc["types"][key]

                # void vs real type
                # fixme
                if "void" in self.real_type(parent_type):
                    parent_type = type + " *"
                    self._case_desc["types"][key] = parent_type
                    ty = c_ast.TypeDecl(None, [], None, type=c_ast.IdentifierType([parent_type]))
                    ast_type = c_ast.Typename(None, [], None, ty)
                    sym = c_ast.Cast(ast_type, sym)

                # container_of fixme

                size = int(value) + 1
                if key in self._case_desc["size_hint"].keys():
                    self._case_desc["size_hint"][key] = max(self._case_desc["size_hint"][key], size)
                else:
                    self._case_desc["size_hint"][key] = size

                return c_ast.ArrayRef(name=sym, subscript=c_ast.Constant("int", value))

            else:
                loc = param.rfind(".")
                name = param[loc + 1 :]
                param = param[8 : loc - 1]

                loc1 = param.rfind(",")
                type = param[loc1 + 1 :]
                loc2 = param.rfind(",", 0, loc1)

                value = param[loc2 + 1 : loc1].split(" ")[0]

                sym = self.traverse_translation(param[:loc2])
                sym_str = c_generator.CGenerator().visit(sym)
                key = reverse_lookup(self._case_desc["parameters"], sym_str)
                parent_type = "unkown"
                if key in self._case_desc["types"]:
                    parent_type = self._case_desc["types"][key]

                if "void" in self.real_type(parent_type):
                    parent_type = type + " *"
                    self._case_desc["types"][key] = parent_type
                    ty = c_ast.TypeDecl(None, [], None, type=c_ast.IdentifierType([parent_type]))
                    ast_type = c_ast.Typename(None, [], None, ty)
                    sym = c_ast.Cast(ast_type, sym)

                size = int(value) + 1
                if key in self._case_desc["size_hint"].keys():
                    self._case_desc["size_hint"][key] = max(self._case_desc["size_hint"][key], size)
                else:
                    self._case_desc["size_hint"][key] = size

                arr_ref = c_ast.ArrayRef(name=sym, subscript=c_ast.Constant("int", value))
                # parent_type = self._case_desc["types"][key]
                link = "."
                if "*" in type:
                    link = "->"  # fixme bug here todo
                return c_ast.StructRef(name=arr_ref, type=link, field=c_ast.ID(name))  # ->

        elif param.startswith("SymRegion{"):
            if param[-1] == "}":
                elements = param[10:-1]
                return self.traverse_translation(elements)
            else:
                loc = param.rfind(".")
                name = param[loc + 1 :]
                param = param[10 : loc - 1]  # skip }
                sym = self.traverse_translation(param)

                sym_str = c_generator.CGenerator().visit(sym)
                key = reverse_lookup(self._case_desc["parameters"], sym_str)
                parent_type = "unkown"
                if key in self._case_desc["types"]:
                    parent_type = self._case_desc["types"][key]
                link = "."
                if "*" in parent_type:
                    link = "->"  # fixme
                return c_ast.StructRef(name=sym, type=link, field=c_ast.ID(name))

        elif param.startswith("reg_$"):
            if param.endswith(">"):
                loc = param.find("<")
                id_name = param[:loc]
                param = param[loc + 1 : -1]
                loc = param.find(",")
                type = param[:loc]
                # print("symname", sym_name)
                # print("type", type)
                # print("param", param)
                # print("traverse", param[loc+1:])
                # print("traverse ", param[loc + 1 :])
                sym = self.traverse_translation(param[loc + 1 :])
                self._case_desc["parameters"][id_name] = c_generator.CGenerator().visit(sym)
                self._case_desc["asts"][id_name] = sym
                self._case_desc["types"][id_name] = self.real_type(type)
                return sym
            else:  # end
                return c_ast.ID(param)
        elif param.startswith("conj_$"):
            return c_ast.ID(param)  # lookup
        else:
            return c_ast.ID(param)


if __name__ == "__main__":
    import json
    from cut import knowlege

    # case_desc = json.load(open("test.json"))
    case_desc = json.load(open("test.c_hehe.json"))
    knowledge_base = knowlege.KnowlegeBase("codechecker_commands.json")
    for case in case_desc:
        test_case = TestCase("hehe", case, knowledge_base)
        test_case.generate_func()
