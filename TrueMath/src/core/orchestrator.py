"""
Module Name: orchestrator
Purpose: Central integration hub — sequences all 15 modules into one autonomous research loop.
         This is the single point of execution for TrueMath.
Integration Notes: Instantiated and started from `main.py`.
"""
import threading
import asyncio
import gc
import json
import time
from typing import Optional

import config
from src.core.sys_logger import get_logger
from src.core.state_manager import EpochStateManager
from src.core.history_store import HistoryStore
from src.core.telemetry_engine import TelemetryEngine
from src.ai.cognitive_engine import CognitiveCore, ContextExhaustionError
from src.ai.mcts_evaluator import MCTSTree
from src.ai.cloud_llm_bridge import CloudLLMBridge
from src.math_engine.ast_compiler import ASTPreFilter, MathSyntaxError, MaliciousPayloadError
from src.math_engine.falsification_engine import FalsificationEngine
from src.math_engine.lean4_bridge import Lean4Bridge, FormalVerificationKernelError
from src.math_engine.lean4_translator import build_lean_source
from src.math_engine.symbolic_genesis import SymbolicGenesisCore
from src.math_engine.problem_solver import try_solve
from src.math_engine.discovery_engine import discover_identity
from src.math_engine.conjecture_checker import run_check as run_conjecture_check
from src.math_engine.oeis_lookup import lookup_sequence
from src.math_engine.hard_problem_dispatcher import solve as solve_hard_problem, CATEGORIES as HARD_PROBLEM_CATEGORIES
from src.math_engine.arxiv_search import search_arxiv
from src.math_engine.web_search_fallback import search_web
from src.math_engine.query_router import route_query, get_unmatched_queries
from src.ai.agent_tools import TOOLS as AGENT_TOOLS, execute_tool_call
from src.memory.graveyard_rag import GraveyardDB
from src.ui_bridge.ipc_handler import IPCBridgeServer

logger = get_logger("Orchestrator")

# Curated set of famous hard/unsolved problems the user can pick from in the
# dashboard, each with a short factual description that's fed to the LLM as
# context so generated hypotheses are actually relevant to the topic (not
# generic filler). Users can also type a fully custom topic.
FAMOUS_PROBLEMS = {
    "Riemann Hypothesis": (
        "All non-trivial zeros of the Riemann zeta function ζ(s) are believed "
        "to have real part exactly 1/2. Unsolved since 1859; one of the "
        "Clay Millennium Prize Problems."
    ),
    "Goldbach Conjecture": (
        "Every even integer greater than 2 can be written as the sum of two "
        "prime numbers. Verified numerically for huge ranges, but unproven "
        "in general."
    ),
    "Collatz Conjecture": (
        "Starting from any positive integer n, repeatedly applying "
        "'n/2 if even, else 3n+1' is conjectured to always eventually reach 1. "
        "True for all tested values so far, but unproven in general."
    ),
    "Twin Prime Conjecture": (
        "There are conjectured to be infinitely many prime pairs (p, p+2). "
        "Unproven, though recent work has bounded the gaps between primes."
    ),
    "P vs NP": (
        "Asks whether every problem whose solution can be quickly verified "
        "can also be quickly solved. One of the Clay Millennium Prize "
        "Problems; almost certainly not numerically testable."
    ),
}

_DEFAULT_TOPIC = "Riemann Hypothesis"
_DEFAULT_TOPIC_DESC = FAMOUS_PROBLEMS[_DEFAULT_TOPIC]
_MAX_TOPIC_CHARS = 200


def _build_math_system_prompt(topic: str, description: str) -> str:
    """Builds a topic-aware system prompt so hypothesis generation is
    actually relevant to whatever problem is currently selected, instead of
    always generating unrelated generic formulas."""
    return (
        f"You are a rigorous mathematical research assistant currently exploring "
        f"this problem: \"{topic}\". Background: {description} "
        "Propose ONE short mathematical formula, relation, or numerical pattern "
        "that could plausibly be relevant to this problem, using only: "
        "x, y, z, n, sin, cos, tan, exp, log, sqrt, pi, E, and standard operators. "
        "Output ONLY the expression — no explanations, no text."
    )


# System prompt used for user-submitted questions via the dashboard's Q&A box
_QA_SYSTEM_PROMPT = (
    "You are a clear, rigorous mathematics tutor. Answer the user's "
    "mathematical question correctly and concisely, showing brief reasoning "
    "or a short derivation where useful. Keep the answer under ~200 words."
)

_MAX_QUESTION_CHARS = 2000


class TrueMathOrchestrator:
    """
    Thread-safe autonomous research engine.
    Wires all 15 backend modules into a single coherent pipeline:
      CognitiveCore → LLMBridge → ASTPreFilter → FalsificationEngine
      → Lean4Bridge → SymbolicGenesis → GraveyardDB → StateManager
      → TelemetryEngine → IPCBridgeServer
    """
    __slots__ = (
        '_stop_event', '_research_loop_thread', '_is_running',
        'state_manager', 'telemetry', 'cognitive', 'llm_bridge',
        'mcts_tree', 'ast_filter', 'falsifier', 'lean4',
        'genesis', 'graveyard', 'ipc', '_node_statuses',
        '_current_topic', '_topic_description', '_system_prompt', 'history_store',
    )

    def __init__(self):
        self._stop_event = threading.Event()
        self._research_loop_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._current_topic = _DEFAULT_TOPIC
        self._topic_description = _DEFAULT_TOPIC_DESC
        self._system_prompt = _build_math_system_prompt(_DEFAULT_TOPIC, _DEFAULT_TOPIC_DESC)
        self._node_statuses = {_DEFAULT_TOPIC: "frontier"}

        # ── Module Instantiation (all config-driven) ─────────────────
        self.state_manager = EpochStateManager(db_path=config.STATE_DB_PATH)
        self.history_store = HistoryStore(db_path=config.HISTORY_DB_PATH)
        self.telemetry     = TelemetryEngine()
        self.cognitive     = CognitiveCore(max_context_tokens=config.COGNITIVE_MAX_TOKENS)
        self.llm_bridge    = CloudLLMBridge(
            groq_api_key=config.GROQ_API_KEY,
            groq_model=config.GROQ_MODEL_NAME,
            groq_base_url=config.GROQ_BASE_URL,
            openrouter_api_key=config.OPENROUTER_API_KEY,
            openrouter_model=config.OPENROUTER_MODEL_NAME,
            openrouter_base_url=config.OPENROUTER_BASE_URL,
            timeout_s=config.LLM_TIMEOUT_S,
        )
        self.mcts_tree  = MCTSTree(
            root_state=_DEFAULT_TOPIC,
            exploration_weight=config.MCTS_EXPLORATION_WEIGHT,  # BUG-13 FIX: consume orphaned config const
        )
        self.ast_filter = ASTPreFilter()
        self.falsifier  = FalsificationEngine(iterations=config.FALSIFICATION_ITERATIONS)
        self.lean4      = Lean4Bridge(
            timeout_seconds=config.LEAN4_TIMEOUT_S,
            project_dir=config.LEAN4_PROJECT_DIR or None,
        )
        self.genesis    = SymbolicGenesisCore(pattern_threshold=config.GENESIS_PATTERN_THRESHOLD)
        self.graveyard  = GraveyardDB(db_path=config.GRAVEYARD_DB_PATH)
        self.ipc        = IPCBridgeServer(host=config.IPC_HOST, port=config.IPC_PORT)

        # Register UI control actions
        self.ipc.register_action("pause",  lambda _: self._handle_pause())
        self.ipc.register_action("resume", lambda _: self._handle_resume())
        self.ipc.register_action("status", lambda _: self.telemetry.generate_snapshot())
        self.ipc.register_action("ask_question", self._handle_ask_question)
        self.ipc.register_action("set_topic", lambda data: self._handle_set_topic(data))
        self.ipc.register_action("discover", lambda _: self._handle_discover())
        self.ipc.register_action("run_conjecture_check", self._handle_conjecture_check)
        self.ipc.register_action("oeis_lookup", self._handle_oeis_lookup)
        self.ipc.register_action("solve_hard_problem", self._handle_hard_problem)
        self.ipc.register_action(
            "get_hard_problem_categories",
            lambda _: {"type": "hard_problem_categories", "categories": HARD_PROBLEM_CATEGORIES},
        )
        self.ipc.register_action("search_arxiv", self._handle_arxiv_search)
        self.ipc.register_action("export_history", self._handle_export_history)
        self.ipc.register_action(
            "get_unmatched_queries",
            lambda _: {"type": "unmatched_queries", "queries": get_unmatched_queries(50)},
        )
        self.ipc.register_action("ask_agent", self._handle_ask_agent)
        self.ipc.register_action(
            "get_history",
            lambda data: {
                "type": "history_data",
                "qa_history": self.history_store.get_qa_history(50, session_id=data.get("_session_id")),
                "discoveries": self.history_store.get_discoveries(50),
            },
        )
        self.ipc.register_action(
            "get_problem_catalog",
            lambda _: {"type": "problem_catalog", "problems": FAMOUS_PROBLEMS, "current_topic": self._current_topic},
        )

        # Register callback to send initial state when new clients connect
        self.ipc.register_on_connect(self._get_initial_messages)

        logger.info("TrueMath Orchestrator fully assembled — all 15 modules wired.")

    def _get_initial_messages(self) -> list[dict]:
        """Generate initial state messages for new frontend connections."""
        return [
            {"type": "telemetry", "payload": self.telemetry.generate_snapshot()},
            {"type": "mcts_update", "payload": self._get_mcts_nodes_ui_payload()},
        ]

    # ── Control API ──────────────────────────────────────────────────

    def start(self) -> None:
        """Starts the background research loop and the async IPC server."""
        if self._is_running:
            return
        if self._research_loop_thread and self._research_loop_thread.is_alive():
            self._stop_event.set()
            self._research_loop_thread.join(timeout=2.0)

        self._stop_event.clear()
        self._is_running = True
        self._research_loop_thread = threading.Thread(
            target=self._master_research_loop, daemon=True, name="ResearchLoop"
        )
        self._research_loop_thread.start()

        # Run IPC server in a dedicated daemon thread with its own event loop
        ipc_thread = threading.Thread(target=self._run_ipc_server, daemon=True, name="IPCServer")
        ipc_thread.start()

        # Broadcast initial state to any already connected clients
        for msg in self._get_initial_messages():
            self.ipc.broadcast_sync(msg)

        logger.info("Autonomous Mathematical Execution Engine: ONLINE.")

    def stop(self) -> None:
        """Gracefully stops all loops and persists final state."""
        self._is_running = False
        self._stop_event.set()
        if self._research_loop_thread:
            self._research_loop_thread.join(timeout=3.0)
        try:
            self.ipc.stop()
        except Exception as e:
            logger.warning(f"Error stopping IPC bridge: {e}")
        logger.info("Autonomous Mathematical Execution Engine: SECURELY HALTED.")

    # ── IPC Helpers ──────────────────────────────────────────────────

    def _run_ipc_server(self) -> None:
        """Runs the asyncio IPC server in its own OS thread."""
        asyncio.run(self.ipc.start_server())

    def _handle_pause(self) -> dict:
        self._stop_event.set()
        logger.info("Research paused by UI command.")
        return {"status": "paused"}

    def _handle_set_topic(self, data: dict) -> dict:
        """Switches the autonomous exploration loop to a new problem.

        Resets the MCTS tree and cognitive context so the engine starts a
        fresh line of exploration targeted at the new topic, and rebuilds the
        LLM system prompt so generated hypotheses are actually relevant to it
        (rather than generic filler, which is what happened before this
        topic-switching feature existed).
        """
        topic = (data or {}).get("topic", "")
        topic = topic.strip() if isinstance(topic, str) else ""
        description = (data or {}).get("description", "")
        description = description.strip() if isinstance(description, str) else ""

        if not topic:
            return {"type": "topic_response", "status": "error", "message": "Topic khaali hai."}
        if len(topic) > _MAX_TOPIC_CHARS:
            return {
                "type": "topic_response",
                "status": "error",
                "message": f"Topic bohat lamba hai (max {_MAX_TOPIC_CHARS} characters).",
            }

        # Known catalog entries have a curated description; custom topics get
        # a generic one unless the client supplied its own.
        if not description:
            description = FAMOUS_PROBLEMS.get(topic, "User-submitted problem. Explore relevant mathematical relationships.")

        self._current_topic = topic
        self._topic_description = description
        self._system_prompt = _build_math_system_prompt(topic, description)

        # Fresh MCTS tree + node statuses for the new topic (attribute
        # reassignment is atomic under the GIL, so the research loop thread
        # never sees a half-updated tree).
        self.mcts_tree = MCTSTree(root_state=topic, exploration_weight=config.MCTS_EXPLORATION_WEIGHT)
        self._node_statuses = {topic: "frontier"}
        self.cognitive.reset_context()

        logger.info(f"Topic switched to: {topic}")
        return {"type": "topic_response", "status": "ok", "topic": topic, "description": description}

    async def _handle_ask_agent(self, data: dict) -> dict:
        """Handles a COMPOUND question (multiple sub-problems combined,
        e.g. "factor 360, then gcd it with 48, then the determinant of
        [[2,1],[1,3]]") using genuine LLM function-calling: the LLM decides
        which real tools to call and with what arguments, but the actual
        math is always done by the verified dispatcher — never by the LLM
        itself. Requires a configured Groq/OpenRouter key (this needs an
        LLM to do the decomposition; there's no reliable way to do this
        without one)."""
        question = (data or {}).get("question", "")
        question = question.strip() if isinstance(question, str) else ""
        session_id = (data or {}).get("_session_id")
        if not question:
            return {"type": "agent_response", "status": "error", "message": "Sawal khaali hai."}
        if len(question) > _MAX_QUESTION_CHARS:
            return {"type": "agent_response", "status": "error", "message": f"Sawal bohat lamba hai (max {_MAX_QUESTION_CHARS} characters)."}

        system_prompt = (
            "You are a math agent with access to real calculation tools. For any question "
            "involving numbers, matrices, or physics, ALWAYS call the appropriate tool rather "
            "than computing the answer yourself — you might make arithmetic mistakes, but the "
            "tools are exact. If a question has multiple parts, call multiple tools in sequence. "
            "Once you have all the real results, write a short final summary combining them."
        )

        loop = asyncio.get_running_loop()
        try:
            answer, tool_log = await loop.run_in_executor(
                None, self.llm_bridge.run_agent, system_prompt, question, AGENT_TOOLS, execute_tool_call
            )
        except Exception as e:
            logger.error(f"ask_agent crashed: {e}")
            return {"type": "agent_response", "status": "error", "message": "Agent mein error aa gaya."}

        if not answer:
            return {"type": "agent_response", "status": "error", "message": self.llm_bridge.last_error_message()}

        self.history_store.save_qa(question, answer.strip(), "agent", session_id=session_id)
        return {
            "type": "agent_response",
            "status": "ok",
            "question": question,
            "answer": answer.strip(),
            "tool_calls": tool_log,
        }

    async def _handle_export_history(self, data: dict) -> dict:
        """Exports saved Q&A history + discoveries to a Markdown or PDF file
        on disk, returning the absolute path so the user can find it in
        their file explorer. Only exports THIS caller's own session
        history, never anyone else's."""
        fmt = (data or {}).get("format", "markdown")
        session_id = (data or {}).get("_session_id")
        loop = asyncio.get_running_loop()
        try:
            if fmt == "pdf":
                path = await loop.run_in_executor(None, self.history_store.export_pdf, config.EXPORTS_DIR, session_id)
            else:
                path = await loop.run_in_executor(None, self.history_store.export_markdown, config.EXPORTS_DIR, session_id)
        except Exception as e:
            logger.error(f"History export failed: {e}")
            return {"type": "export_result", "status": "error", "message": f"Export fail ho gaya: {e}"}
        return {"type": "export_result", "status": "ok", "path": path, "format": fmt}

    async def _handle_arxiv_search(self, data: dict) -> dict:
        """Searches real, current arXiv preprints for a topic — genuine
        live internet data (network call, runs in a thread executor)."""
        query = (data or {}).get("query", self._current_topic)
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, search_arxiv, query, 5, 15)
        except Exception as e:
            logger.error(f"arXiv search crashed: {e}")
            return {"type": "arxiv_result", "status": "error", "message": "arXiv search mein error aa gaya."}
        return {"type": "arxiv_result", **result}

    async def _handle_hard_problem(self, data: dict) -> dict:
        """Dispatches to a real solver (number theory / optimization /
        crypto-math / combinatorics) — runs in a thread executor since some
        operations (factoring, LP, knapsack) can take real CPU time."""
        category = (data or {}).get("category", "")
        operation = (data or {}).get("operation", "")
        params = (data or {}).get("params", {})

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, solve_hard_problem, category, operation, params)
        except Exception as e:
            logger.error(f"Hard problem solve crashed: {e}")
            return {"type": "hard_problem_result", "status": "error", "message": "Solver mein error aa gaya."}

        return {"type": "hard_problem_result", "category": category, "operation": operation, **result}

    async def _handle_oeis_lookup(self, data: dict) -> dict:
        """Looks up a user-supplied number sequence against the real OEIS
        database. Runs in a thread executor since it's a network call."""
        sequence = (data or {}).get("sequence", "")
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, lookup_sequence, sequence)
        except Exception as e:
            logger.error(f"OEIS lookup crashed: {e}")
            return {"type": "oeis_result", "status": "error", "message": "OEIS lookup mein error aa gaya."}
        return {"type": "oeis_result", **result}

    async def _handle_conjecture_check(self, data: dict) -> dict:
        """Runs a real numeric conjecture check (Collatz/Goldbach/Twin
        Primes) in a thread executor so a large limit doesn't freeze the
        IPC event loop for other connected clients."""
        conjecture = (data or {}).get("conjecture", "collatz")
        try:
            limit = int((data or {}).get("limit", 100_000))
        except (TypeError, ValueError):
            limit = 100_000

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, run_conjecture_check, conjecture, limit)
        except Exception as e:
            logger.error(f"Conjecture check '{conjecture}' crashed: {e}")
            return {"type": "conjecture_result", "status": "error", "message": "Conjecture check mein error aa gaya."}

        return {"type": "conjecture_result", "status": "ok", **result}

    def _handle_discover(self) -> dict:
        """Generates one fresh, symbolically-verified identity instance
        on demand (see discovery_engine.py for the honesty notes on what
        this actually is and isn't)."""
        try:
            result = discover_identity()
        except Exception as e:
            logger.error(f"discover_identity failed: {e}")
            return {"type": "discovery", "status": "error", "message": "Discovery engine mein error aa gaya."}
        self.history_store.save_discovery(
            result["base_identity"], result["substitution"], result["lhs"], result["rhs"], result["verified_equal"]
        )
        return {"type": "discovery", "status": "ok", **result}

    def _handle_resume(self) -> dict:
        self._stop_event.clear()
        logger.info("Research resumed by UI command.")
        return {"status": "resumed"}

    async def _handle_ask_question(self, data: dict) -> dict:
        """Handles a user-submitted math question from the dashboard's Q&A box.

        Runs the (blocking, up to ~15s) LLM call in a thread executor so the
        IPC event loop stays free to keep broadcasting telemetry to other
        connected clients while the answer is being generated.
        """
        question = (data or {}).get("question", "")
        question = question.strip() if isinstance(question, str) else ""
        session_id = (data or {}).get("_session_id")

        if not question:
            return {"type": "qa_response", "status": "error", "message": "Sawal khaali hai."}
        if len(question) > _MAX_QUESTION_CHARS:
            return {
                "type": "qa_response",
                "status": "error",
                "message": f"Sawal bohat lamba hai (max {_MAX_QUESTION_CHARS} characters).",
            }

        # ── Step 1: Try to actually COMPUTE a real, exact answer first ──
        # (equations, derivatives, integrals, simplification, factoring,
        # arithmetic). This is ground truth from SymPy, never guessed.
        try:
            computed = try_solve(question)
        except Exception as e:
            logger.debug(f"Symbolic solver crashed (non-fatal): {e}")
            computed = None

        if computed:
            self.history_store.save_qa(question, computed["answer"], "computed", session_id=session_id)
            return {
                "type": "qa_response",
                "status": "ok",
                "question": question,
                "answer": computed["answer"],
                "answer_latex": computed.get("answer_latex"),
                "steps": computed.get("steps", []),
                "verified": computed.get("verified"),
                "verified_ok": computed.get("verified_ok"),
                "graph": computed.get("graph"),
                "source": "computed",
            }

        # ── Step 2: Keyword router — recognizes common question patterns
        # ("is X a perfect number", "factor X", "gcd of X and Y") and calls
        # the right tool directly, deterministically, no LLM needed. Faster
        # and more reliable than the LLM for anything it recognizes; only
        # unmatched queries fall through to Step 3.
        try:
            routed = route_query(question)
        except Exception as e:
            logger.debug(f"Query router crashed (non-fatal): {e}")
            routed = None

        if routed:
            self.history_store.save_qa(question, routed["answer"], routed.get("source", "router"), session_id=session_id)
            return {
                "type": "qa_response",
                "status": "ok",
                "question": question,
                "answer": routed["answer"],
                "steps": routed.get("steps", []),
                "verified": routed.get("verified"),
                "verified_ok": routed.get("verified_ok"),
                "source": "computed",
            }

        # ── Step 3: Fall back to the LLM tutor for open-ended / conceptual
        # questions neither the symbolic solver nor the keyword router can
        # recognize.
        loop = asyncio.get_running_loop()
        user_provider = (data or {}).get("user_provider", "")
        user_api_key = (data or {}).get("user_api_key", "")
        error_reason = None

        if user_provider and user_api_key:
            # Public-deployment path: this visitor supplied their OWN key,
            # so their request uses THEIR quota, not the server's shared
            # one. The key is used only for this call, never saved anywhere.
            try:
                answer, error_reason = await loop.run_in_executor(
                    None, self.llm_bridge.prompt_with_user_key, _QA_SYSTEM_PROMPT, question, user_provider, user_api_key
                )
            except Exception as e:
                logger.error(f"ask_question (user key) call failed: {e}")
                answer, error_reason = None, "network_error"
            agreement, all_answers = 1.0, [answer] if answer else []
        else:
            # Default path: server's own configured Groq/OpenRouter keys,
            # with Self-Consistency prompting (Wang et al. 2022): asks 3
            # independent times in parallel and majority-votes on the answer,
            # a real technique for improving LLM reliability on reasoning tasks.
            try:
                answer, agreement, all_answers = await loop.run_in_executor(
                    None, self.llm_bridge.prompt_ai_self_consistent, _QA_SYSTEM_PROMPT, question, 3
                )
            except Exception as e:
                logger.error(f"ask_question LLM call failed: {e}")
                answer, agreement, all_answers = None, 0.0, []

        if not answer:
            loop2 = asyncio.get_running_loop()
            try:
                web_result = await loop2.run_in_executor(None, search_web, question, 5, 10)
            except Exception as e:
                logger.error(f"Web search fallback crashed: {e}")
                web_result = {"status": "error"}

            if user_provider and user_api_key:
                error_messages = {
                    "rate_limited": f"Tumhari {user_provider} key ki rate limit hit ho gayi hai — thodi der ruko.",
                    "invalid_key": f"Tumhari {user_provider} key invalid lag rahi hai — check karo.",
                    "network_error": "Internet se connect nahi ho saka.",
                }
                base_message = error_messages.get(error_reason, "Tumhari key se jawab nahi mil saka.")
            else:
                base_message = self.llm_bridge.last_error_message()

            if web_result.get("status") == "ok" and web_result.get("results"):
                return {
                    "type": "qa_response",
                    "status": "error",
                    "question": question,
                    "message": base_message,
                    "web_fallback": web_result["results"],
                }
            return {
                "type": "qa_response",
                "status": "error",
                "question": question,
                "message": base_message,
            }

        self.history_store.save_qa(question, answer.strip(), "llm", session_id=session_id)
        return {
            "type": "qa_response",
            "status": "ok",
            "question": question,
            "answer": answer.strip(),
            "source": "llm",
            "agreement": round(agreement, 2),
            "attempts": len(all_answers),
        }

    # ── Main Research Pipeline ───────────────────────────────────────

    def _master_research_loop(self) -> None:
        """
        The 8-step autonomous mathematical research pipeline:
          1. LLM proposes a hypothesis via CognitiveCore + LLMBridge
          2. ASTPreFilter validates and sandboxes the expression
          3. GraveyardDB checks whether this path was tried before
          4. FalsificationEngine statistically stress-tests the theorem
          5. Lean4Bridge formally verifies surviving theorems
          6. SymbolicGenesis mines for novel operators
          7. StateManager snapshots the MCTS graph
          8. TelemetryEngine pushes dashboard metrics via IPC
        """
        logger.debug("Entering autonomous research matrix...")
        epoch = 0
        dummy_vector = [0.1] * 128  # Placeholder until real embedding model is plugged in
        last_telemetry_broadcast = 0
        last_discovery_broadcast = 0

        while not self._stop_event.is_set():
            try:
                epoch += 1

                # ── Step 1: Generate Hypothesis ──────────────────────
                hypothesis_str = None
                try:
                    hypothesis_str = self.llm_bridge.prompt_ai(
                        self._system_prompt,
                        math_context=f"Explore epoch {epoch} of: {self._current_topic}"
                    )
                except Exception as e:
                    logger.debug(f"LLM unavailable: {e}")

                if not hypothesis_str:
                    hypothesis_str = self.cognitive.generate_hypothesis()

                # ── Step 2: AST Validation & Security ───────────────
                try:
                    parsed_expr = self.ast_filter.parse_safe_math(hypothesis_str)
                except (MathSyntaxError, MaliciousPayloadError) as e:
                    logger.warning(f"AST rejected: {e}")
                else:
                    # ── Step 3: Graveyard Memory Check ───────────────────
                    past_failures = self.graveyard.query_graveyard(dummy_vector, threshold=0.99)
                    if not past_failures:
                        # ── Step 4: Statistical Falsification ────────────────
                        try:
                            import sympy

                            safe_lambda = sympy.lambdify(
                                (
                                    self.ast_filter.safe_dict["x"],
                                    self.ast_filter.safe_dict["y"],
                                    self.ast_filter.safe_dict["z"],
                                ),
                                parsed_expr,
                                modules=["math"],
                            )
                            survived = self.falsifier.structural_brute_force(safe_lambda, vars_expected=3)
                        except OverflowError:
                            logger.warning(f"Falsification overflow on '{hypothesis_str[:40]}'")
                            survived = False
                        except Exception as exc:
                            logger.debug(f"Falsification eval error ({type(exc).__name__}): {exc}")
                            survived = False

                        if survived:
                            # ── Step 5: Formal Lean 4 Verification ───────────────
                            lean_content, needs_mathlib = build_lean_source(hypothesis_str)
                            try:
                                passed, detail = self.lean4.verify_theorem(lean_content, needs_mathlib=needs_mathlib)
                            except FormalVerificationKernelError:
                                passed, detail = False, "Lean 4 unavailable"

                            self.telemetry.log_lean4_execution(success=passed)
                            if not passed:
                                self.graveyard.bury_path(hypothesis_str[:64], detail, dummy_vector)

                            # ── Step 6: Symbolic Genesis – Operator Mining ────────
                            trace = hypothesis_str.replace("(", " ").replace(")", " ").split()
                            new_op = self.genesis.scan_for_abstractions(trace)
                            if new_op:
                                self.telemetry.log_new_symbol()

                            # ── Step 7: MCTS Update ──────────────────────────────
                            self.telemetry.log_branch()
                            frontier = self.mcts_tree.select_best_path(self.mcts_tree.root)
                            self.mcts_tree.expand(frontier, [hypothesis_str])
                            self.mcts_tree.backpropagate(frontier, reward=1.0 if passed else 0.0)
                            self._node_statuses[hypothesis_str] = "verified" if passed else "rejected"

                if epoch % 50 == 0:
                    self.state_manager.save_epoch(
                        epoch_id=f"epoch_{epoch}",
                        state_data={"epoch": epoch, "last_hypothesis": hypothesis_str},
                    )

                # ── Step 8: Telemetry Snapshot (broadcast every second) ──
                current_time = time.time()
                if current_time - last_telemetry_broadcast > 1.0:
                    snapshot = self.telemetry.generate_snapshot()
                    snapshot["current_topic"] = self._current_topic
                    self.ipc.broadcast_sync({"type": "telemetry", "payload": snapshot})
                    self.ipc.broadcast_sync({"type": "mcts_update", "payload": self._get_mcts_nodes_ui_payload()})
                    last_telemetry_broadcast = current_time

                if current_time - last_discovery_broadcast > 12.0:
                    try:
                        disc = discover_identity()
                        self.history_store.save_discovery(
                            disc["base_identity"], disc["substitution"], disc["lhs"], disc["rhs"], disc["verified_equal"]
                        )
                        self.ipc.broadcast_sync({"type": "discovery", "status": "ok", **disc})
                    except Exception as e:
                        logger.debug(f"Live discovery broadcast skipped: {e}")
                    last_discovery_broadcast = current_time

                self._stop_event.wait(0.1)

            except ContextExhaustionError:
                logger.warning("Cognitive context exhausted — resetting context window.")
                self.cognitive.reset_context()
            except Exception as e:
                logger.error(f"Orchestrator unhandled exception at epoch {epoch}: {e}", exc_info=True)
                gc.collect()
                self._stop_event.wait(1.0)

        logger.debug("Exited research matrix gracefully.")

    def _get_mcts_nodes_ui_payload(self) -> list:
        """Serializes the MCTS graph into a flat representation suited for UI rendering."""
        ui_nodes = []
        visited = set()
        queue = [self.mcts_tree.root]
        
        while queue:
            node = queue.pop(0)
            node_id = str(id(node))
            if node_id in visited:
                continue
            visited.add(node_id)
            
            parent = node.parent() if node.parent else None
            parent_id = str(id(parent)) if parent else None
            
            if parent is None:
                status = "frontier"
            else:
                status = self._node_statuses.get(node.state_hash, "frontier")
                
            ui_nodes.append({
                "id": node_id,
                "label": node.state_hash,
                "status": status,
                "parentId": parent_id
            })
            
            for child in node.children:
                queue.append(child)
                
        return ui_nodes
