# TrueMath Innovator

**TrueMath Innovator** is a desktop app for Windows that helps students and math enthusiasts solve math problems with exact results and explore famous math conjectures. Exact calculations are done by real code (SymPy and Lean 4), not guessed by an AI.

Available on the Microsoft Store.

---

## Features

- **Exact Math Solver**: derivatives, integrals, equations, simplify and factor, computed exactly with SymPy running locally on your PC.
- **AI Answers**: conceptual questions are answered by an AI model (via Groq or OpenRouter). Always double-check AI answers.
- **Photo / Screenshot Solve**: paste a screenshot of a math problem and get a solution.
- **Conjecture Checker**: tests famous conjectures (for example Collatz) over a number range using real computation. These tests do not prove anything new; they only check a finite range.
- **Hard Problem Solver**: runs well-known algorithms such as Dijkstra, Miller-Rabin, Pollard's rho and baby-step giant-step.
- **Live Math Discoveries**: generates new versions of known identities and verifies each one with SymPy.
- **OEIS Check**: looks up number sequences in the OEIS database.
- **Recent Papers**: shows recent math research papers from arXiv.org.
- **MCTS Decision Tree and Lean 4 Truth Ratio**: a visual view of the search process and the proofs checked with Lean 4.
- **Export**: save your results as `.md` or `.pdf`.

---

## Technical Details (for Microsoft Store certification)

TrueMath Innovator is a packaged desktop application (MSIX). It bundles its own math engine and runs it on the user's PC.

### Capabilities used

| Capability | Why it is needed |
|---|---|
| `runFullTrust` | The app is a Win32 desktop application. It starts its bundled Python (SymPy) engine and a local dashboard server on 127.0.0.1 (this computer only), and runs the Lean 4 theorem prover (if installed by the user) as a normal local process under the user's own account. |
| `internetClient` | The app connects to the internet to call the Groq and OpenRouter APIs (AI answers), arXiv.org (research papers) and OEIS (number sequences). |

The app does **not** install or run any Windows service. It does **not** use `localSystemServices` or `packagedServices`, and it does not need administrator rights.

### What runs locally

- SymPy computation
- Lean 4 proof checking (requires Lean 4 to be installed on the PC; the app works without it, but proof checking is disabled)
- Conjecture checks and the Hard Problem Solver

### What uses the internet

- AI answers and screenshot solving (Groq and OpenRouter APIs)
- Recent papers (arXiv.org)
- Sequence lookup (OEIS)

---

## Privacy

Short version:

- Math calculations run on your device.
- When you use the AI features, your question (or screenshot) is sent to the Groq or OpenRouter API to get an answer.
- When you use OEIS or arXiv features, the sequence or search text you enter is sent to those websites.
- We do not collect your name, email, or account data, and we do not sell your data.

Full details: [PRIVACY.md](PRIVACY.md)

---

## Important Notes

- AI answers can be wrong. Conceptual answers should always be double-checked.
- The Conjecture Checker tests a limited range of numbers. Finding no counterexample is expected and is not a mathematical proof.
- The `crypto` category of the Hard Problem Solver is for teaching only and is not secure.

---

## Support

If you need help, have found a bug, or have a suggestion, please contact us:

- **Support email:** dijasniassuh8@gmail.com
- **Bug reports and questions:** open an [Issue](https://github.com/Sajidsaj/True-Math/issues) on this repository.

We try to reply within a few days.

---

## About

Developed by Sajid Abro.

&copy; 2026 Sajid Abro. All rights reserved.
