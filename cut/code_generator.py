from cut import test_case as case
from cut import knowlege
from cut import log_parser
import json

import os


class CodeGenerator:
    def __init__(self, jfile: str) -> None:
        self._jfile = jfile
        self._knowlege = knowlege.KnowlegeBase(jfile)

    def generate(self) -> None:
        jdata = json.load(open(self._jfile))
        actions, _ = log_parser.parse_unique_log(jdata, ".", compile_uniqueing="strict")
        for act in actions:
            src_path = os.path.abspath(os.path.dirname(act.source))
            filename = os.path.basename(act.source)
            for f in os.listdir(src_path):
                f = os.path.join(src_path, f)
                if os.path.isfile(f) and filename in f and f.endswith(".json"):
                    print(f)
                    func_name = f[:-5]
                    cur = func_name.rfind(".c")
                    func_name = func_name[cur + 3 :]
                    cases = self.generateCases(f, func_name)
                    self.save_to_file(cases, act.source, func_name)

    def save_to_file(self, cases, source, func_name):
        test_file = source + "_test_" + func_name + ".c"
        with open(test_file, "w") as f:
            for item in cases:
                f.write(item)

    def generateCases(self, f, func_name):
        case_asts = []
        case_descs = json.load(open(f))
        for case_desc in case_descs:
            test_case = case.TestCase(func_name, case_desc, self._knowlege)
            case_asts.append(test_case.generate_func())
        return case_asts


if __name__ == "__main__":
    cgen = CodeGenerator("codechecker_commands.json")
    cgen.generate()
