import argparse
import json
import os
import sys
from pathlib import Path

import simple_parsing
import subprocess
import signal
from typing import List

from cut.__version__ import __version__
from cut import logger
from cut import log_parser
from cut import code_generator

proc_pid = None


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create ArgumentParser."""

    parser = simple_parsing.ArgumentParser(
        add_option_string_dash_variants=simple_parsing.DashVariant.UNDERSCORE_AND_DASH,
        description="Kut is a kernel unit test generation framework for Linux kernel code",
        fromfile_prefix_chars="@",
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        default="info",
        type=str,
        help="verbose output(info, debug)",
    )

    parser.add_argument(
        "-b",
        "--build",
        dest="build",
        required=False,
        default=None,
        type=str,
        help="trace building, output codechecker_commands.json. e.g. : cut -b 'make'",
    )

    parser.add_argument(
        "-c",
        "--case",
        dest="case",
        required=False,
        default=None,
        type=str,
        help="generate cases after build scripts. e.g. : cut -g 'make'",
    )

    parser.add_argument(
        "-g",
        "--generate",
        dest="generate",
        required=True,
        default=None,
        type=str,
        help="generate cases after build scripts. e.g. : cut -g 'make'",
    )

    return parser


def run_checker(env: dict = None, args: argparse.Namespace = None) -> int:
    """Run CodeChecker to trace compile commands, stored in codechecker_commands.json."""

    if env is None:
        env = {}
    env["CC_LOGGER_GCC_LIKE"] = "gcc:g++:clang:clang++:cc:c++:ld"
    checker_cmd = ["CodeChecker", "log", "-b", args.generate, "-o", "codechecker_commands.json"]

    proc = subprocess.Popen(checker_cmd, encoding="utf=8", errors="ignore", env=env)
    global proc_pid
    proc_pid = proc.pid
    proc.wait()
    LOG = logger.get_logger("system")
    if proc.returncode != 0:
        LOG.error("run CodeChecker failed! args : {}".format(checker_cmd))
    return proc.returncode


def parse_build_json() -> dict:
    ret = {}
    with open("codechecker_commands.json") as f:
        build_cmds = json.load(f)
        return build_cmds
    return ret


def run_clangsa(env: dict = None, args: argparse.Namespace = None) -> int:
    """Run Clang Static Analysis to generate case description json, stored in each xx.c_funcname.json."""
    build_dict = parse_build_json()
    actions, skipped_cmp_cmd_count = log_parser.parse_unique_log(build_dict, ".")
    print(build_dict)
    print(type(actions))
    for act in actions:
        print(str(act))
    clangsa_cmd = [
        "clang",
        "--analyze",
        "-Qunused-arguments",
        "--analyzer-no-default-checks",
        "-Xclang",
        "-analyzer-checker=core.CaseFind",
        "-I",
        "/usr/lib/clang/16.0.0/include",
    ]

    LOG = logger.get_logger("system")
    LOG.info("!!!!!start clangsa case generator!!!!!")
    for act in actions:
        each_cmd = []
        each_cmd.extend(clangsa_cmd)
        each_cmd.extend(act.analyzer_options)
        each_cmd.append(act.source)
        LOG.info(each_cmd)
        proc = subprocess.Popen(each_cmd, encoding="utf=8", errors="ignore", cwd=act.directory, env=env)
        global proc_pid
        proc_pid = proc.pid
        proc.wait()
        if proc.returncode != 0:
            LOG.error("run clangsa failed! args : {}".format(each_cmd))
            return proc.returncode

    return 0


def run_codegen(env: dict = None, args: argparse.Namespace = None) -> int:
    """
    Run test case code generator, Each input json with a test c source code output.
    For example, CodeGenerator parses xx.c_funcname.json then generate xx.c_funcname_test.c.
    """
    cgen = code_generator.CodeGenerator("codechecker_commands.json")
    ret = cgen.generate()
    return ret


def run_cmd(env: dict = None, args: argparse.Namespace = None) -> int:
    """
    Run commands to generate cases.
    Steps:
        1. Run CodeChecker to trace compile commands, stored in codechecker_commands.json.
        2. Run Clang Static Analysis to generate case description json, stored in each xx.c_funcname.json.
        3. Generate case source codes based on 2.
        4. Generate case Makefiles.

    Args:
        env: environment for cmds.
        args: args from input.

    Returns:
        An integer representing the success of the program run.
    """
    ret = run_checker(env, args)
    if ret != 0:
        return ret
    ret = run_clangsa(env, args)
    if ret != 0:
        return ret
    ret = run_codegen(env, args)
    if ret != 0:
        return ret
    return 0


def main(argv: List[str] = None) -> int:
    """
    Entry point for the CLI of the Kernel automatic unit test generation framework.

    This method behaves like a standard UNIX command-line application, i.e.,
    the return value '0' signals a successful executaion. Any other return value signals
    some errors.

    Args:
        argv: List of command-line arguments

    Returns:
       An integer representing the success of the program run.
    """

    if argv is None:
        argv = sys.argv

    argparser = _create_argument_parser()
    args, unknown = argparser.parse_known_args()

    logger.setup_logger(args.verbosity)
    LOG = logger.get_logger("system")

    if args.generate is None:
        LOG.error("FLAG -g/--generate must be specified!")
        sys.argv.append("--help")

    original_env = os.environ.copy()

    def signal_term_handler(signum, frame):
        global proc_pid
        if proc_pid:
            os.kill(proc_pid, signal.SIGINT)
        sys.exit(128 + signum)

    signal.signal(signal.SIGTERM, signal_term_handler)
    signal.signal(signal.SIGINT, signal_term_handler)
    run_cmd(original_env, args)
    return 0


if __name__ == "__main__":
    sys.exit(main(argv=sys.argv))
