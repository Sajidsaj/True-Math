/**
 * App.jsx — TrueMath Visual Dashboard
 * ------------------------------------------------------------
 * Central application bootstrap.
 * - Connects natively to the Python IPC backend via WebSocket.
 * - Distributes real-time telemetry data to child components.
 * - Handles connection state, reconnection backoff, and UI layout.
 *
 * Integration:
 *   Relies on Python `ipc_handler.py` serving a WebSocket at
 *   ws://127.0.0.1:9999/ws (or as configured).
 * ------------------------------------------------------------
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';

/** SECURITY: only allow http/https URLs through to an href attribute.
 * arXiv and web-search results are external, untrusted data — without this,
 * a malicious result could return a "link" like "javascript:alert(1)"
 * which the browser would execute if the user clicks it. React does not
 * sanitize href by default, so this check is required. */
function safeUrl(url) {
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') return url;
  } catch {
    // fall through to reject
  }
  return '#';
}
import katex from 'katex';
import 'katex/dist/katex.min.css';

/** Renders a LaTeX string as proper math notation using KaTeX. Falls back
 * to showing the raw text if the LaTeX fails to parse (never crashes). */
function MathTeX({ latex, fallback }) {
  if (!latex) return fallback ? <span>{fallback}</span> : null;
  try {
    const html = katex.renderToString(latex, { throwOnError: false, displayMode: false, trust: false });
    return <span className="math-tex" dangerouslySetInnerHTML={{ __html: html }} />;
  } catch {
    return <span>{fallback || latex}</span>;
  }
}

/** Lightweight inline SVG line chart — no extra chart library needed.
 * Draws f(x) over the sampled points and marks any x-axis crossings
 * (roots) with a dot, so a solved equation's answer is visually confirmed. */
function MiniGraph({ graph }) {
  if (!graph || !graph.points || graph.points.length < 2) return null;
  const W = 320, H = 140, PAD = 8;
  const xs = graph.points.map((p) => p[0]);
  const ys = graph.points.map((p) => p[1]);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys, 0), yMax = Math.max(...ys, 0);
  const sx = (x) => PAD + ((x - xMin) / (xMax - xMin || 1)) * (W - 2 * PAD);
  const sy = (y) => H - PAD - ((y - yMin) / (yMax - yMin || 1)) * (H - 2 * PAD);

  const pathD = graph.points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${sx(p[0]).toFixed(1)} ${sy(p[1]).toFixed(1)}`).join(' ');

  // Find approximate zero-crossings (roots) for marker dots
  const roots = [];
  for (let i = 1; i < graph.points.length; i++) {
    const [x0, y0] = graph.points[i - 1];
    const [x1, y1] = graph.points[i];
    if (y0 === 0) roots.push(x0);
    else if (y0 * y1 < 0) roots.push(x0 + (x1 - x0) * (-y0 / (y1 - y0)));
  }

  return (
    <svg width={W} height={H} className="qa-graph" viewBox={`0 0 ${W} ${H}`}>
      {yMin < 0 && yMax > 0 && (
        <line x1={PAD} x2={W - PAD} y1={sy(0)} y2={sy(0)} className="qa-graph-axis" />
      )}
      <path d={pathD} className="qa-graph-line" fill="none" />
      {roots.map((r, i) => (
        <circle key={i} cx={sx(r)} cy={sy(0)} r={4} className="qa-graph-root" />
      ))}
    </svg>
  );
}
import { BrainPowerTelemetry } from './components/BrainPowerTelemetry';
import { MCTSTreeLayout }      from './components/MCTSTreeLayout';
import { APP_VERSION } from './version';

const RECONNECT_MS = 3000; // Reconnect every 3 seconds on drop

function resolveRuntimeConfig() {
  return window.__TRUEMATH_CONFIG__ ?? {};
}

function buildWebSocketUrl() {
  const runtimeConfig = resolveRuntimeConfig();
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = runtimeConfig.ipcHost || window.location.hostname || '127.0.0.1';
  const port = runtimeConfig.ipcPort || 9999;
  const path = runtimeConfig.ipcPath || '/ws';
  return `${protocol}//${host}:${port}${path}`;
}

export default function App() {
  const [telemetry,  setTelemetry]  = useState(null);
  const [mctsNodes,  setMctsNodes]  = useState([]);
  const [connected,  setConnected]  = useState(false);
  const [statusMsg,  setStatusMsg]  = useState('Connecting to AI Engine…');

  // ── Problem topic selector state ───────────────────────────
  const [problemCatalog, setProblemCatalog] = useState({});
  const [selectedProblem, setSelectedProblem] = useState('Riemann Hypothesis');
  const [customTopic, setCustomTopic] = useState('');
  const [topicStatus, setTopicStatus] = useState('');

  // ── Live arXiv research feed state ─────────────────────────
  const [arxivPapers, setArxivPapers] = useState([]);
  const [arxivLoading, setArxivLoading] = useState(false);
  const [arxivMessage, setArxivMessage] = useState('');

  // ── Live discovery feed state ──────────────────────────────
  const [discoveries, setDiscoveries] = useState([]); // most recent first

  // ── OEIS lookup state ───────────────────────────────────────
  const [oeisInput, setOeisInput] = useState('');
  const [oeisResult, setOeisResult] = useState(null);
  const [oeisLoading, setOeisLoading] = useState(false);

  // ── Hard Problem Solver state ──────────────────────────────
  const [hpCategories, setHpCategories] = useState({});
  const [hpCategory, setHpCategory] = useState('number_theory');
  const [hpOperation, setHpOperation] = useState('gcd');
  const [hpParams, setHpParams] = useState('{"a": 48, "b": 18}');
  const [hpResult, setHpResult] = useState(null);
  const [hpRunning, setHpRunning] = useState(false);

  // ── Conjecture checker state ────────────────────────────────
  const [conjectureChoice, setConjectureChoice] = useState('collatz');
  const [conjectureLimit, setConjectureLimit] = useState(100000);
  const [conjectureRunning, setConjectureRunning] = useState(false);
  const [conjectureResult, setConjectureResult] = useState(null);

  // ── Q&A box state ──────────────────────────────────────────
  const [question,  setQuestion]  = useState('');
  const [qaHistory, setQaHistory] = useState([]); // most recent first
  const [asking,    setAsking]    = useState(false);
  const lastQuestionRef = useRef('');
  const [exportStatus, setExportStatus] = useState('');
  const [unmatchedQueries, setUnmatchedQueries] = useState([]);
  const [showUnmatched, setShowUnmatched] = useState(false);
  const [agentMode, setAgentMode] = useState(false);
  const [userProvider, setUserProvider] = useState('');
  const [userApiKey, setUserApiKey] = useState('');
  const [showKeyInput, setShowKeyInput] = useState(false);

  // Debug log
  console.log('Runtime Config:', resolveRuntimeConfig());
  console.log('WebSocket URL:', buildWebSocketUrl());

  // Stable ref for the websocket — avoids stale closure in effect
  const wsRef            = useRef(null);
  // BUG-14 FIX: Track the reconnect timer so it can be cancelled on unmount.
  // Without this, every onclose fires a new setTimeout even after the component
  // is destroyed, creating an infinite timer chain that leaks browser memory.
  const reconnectTimerRef = useRef(null);

  /** Parses incoming JSON messages from the Python backend. */
  const handleMessage = useCallback((raw) => {
    try {
      const msg = JSON.parse(raw);
      if (msg.type === 'telemetry')   setTelemetry(msg.payload);
      if (msg.type === 'mcts_update') setMctsNodes(msg.payload ?? []);
      if (msg.type === 'problem_catalog') {
        setProblemCatalog(msg.problems ?? {});
        if (msg.current_topic) setSelectedProblem(msg.current_topic);
      }
      if (msg.type === 'topic_response') {
        setTopicStatus(msg.status === 'ok' ? `Ab explore ho raha hai: ${msg.topic}` : msg.message);
      }
      if (msg.type === 'arxiv_result') {
        setArxivLoading(false);
        setArxivMessage(msg.message || '');
        setArxivPapers(msg.status === 'ok' ? (msg.papers || []) : []);
      }
      if (msg.type === 'discovery' && msg.status === 'ok') {
        setDiscoveries((prev) => [
          {
            baseIdentity: msg.base_identity,
            substitution: msg.substitution,
            lhs: msg.lhs,
            rhs: msg.rhs,
            verified: msg.verified_equal,
          },
          ...prev,
        ].slice(0, 15));
      }
      if (msg.type === 'conjecture_result') {
        setConjectureRunning(false);
        setConjectureResult(msg.status === 'ok' ? msg : { summary: msg.message, counterexample_found: false });
      }
      if (msg.type === 'oeis_result') {
        setOeisLoading(false);
        setOeisResult(msg);
      }
      if (msg.type === 'export_result') {
        setExportStatus(msg.status === 'ok' ? `Saved: ${msg.path}` : msg.message);
      }
      if (msg.type === 'unmatched_queries') {
        setUnmatchedQueries(msg.queries || []);
      }
      if (msg.type === 'agent_response') {
        setAsking(false);
        setQaHistory((prev) => [
          {
            question: msg.question ?? lastQuestionRef.current,
            answer: msg.status === 'ok' ? msg.answer : msg.message,
            isError: msg.status !== 'ok',
            source: 'agent',
            toolCalls: msg.tool_calls,
          },
          ...prev,
        ].slice(0, 20));
      }
      if (msg.type === 'hard_problem_categories') {
        setHpCategories(msg.categories ?? {});
      }
      if (msg.type === 'hard_problem_result') {
        setHpRunning(false);
        setHpResult(msg);
      }
      if (msg.type === 'qa_response') {
        setAsking(false);
        setQaHistory((prev) => [
          {
            question: msg.question ?? lastQuestionRef.current,
            answer: msg.status === 'ok' ? msg.answer : msg.message,
            answerLatex: msg.answer_latex,
            isError: msg.status !== 'ok',
            webFallback: msg.web_fallback,
            source: msg.source, // 'computed' | 'llm' | undefined (error)
            steps: msg.steps,
            verified: msg.verified,
            verifiedOk: msg.verified_ok,
            graph: msg.graph,
            agreement: msg.agreement,
            attempts: msg.attempts,
          },
          ...prev,
        ].slice(0, 20));
      }
    } catch {
      // Silently discard malformed payloads from the backend
    }
  }, []);

  /** Creates and registers a WebSocket connection to the IPC server. */
  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return;

    const ws = new WebSocket(buildWebSocketUrl());
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setStatusMsg('Live — AI Engine Online');
      ws.send(JSON.stringify({ action: 'get_problem_catalog', data: {} }));
      ws.send(JSON.stringify({ action: 'get_hard_problem_categories', data: {} }));
    };

    ws.onmessage = (e) => handleMessage(e.data);

    ws.onclose = () => {
      setConnected(false);
      setStatusMsg('Reconnecting…');
      // BUG-14 FIX: Store timer ID so cleanup can cancel it on unmount
      reconnectTimerRef.current = setTimeout(connect, RECONNECT_MS);
    };

    ws.onerror = () => {
      setStatusMsg('IPC Bridge Error — retrying…');
      ws.close();
    };
  }, [handleMessage]);

  const HP_SAMPLE_PARAMS = {
    gcd: '{"a": 48, "b": 18}', lcm: '{"a": 4, "b": 6}',
    extended_gcd: '{"a": 35, "b": 15}', mod_inverse: '{"a": 3, "m": 11}',
    mod_pow: '{"base": 2, "exp": 10, "mod": 1000}', is_prime: '{"n": 97}',
    prime_factors: '{"n": 123456789}', crt: '{"remainders": [2,3,2], "moduli": [3,5,7]}',
    diophantine: '{"a": 6, "b": 10, "c": 4}',
    linear_program: '{"c": [-3,-5], "A_ub": [[1,0],[0,2],[3,2]], "b_ub": [4,12,18]}',
    shortest_path: '{"graph": {"A":{"B":4,"C":1},"C":{"B":1,"D":5},"B":{"D":1},"D":{}}, "start":"A", "end":"D"}',
    knapsack: '{"weights": [2,3,4,5], "values": [3,4,5,6], "capacity": 5}',
    factor: '{"n": 9797}', discrete_log: '{"g": 5, "h": 8, "p": 23}',
    rsa_keygen: '{"bits": 16}', rsa_encrypt: '{"message": 42, "e": 65537, "n": 2696152567}',
    rsa_decrypt: '{"cipher": 123, "d": 444329233, "n": 2696152567}',
    n_choose_r: '{"n": 10, "r": 3}', n_permute_r: '{"n": 10, "r": 3}',
    fibonacci: '{"n": 50}', catalan: '{"n": 10}', summary: '{"n": 10, "r": 3}',
    generate_keypair: '{"key_size": 2048}',
    encrypt: '{"message": "hello", "public_key_pem": "-----BEGIN PUBLIC KEY-----..."}',
    decrypt: '{"ciphertext": "...", "private_key_pem": "-----BEGIN PRIVATE KEY-----..."}',
    sign: '{"message": "hello", "private_key_pem": "-----BEGIN PRIVATE KEY-----..."}',
    verify: '{"message": "hello", "signature": "...", "public_key_pem": "-----BEGIN PUBLIC KEY-----..."}',
    classify_structure: '{"elements": [0,1,2,3], "table": {"0":{"0":0,"1":1,"2":2,"3":3},"1":{"0":1,"1":2,"2":3,"3":0},"2":{"0":2,"1":3,"2":0,"3":1},"3":{"0":3,"1":0,"2":1,"3":2}}}',
    classify_ring: '{"elements": [0,1,2,3], "add_table": {"0":{"0":0,"1":1,"2":2,"3":3},"1":{"0":1,"1":2,"2":3,"3":0},"2":{"0":2,"1":3,"2":0,"3":1},"3":{"0":3,"1":0,"2":1,"3":2}}, "mul_table": {"0":{"0":0,"1":0,"2":0,"3":0},"1":{"0":0,"1":1,"2":2,"3":3},"2":{"0":0,"1":2,"2":0,"3":2},"3":{"0":0,"1":3,"2":2,"3":1}}}',
    convert: '{"value": 100, "from_unit": "km/h", "to_unit": "m/s"}',
    convert_temperature: '{"value": 100, "from_unit": "celsius", "to_unit": "fahrenheit"}',
    list_units: '{}',
    get_constant: '{"name": "speed_of_light"}',
    list_constants: '{}',
    dot_product: '{"a": [1,2,3], "b": [4,5,6]}',
    cross_product: '{"a": [1,0,0], "b": [0,1,0]}',
    magnitude: '{"v": [3,4]}',
    normalize: '{"v": [3,4]}',
    angle_between: '{"a": [1,0], "b": [0,1]}',
    kinematics: '{"u": 0, "a": 9.8, "t": 2}',
    kinetic_energy: '{"mass": 2, "velocity": 10}',
    potential_energy: '{"mass": 2, "height": 10}',
    momentum: '{"mass": 2, "velocity": 10}',
    newtons_second_law: '{"mass": 5, "acceleration": 2}',
    analyze_complexity: '{"code": "def f(arr):\\n    for i in arr:\\n        for j in arr:\\n            print(i,j)"}',
    lorentz_factor: '{"velocity": 240000000}',
    time_dilation: '{"proper_time": 1, "velocity": 240000000}',
    length_contraction: '{"proper_length": 10, "velocity": 240000000}',
    relativistic_momentum: '{"mass": 1, "velocity": 240000000}',
    relativistic_energy: '{"mass": 1, "velocity": 0}',
    velocity_addition: '{"v1": 200000000, "v2": 200000000}',
    schwarzschild_radius: '{"mass": 1.989e30}',
    gravitational_time_dilation: '{"mass": 5.972e24, "radius": 6371000}',
    gravitational_redshift: '{"mass": 5.972e24, "emitted_radius": 6371000, "observed_radius": 42164000}',
    explore: '{"n": 8128, "include_oeis": false}',
  };

  const changeHpCategory = useCallback((cat) => {
    setHpCategory(cat);
    const firstOp = (hpCategories[cat] || [])[0];
    if (firstOp) {
      setHpOperation(firstOp);
      setHpParams(HP_SAMPLE_PARAMS[firstOp] || '{}');
    }
  }, [hpCategories]);

  const changeHpOperation = useCallback((op) => {
    setHpOperation(op);
    setHpParams(HP_SAMPLE_PARAMS[op] || '{}');
  }, []);

  /** Runs a hard-problem solver operation (number theory / optimization / crypto / combinatorics). */
  const runHardProblem = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    let parsedParams;
    try {
      parsedParams = JSON.parse(hpParams);
    } catch {
      setHpResult({ status: 'error', message: 'Params valid JSON nahi hai — check karo syntax.' });
      return;
    }
    setHpRunning(true);
    setHpResult(null);
    wsRef.current.send(JSON.stringify({
      action: 'solve_hard_problem',
      data: { category: hpCategory, operation: hpOperation, params: parsedParams },
    }));
  }, [hpCategory, hpOperation, hpParams]);

  /** Looks up a number sequence against the real OEIS database. */
  const lookupOeis = useCallback(() => {
    const seq = oeisInput.trim();
    if (!seq || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setOeisLoading(true);
    setOeisResult(null);
    wsRef.current.send(JSON.stringify({ action: 'oeis_lookup', data: { sequence: seq } }));
  }, [oeisInput]);

  /** Requests a real numeric conjecture check (Collatz/Goldbach/Twin Primes). */
  const runConjectureCheck = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setConjectureRunning(true);
    setConjectureResult(null);
    wsRef.current.send(JSON.stringify({
      action: 'run_conjecture_check',
      data: { conjecture: conjectureChoice, limit: conjectureLimit },
    }));
  }, [conjectureChoice, conjectureLimit]);

  /** Requests one fresh identity discovery immediately (also arrive automatically every ~12s). */
  const discoverNow = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: 'discover', data: {} }));
  }, []);

  /** Fetches the log of questions the keyword router couldn't handle (fell through to LLM) — the honest 'learning' review list. */
  const toggleUnmatchedQueries = useCallback(() => {
    if (!showUnmatched && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'get_unmatched_queries', data: {} }));
    }
    setShowUnmatched((prev) => !prev);
  }, [showUnmatched]);

  /** Exports saved Q&A history + discoveries to a file on disk. */
  const exportHistory = useCallback((format) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: 'export_history', data: { format } }));
  }, []);

  /** Searches real, current arXiv preprints for the active topic (or a custom query). */
  const searchArxiv = useCallback((query) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setArxivLoading(true);
    setArxivPapers([]);
    wsRef.current.send(JSON.stringify({ action: 'search_arxiv', data: { query: query || selectedProblem } }));
  }, [selectedProblem]);

  /** Switches the backend's autonomous exploration to a new problem. */
  const sendTopic = useCallback(() => {
    const topic = (customTopic.trim() || selectedProblem).trim();
    if (!topic) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setTopicStatus('AI Engine se connection nahi hai — thoda ruk kar dobara try karein.');
      return;
    }
    const description = customTopic.trim() ? '' : (problemCatalog[selectedProblem] ?? '');
    setTopicStatus('Switching…');
    wsRef.current.send(JSON.stringify({ action: 'set_topic', data: { topic, description } }));
    setCustomTopic('');
  }, [customTopic, selectedProblem, problemCatalog]);

  /** Sends the current question to the Python backend over the existing WS. */
  const askQuestion = useCallback(() => {
    const q = question.trim();
    if (!q) return;
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setQaHistory((prev) => [
        { question: q, answer: 'AI Engine se connection nahi hai — thoda ruk kar dobara try karein.', isError: true },
        ...prev,
      ]);
      return;
    }
    lastQuestionRef.current = q;
    setAsking(true);
    const payload = { question: q };
    if (userProvider && userApiKey) {
      payload.user_provider = userProvider;
      payload.user_api_key = userApiKey;
    }
    wsRef.current.send(JSON.stringify({ action: agentMode ? 'ask_agent' : 'ask_question', data: payload }));
    setQuestion('');
  }, [question, agentMode, userProvider, userApiKey]);

  const handleQuestionKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  }, [askQuestion]);

  // Initialize WebSocket on mount; clean up (including pending timers) on unmount
  useEffect(() => {
    connect();
    return () => {
      // Cancel any pending reconnect timer before tearing down
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return (
    <div className="dashboard-layout">

      {/* ── Header ─────────────────────────────────────── */}
      <header className="dash-header glass-card">
        <div className="logo">True<span>Math</span> Innovator</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className={`ws-badge ${connected ? 'connected' : 'disconnected'}`}>
            {connected ? '● LIVE' : '○ OFFLINE'}
          </span>
          <div className="status-pill">
            <span className="dot" />
            {statusMsg}
          </div>
        </div>
      </header>

      {/* ── Problem / Topic Picker ─────────────────────── */}
      <section className="topic-panel glass-card">
        <h2>Kaunsa Problem Explore Karein?</h2>
        <p className="topic-disclaimer">
          ⚠️ Ye tool famous unsolved problems ke ird-gird patterns dhoondta aur numerically test karta hai —
          ye <strong>proof nahi banata</strong> aur inn problems ko "solve" nahi karega (agar ho sakta,
          duniya ke top mathematicians pehle kar chuke hote). Isay ek exploration/learning tool samjho.
        </p>
        <div className="topic-controls">
          <select
            className="topic-select"
            value={selectedProblem}
            onChange={(e) => setSelectedProblem(e.target.value)}
          >
            {Object.keys(problemCatalog).length > 0
              ? Object.keys(problemCatalog).map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))
              : <option value="Riemann Hypothesis">Riemann Hypothesis</option>}
          </select>
          <input
            className="topic-custom-input"
            type="text"
            placeholder="...ya apna khud ka problem likho"
            value={customTopic}
            onChange={(e) => setCustomTopic(e.target.value)}
          />
          <button className="qa-submit" onClick={sendTopic}>Start Exploring</button>
        </div>
        {problemCatalog[selectedProblem] && !customTopic.trim() && (
          <p className="topic-desc">{problemCatalog[selectedProblem]}</p>
        )}
        {topicStatus && <p className="topic-status">{topicStatus}</p>}
        {telemetry?.current_topic && (
          <p className="topic-active">Abhi active: <strong>{telemetry.current_topic}</strong></p>
        )}

        <div className="oeis-tool">
          <div className="discovery-header">
            <p className="topic-desc" style={{ margin: 0 }}>Real-time arXiv.org se current research dekho (live internet):</p>
            <button className="qa-submit small" onClick={() => searchArxiv()} disabled={arxivLoading}>
              {arxivLoading ? 'Searching…' : 'Recent Papers'}
            </button>
          </div>
          {arxivMessage && <p className="topic-desc">{arxivMessage}</p>}
          <div className="qa-history">
            {arxivPapers.map((p, idx) => (
              <div key={idx} className="qa-item">
                <div className="qa-question">
                  <a href={safeUrl(p.link)} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit' }}>{p.title}</a>
                </div>
                <div className="qa-answer">
                  {p.authors?.join(', ')} — {p.published}
                  <br />{p.summary}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── MCTS Tree ──────────────────────────────────── */}
      <MCTSTreeLayout nodes={mctsNodes} />

      {/* ── Brain Power Telemetry ──────────────────────── */}
      <BrainPowerTelemetry data={telemetry} />

      {/* ── Conjecture Checker ─────────────────────────── */}
      <section className="topic-panel conjecture-panel glass-card">
        <h2>Conjecture Checker (Real Number-Crunching)</h2>
        <p className="topic-disclaimer">
          ⚠️ Ye real brute-force computation hai (LLM nahi) — famous conjectures ko ek range tak
          test karta hai. Ye conjectures already professionally hazaron guna bade range tak verified hain,
          isliye "no counterexample" milna normal/expected hai — koi naya proof nahi banta.
        </p>
        <div className="topic-controls">
          <select className="topic-select" value={conjectureChoice} onChange={(e) => setConjectureChoice(e.target.value)}>
            <option value="collatz">Collatz Conjecture</option>
            <option value="goldbach">Goldbach Conjecture</option>
            <option value="twin_primes">Twin Prime Conjecture</option>
            <option value="perfect_numbers">Perfect Numbers (Odd Perfect Number question)</option>
            <option value="mersenne_primes">Mersenne Primes (infinitude question)</option>
          </select>
          <input
            className="topic-custom-input"
            type="number"
            min="100" max="2000000" step="1000"
            value={conjectureLimit}
            onChange={(e) => setConjectureLimit(Number(e.target.value))}
            style={{ maxWidth: 160 }}
          />
          <button className="qa-submit" onClick={runConjectureCheck} disabled={conjectureRunning}>
            {conjectureRunning ? 'Checking…' : 'Run Check'}
          </button>
        </div>
        {conjectureResult && (
          <div className={`qa-item ${conjectureResult.counterexample_found ? 'error' : ''}`}>
            <div className="qa-question">
              {conjectureResult.conjecture}
              {conjectureResult.counterexample_found
                ? <span className="qa-badge ai">⚠️ Counterexample?!</span>
                : <span className="qa-badge exact">✓ Verified in range</span>}
            </div>
            <div className="qa-answer">{conjectureResult.summary}</div>
          </div>
        )}
      </section>

      {/* ── Live Math Discoveries ──────────────────────── */}
      <section className="discovery-panel glass-card">
        <div className="discovery-header">
          <h2>Live Math Discoveries</h2>
          <button className="qa-submit small" onClick={discoverNow}>Discover Now</button>
        </div>
        <p className="topic-disclaimer">
          ⚠️ Ye <strong>known identities</strong> (Pythagorean, double-angle, log/exp rules waghera) ke
          naye — pehle kahin likhe na hue — versions banata hai, random expressions substitute karke, aur
          har ek ko <strong>SymPy se exactly verify</strong> karta hai. Ye naya research-level math nahi hai,
          balke ek verified "generative math" exploration hai — har jawab 100% proven hai, guessed nahi.
        </p>
        {discoveries.length === 0 && <p className="qa-empty-hint">Pehli discovery ~12 second mein aayegi, ya "Discover Now" click karo.</p>}
        <div className="qa-history">
          {discoveries.map((d, idx) => (
            <div key={idx} className={`qa-item ${!d.verified ? 'error' : ''}`}>
              <div className="qa-question">
                {d.baseIdentity}
                <span className={`qa-badge ${d.verified ? 'exact' : 'ai'}`}>{d.verified ? '✓ Verified' : '✗ Failed'}</span>
              </div>
              <div className="qa-answer">{d.lhs} = {d.rhs}</div>
              <ol className="qa-steps"><li>Substitution used: u = {d.substitution}</li></ol>
            </div>
          ))}
        </div>

        <div className="oeis-tool">
          <p className="topic-desc">OEIS (real database) mein apni sequence check karo:</p>
          <div className="topic-controls">
            <input
              className="topic-custom-input"
              type="text"
              placeholder="1, 1, 2, 3, 5, 8"
              value={oeisInput}
              onChange={(e) => setOeisInput(e.target.value)}
            />
            <button className="qa-submit small" onClick={lookupOeis} disabled={oeisLoading}>
              {oeisLoading ? 'Searching…' : 'OEIS Check'}
            </button>
          </div>
          {oeisResult && (
            <div className={`qa-item ${oeisResult.status !== 'ok' ? 'error' : ''}`}>
              <div className="qa-answer">{oeisResult.message}</div>
              {oeisResult.matches && oeisResult.matches.map((m, i) => (
                <div key={i} className="qa-steps">• {m.oeis_id}: {m.name}</div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── Hard Problem Solver (Number Theory / Optimization / Crypto / Combinatorics) ── */}
      <section className="topic-panel hp-panel glass-card">
        <h2>Hard Problem Solver</h2>
        <p className="topic-disclaimer">
          ⚠️ Real algorithms (Dijkstra, LP, Miller-Rabin, Pollard's rho, baby-step giant-step, DP) —
          exact/proven, na ke LLM guess. <strong>"crypto"</strong> category sirf teaching-demo hai (toy-sized,
          NOT secure). <strong>"real_crypto"</strong> category genuinely production-grade hai (real 2048-bit
          RSA, OAEP padding, `cryptography` library/OpenSSL se) — safe use karne layak.
          Sab kuch <code>src/math_engine/hard_problem_dispatcher.py</code> se library ke taur pe bhi import ho sakta hai.
          <strong>"algebra_sandbox"</strong> category se apna khud ka custom rule/universe define karo — ye mechanically
          verify karega ke wo group/ring/field hai ya nahi (genuinely tumhare banaye rules pe based, sach mein compute hota hai).
        </p>
        <div className="topic-controls">
          <select className="topic-select" value={hpCategory} onChange={(e) => changeHpCategory(e.target.value)}>
            {Object.keys(hpCategories).map((cat) => <option key={cat} value={cat}>{cat}</option>)}
          </select>
          <select className="topic-select" value={hpOperation} onChange={(e) => changeHpOperation(e.target.value)}>
            {(hpCategories[hpCategory] || []).map((op) => <option key={op} value={op}>{op}</option>)}
          </select>
          <button className="qa-submit" onClick={runHardProblem} disabled={hpRunning}>
            {hpRunning ? 'Solving…' : 'Solve'}
          </button>
        </div>
        <textarea
          className="qa-input"
          rows={2}
          value={hpParams}
          onChange={(e) => setHpParams(e.target.value)}
          placeholder='Params as JSON, e.g. {"a": 48, "b": 18}'
        />
        {hpResult && (
          <div className={`qa-item ${hpResult.status !== 'ok' ? 'error' : ''}`}>
            <div className="qa-answer">
              <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                {JSON.stringify(hpResult.status === 'ok' ? hpResult.result : hpResult.message, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </section>

      {/* ── Ask Your Own Math Question ──────────────────── */}
      <section className="qa-panel glass-card">
        <div className="discovery-header">
          <h2>Apna Math Sawal Poochein</h2>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="qa-submit small" onClick={() => exportHistory('markdown')}>Export .md</button>
            <button className="qa-submit small" onClick={() => exportHistory('pdf')}>Export .pdf</button>
            <button className="qa-submit small" onClick={toggleUnmatchedQueries}>
              {showUnmatched ? 'Hide' : 'Unmatched Queries'}
            </button>
          </div>
        </div>
        {exportStatus && <p className="topic-status">{exportStatus}</p>}
        <label className="agent-toggle">
          <input type="checkbox" checked={agentMode} onChange={(e) => setAgentMode(e.target.checked)} />
          <span>
            Agent Mode {agentMode ? '(ON)' : '(OFF)'} — compound sawal ke liye ("factor 360, then gcd it with 48, then
            determinant of [[2,1],[1,3]]"). LLM sirf decide karta hai KAUNSA tool call karna hai — asli calculation
            hamesha real Python code karta hai, LLM nahi. AI key chahiye.
          </span>
        </label>

        <div className="own-key-section">
          <button className="qa-submit small" onClick={() => setShowKeyInput((prev) => !prev)}>
            {showKeyInput ? 'Hide' : 'Use My Own API Key'}
          </button>
          {showKeyInput && (
            <div className="own-key-form">
              <p className="topic-desc">
                Agar tum public/shared TrueMath use kar rahe ho, apni khud ki free Groq/OpenRouter key daalo —
                ye sirf is browser session ke liye use hoti hai, kahin save nahi hoti (na file mein, na database mein).
                Khaali chhodo to server ki apni key use hogi.
              </p>
              <div className="topic-controls">
                <select className="topic-select" value={userProvider} onChange={(e) => setUserProvider(e.target.value)}>
                  <option value="">Server ki key use karo (default)</option>
                  <option value="groq">Meri Groq key</option>
                  <option value="openrouter">Meri OpenRouter key</option>
                </select>
                <input
                  className="topic-custom-input"
                  type="password"
                  placeholder="Apni API key yahan paste karo"
                  value={userApiKey}
                  onChange={(e) => setUserApiKey(e.target.value)}
                  disabled={!userProvider}
                />
              </div>
            </div>
          )}
        </div>
        {showUnmatched && (
          <div className="qa-item">
            <p className="topic-desc">
              Ye wo sawal hain jo keyword router pehchan nahi paya (isliye LLM ke paas gaye) —
              agar koi pattern baar-baar dikhe, wo naya keyword rule add karne ka signal hai.
            </p>
            {unmatchedQueries.length === 0
              ? <p className="qa-empty-hint">Abhi koi unmatched query nahi hai.</p>
              : unmatchedQueries.map((q, i) => <div key={i} className="qa-steps">{q}</div>)}
          </div>
        )}
        <div className="qa-input-row">
          <textarea
            className="qa-input"
            placeholder="Jaise: Derivative of sin(x)*x^2 kya hoga?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleQuestionKeyDown}
            rows={2}
          />
          <button
            className="qa-submit"
            onClick={askQuestion}
            disabled={asking || !question.trim()}
          >
            {asking ? 'Soch raha hai…' : 'Poochein'}
          </button>
        </div>

        {qaHistory.length === 0 && !asking && (
          <p className="qa-empty-hint">
            Equations, derivatives, integrals, simplify/factor jaise sawal <strong>exact compute</strong>{' '}
            hote hain (SymPy se, 100% sahi). Baaki conceptual sawal AI (phi3.5/Groq) se jawab dete hain —
            unko double-check zaroor karo.
          </p>
        )}

        <div className="qa-history">
          {qaHistory.map((item, idx) => (
            <div key={idx} className={`qa-item ${item.isError ? 'error' : ''}`}>
              <div className="qa-question">
                Q: {item.question}
                {item.source === 'computed' && <span className="qa-badge exact">✓ Exact</span>}
                {item.source === 'llm' && (
                  <span className="qa-badge ai">
                    AI ({item.attempts && item.agreement != null ? `${Math.round(item.agreement * item.attempts)}/${item.attempts} agreed` : 'double-check karein'})
                  </span>
                )}
              </div>
              <div className="qa-answer">
                {item.answerLatex ? <MathTeX latex={item.answerLatex} fallback={item.answer} /> : item.answer}
              </div>

              {item.steps && item.steps.length > 0 && (
                <ol className="qa-steps">
                  {item.steps.map((s, i) => <li key={i}>{s}</li>)}
                </ol>
              )}

              {item.verified && (
                <div className={`qa-verified ${item.verifiedOk === false ? 'fail' : 'pass'}`}>
                  {item.verifiedOk === false ? '⚠️ ' : '🔍 '}{item.verified}
                </div>
              )}

              {item.graph && <MiniGraph graph={item.graph} />}

              {item.toolCalls && item.toolCalls.length > 0 && (
                <div className="qa-tool-calls">
                  <p className="topic-desc">Agent ne ye REAL tools call kiye (LLM ne calculate nahi kiya):</p>
                  {item.toolCalls.map((tc, i) => (
                    <div key={i} className="qa-steps">
                      <code>{tc.tool}({JSON.stringify(tc.arguments)})</code> → {JSON.stringify(tc.result.result ?? tc.result)}
                    </div>
                  ))}
                </div>
              )}

              {item.webFallback && item.webFallback.length > 0 && (
                <div className="qa-web-fallback">
                  <p className="topic-desc">AI available nahi tha — DuckDuckGo se real search results (AI-generated nahi):</p>
                  {item.webFallback.map((r, i) => (
                    <div key={i} className="qa-web-result">
                      <a href={safeUrl(r.link)} target="_blank" rel="noopener noreferrer">{r.title}</a>
                      <p>{r.snippet}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── Status Bar ─────────────────────────────────── */}
      <footer className="status-bar glass-card">
        <span>{`TrueMath v${APP_VERSION}`}</span>
        <span className="sep">·</span>
        <span>Mode: Autonomous Research</span>
        <span className="sep">·</span>
        <span>Formal Verifier: Lean 4</span>
        <span className="sep">·</span>
        <span style={{ color: connected ? 'var(--accent-3)' : 'var(--accent-err)' }}>
          {connected ? 'IPC Connected' : 'IPC Disconnected'}
        </span>
      </footer>

    </div>
  );
}
