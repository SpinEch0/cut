#!/usr/bin/env python

#===- cindex-dump.py - cindex/Python Source Dump -------------*- python -*--===#
#
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
#===------------------------------------------------------------------------===#

"""
A simple command line tool for dumping a source file using the Clang Index
Library.
"""

from clang.cindex import Config
from clang.cindex import TypeKind
from clang.cindex import CursorKind
from clang.cindex import Index
import json
import os
import cfile

def get_diag_info(diag):
    return { 'severity' : diag.severity,
             'location' : diag.location,
             'spelling' : diag.spelling,
             'ranges' : diag.ranges,
             'fixits' : diag.fixits }

def get_cursor_id(cursor, cursor_list = []):
    if not opts.showIDs:
        return None

    if cursor is None:
        return None

    # FIXME: This is really slow. It would be nice if the index API exposed
    # something that let us hash cursors.
    for i,c in enumerate(cursor_list):
        if cursor == c:
            return i
    cursor_list.append(cursor)
    return len(cursor_list) - 1

def read_builtin_type(btype):
    #print("builtin type ", btype.spelling)
    return btype.spelling

def read_qualified_type(qtype):
    specifiers = ''
    while True:
        if qtype.is_const_qualified() and not specifiers.startswith(' const'):
            specifiers = ' const' + specifiers
        if qtype.is_volatile_qualified() and not specifiers.startswith(' volatile'):
            specifiers = ' volatile' + specifiers
        if qtype.kind is TypeKind.POINTER:
            specifiers = ' *' + specifiers
            qtype = qtype.get_pointee()
        elif qtype.kind is TypeKind.LVALUEREFERENCE:
            specifiers = ' &' + specifiers
            qtype = qtype.get_pointee()
        elif qtype.kind is TypeKind.RVALUEREFERENCE:
            specifiers = ' &&' + specifiers
            qtype = qtype.get_pointee()
        elif qtype.kind in [TypeKind.RECORD, TypeKind.TYPEDEF, TypeKind.ENUM, TypeKind.UNEXPOSED]:
            cursor = qtype.get_declaration()
            if cursor.kind is CursorKind.TYPEDEF_DECL:
                qtype = cursor.underlying_typedef_type
            else:
                specifiers = '::' + cursor.type.spelling
                if cursor.kind is CursorKind.ENUM_DECL:
                    specifiers = 'enum ' + spelling + specifiers
                elif cursor.kind is CursorKind.STRUCT_DECL:
                    specifiers = 'struct ' + spelling + specifiers
                elif cursor.kind is CursorKind.UNION_DECL:
                    specifiers = 'union ' + spelling + specifiers
                elif cursor.kind is CursorKind.CLASS_DECL:
                    specifiers = 'class ' + spelling + specifiers
                break
        else:
            specifiers = read_builtin_type(qtype) + specifiers
            return specifiers
    return specifiers
    

def get_info(node, depth=0):
    if opts.maxDepth is not None and depth >= opts.maxDepth:
        children = None
    else:
        children = [get_info(c, depth+1)
                    for c in node.get_children()]
    return { 'id' : get_cursor_id(node),
             'kind' : node.kind,
             'usr' : node.get_usr(),
             'spelling' : node.spelling,
             'args': node.type.spelling,
             'location' : node.location,
             'extent.start' : node.extent.start,
             'extent.end' : node.extent.end,
             'is_definition' : node.is_definition(),
             'definition id' : get_cursor_id(node.get_definition()),
             'children' : children }


def generateCase(ast, f):
    funcname = f[:-5]
    cur = funcname.rfind(".c")
    funcname = funcname[cur+3:]
    print('funcname ', funcname)
    cf = cfile.cfile(f+"_test.c")
    import uuid
    case_desc = json.load(open(f))
    for case in case_desc:
        print(case)
        caseId = str(uuid.uuid5(uuid.NAMESPACE_X500, str(case))).replace('-', '')
        cf.code.append(cfile.blank())
        cf.code.append(cfile.function("test_" + funcname + caseId, 'void'))
        body = cfile.block(innerIndent=2)
        if funcname not in ast['funcs'].keys():
            print("err func not found in ast", funcname)
            return 1
        args = ast['funcs'][funcname]
        print(args)
        model_params = case['parameters']
        model_str = case['model']
        model_str = model_str.split('\n')
        value_dict = {}
        for item in model_str:
            item = item.split("->")
            print("item is ",item)
            if len(item) > 1:
                value_dict[item[0].strip(' ')]=item[1].strip(' ')
       
        for arg in args.items():
            body.append(cfile.statement(arg[1] + ' ' + arg[0]))
            
        # init params
        print(model_params)
        print(value_dict)
        for item in value_dict.items():
            print('item0 ', item[0])
            print(model_params)
            if item[0] in model_params.keys():
                body.append(cfile.statement(model_params[item[0]] + " = " + item[1]))
        fcall = cfile.fcall(funcname)
        for arg in args.items():
            fcall.add_arg(arg[0])
        body.append(cfile.statement(fcall))
        cf.code.append(body)
        print(str(cf))


def generate(ast, src_file):
    src_path = os.path.abspath(os.path.dirname(src_file))
    filename = os.path.abspath(src_file).split('/')[-1]
    for f in os.listdir(src_path):
        if os.path.isfile(f) and filename in f and f.endswith(".json"):
            generateCase(ast, f)
            

def get_info1(node, depth=0):
    funcs = {}
    global_vars = {}
    typedefs = {}
    for n in node.get_children():
        if n.kind == CursorKind.FUNCTION_DECL:
            args = {}
            for nn in n.get_children():
                if nn.kind == CursorKind.PARM_DECL:
                    args[nn.spelling] = nn.type.spelling
            funcs[n.spelling] = args
        elif n.kind == CursorKind.VAR_DECL:
            global_vars[n.spelling] = n.type.spelling
        elif n.kind == CursorKind.TYPEDEF_DECL:
            typedefs[n.spelling] = read_qualified_type(n.underlying_typedef_type)
    ret = {"funcs":funcs, "vars":global_vars, "typedefs":typedefs}
    return ret
def main():
    #Config.set_library_file("/usr/lib/libclang.so.13")
    from pprint import pprint

    from optparse import OptionParser, OptionGroup

    global opts

    parser = OptionParser("usage: %prog [options] filename.c [clang-args*]")
    parser.add_option("", "--show-ids", dest="showIDs",
                      help="Compute cursor IDs (very slow)",
                      action="store_true", default=False)
    parser.add_option("", "--max-depth", dest="maxDepth",
                      help="Limit cursor expansion to depth N",
                      metavar="N", type=int, default=None)
    parser.add_option("-l", "--clanglib", dest="lib",
                      help="specify your own libclang.so if it can not be found in default",
                      metavar="libclang.so", type=str, default=None)

    parser.disable_interspersed_args()
    (opts, args) = parser.parse_args()

    if opts.lib:
        Config.set_library_file(opts.lib)
    else:
        print("WARN: If libclang is not found, you can specify your own libclang.so.\nUse -h to see details!")

    if len(args) == 0:
        parser.error("no args, input file must be specified")

    src_file = args[0]
    print(src_file)
    index = Index.create()
    #args.append("-I")
    #args.append("/usr/lib/clang/13.0.1/include/")
    tu = index.parse(None, args)
    if not tu:
        parser.error("unable to load input")

    pprint(('diags', [get_diag_info(d) for d in  tu.diagnostics]))
    #pprint(('nodes', get_info(tu.cursor)))
    #pprint(('nodes', get_info1(tu.cursor)))

    ast_info = get_info1(tu.cursor)
    generate(ast_info, src_file)

if __name__ == '__main__':
    main()
