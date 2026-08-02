#!/usr/bin/env python3
"""
TrueMath CLI — solve math problems directly from the terminal, no dashboard
needed. Useful for scripting/coding workflows.

Usage:
    python cli.py solve "2x + 5 = 15"
    python cli.py solve "derivative of x^3"
    python cli.py hard number_theory prime_factors '{"n": 123456789}'
    python cli.py list-operations
"""
from __future__ import annotations

import json
import sys

from src.math_engine.problem_solver import try_solve
from src.math_engine.hard_problem_dispatcher import solve as solve_hard_problem, CATEGORIES


def cmd_solve(args):
    if not args:
        print("Usage: python cli.py solve \"<question>\"")
        sys.exit(1)
    question = " ".join(args)
    result = try_solve(question)
    if result:
        print(f"Answer: {result['answer']}")
        if result.get("steps"):
            print("Steps:")
            for step in result["steps"]:
                print(f"  - {step}")
        if result.get("verified"):
            print(f"Verified: {result['verified']}")
    else:
        print("Ye ek concrete computable problem nahi lagta (equation/derivative/integral/simplify/factor/arithmetic).")
        print("For open-ended questions, use the dashboard's Q&A box (needs Groq/OpenRouter API keys).")


def cmd_hard(args):
    if len(args) < 2:
        print('Usage: python cli.py hard <category> <operation> \'{"param": value}\'')
        print(f"Categories: {list(CATEGORIES.keys())}")
        sys.exit(1)
    category, operation = args[0], args[1]
    params = json.loads(args[2]) if len(args) > 2 else {}
    result = solve_hard_problem(category, operation, params)
    print(json.dumps(result, indent=2, default=str))


def cmd_list_operations(_args):
    for category, ops in CATEGORIES.items():
        print(f"{category}:")
        for op in ops:
            print(f"  - {op}")


_COMMANDS = {
    "solve": cmd_solve,
    "hard": cmd_hard,
    "list-operations": cmd_list_operations,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        print(__doc__)
        print(f"Available commands: {list(_COMMANDS.keys())}")
        sys.exit(1)
    command = sys.argv[1]
    _COMMANDS[command](sys.argv[2:])


if __name__ == "__main__":
    main()
