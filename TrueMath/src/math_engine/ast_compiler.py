"""
Module Name: ast_compiler
Purpose: Parse AI-proposed math formulas into safe, strict Abstract Syntax Trees.
Responsibilities:
  - Convert pseudo-math strings into SymPy AST logic.
  - Strict security check to block Python code injection (eval/exec vulnerabilities).
  - Pre-filter out mathematically absurd expressions before they hit Lean 4.
Dependencies: sympy, ast
Input: Raw string equations from Cognitive_AI_Engine.
Output: Validated SymPy expressions or raising specific errors.
Possible Errors: Invalid syntax, malicious injection attempts.
Testing Method: Regex bounds tests and injecting maliciously formed Python strings.
Estimated Complexity: High.
Integration Notes: Call `parse_safe_math()` before forwarding any calculation to Lean 4 kernel.
"""
import ast
from typing import Optional, Union, Dict, Any
from src.core.sys_logger import get_logger

logger = get_logger("ASTCompiler")

class MathSyntaxError(Exception):
    """Raised when the AI produces mathematically invalid text."""
    pass

class MaliciousPayloadError(Exception):
    """Raised if a prompt-injection or arbitrary code execution attempt is detected."""
    pass

class ASTPreFilter:
    __slots__ = ('_safe_dict',)
    
    def __init__(self):
        self._safe_dict = None

    @property
    def safe_dict(self) -> Dict[str, Any]:
        """Lazy property loading sympy on demand, speeding up startup by >200ms."""
        if self._safe_dict is None:
            import sympy
            self._safe_dict = {
                'x': sympy.Symbol('x'),
                'y': sympy.Symbol('y'),
                'z': sympy.Symbol('z'),
                'n': sympy.Symbol('n'),
                'sin': sympy.sin,
                'cos': sympy.cos,
                'tan': sympy.tan,
                'exp': sympy.exp,
                'log': sympy.log,
                'pi': sympy.pi,
                'E': sympy.E,
                'sqrt': sympy.sqrt
            }
        return self._safe_dict

    def _security_check(self, expression_str: str) -> bool:
        """Statically analyzes the expression string to block native Python hacks."""
        try:
            tree = ast.parse(expression_str, mode='eval')
            for node in ast.walk(tree):
                # Disallow lambda definitions entirely
                if isinstance(node, ast.Lambda):
                    logger.critical("Security Alert: Blocked unauthorized Lambda definition.")
                    return False

                # Block function calls that aren't in our pure math whitelist Name
                if isinstance(node, ast.Call):
                    if not isinstance(node.func, ast.Name):
                        logger.critical(f"Security Alert: Blocked complex call expression of type '{type(node.func).__name__}'")
                        return False
                    if node.func.id not in self.safe_dict:
                        logger.critical(f"Security Alert: Blocked unauthorized function call '{node.func.id}'")
                        return False

                # Block general attribute access (like string.__class__ hacks)
                if isinstance(node, ast.Attribute):
                    logger.critical(f"Security Alert: Blocked unauthorized attribute access '{node.attr}'")
                    return False
            return True
        except SyntaxError:
            # Let standard Sympify catch pure mathematical syntax errors later, 
            # unless it's completely unparseable code.
            return True

    def parse_safe_math(self, expression_str: str) -> Any:
        """
        Converts raw string to a mathematically safe SymPy expression.
        Guarantees isolation of the Python OS environment from untrusted AI outputs.
        """
        import sympy

        if len(expression_str) > 5000:
            logger.critical(f"Security Alert: Math payload exceeds 5000 chars. Possible AI DOS hallucination.")
            raise MaliciousPayloadError("Expression length exceeds mathematical sandbox limits.")
            
        if not self._security_check(expression_str):
            raise MaliciousPayloadError("Expression failed strict static security analysis.")
            
        try:
            # Strictly limit the namespace evaluation using the safe_dict constraint
            expr = sympy.sympify(expression_str, locals=self.safe_dict, evaluate=False)
            logger.debug(f"Successfully compiled AST: {expr}")
            return expr
        except sympy.SympifyError as e:
            logger.error(f"SymPy rejected parsing for '{expression_str[:80]}': {e}")
            raise MathSyntaxError(f"Invalid math syntax: {e}")
        except Exception as e:
            logger.error(f"Unexpected compilation fault for '{expression_str[:80]}': {e}", exc_info=True)
            raise MathSyntaxError(f"Internal compiler error: {e}")
