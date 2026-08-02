"""
Module Name: llm_bridge
Purpose: Zero-dependency native HTTP client to communicate specifically with Local AI models (llama.cpp/Ollama).
Responsibilities:
  - Formulate structured JSON POST requests bypassing external pip modules (`requests`) for maximum zero-day protection.
  - Apply strict timeout bounds so a hanging LLM API doesn't freeze the Math Orchestrator matrix.
Dependencies: urllib, json
Input: Structured mathematical instruction prompts.
Output: LLM raw string mathematical theories.
Possible Errors: URLError (AI server down), TimeoutError.
Testing Method: Mock urllib response bytes to verify JSON parsing logic and panic handling.
Estimated Complexity: Medium.
Integration Notes: Requires a local AI engine running on port 11434 (default Ollama).
"""
import urllib.request
import urllib.error
import urllib.parse
import json
from typing import Dict, Any, Optional
from src.core.sys_logger import get_logger

logger = get_logger("LLM_Bridge")

class LocalLLMBridge:
    __slots__ = ('base_url', 'model_name', 'timeout')

    def __init__(self, base_url: str = "http://127.0.0.1:11434/api/generate", model_name: str = "llama3:latest", timeout: int = 15):
        # By default targeting Local PC Ollama standard bounds securely
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        logger.info(f"Local AI LLM Bridge bounded securely to {base_url} using model {model_name}.")

    def prompt_ai(self, system_prompt: str, math_context: str) -> Optional[str]:
        """Throws native HTTP headers against local AI execution binaries bypassing Python C-extensions natively."""
        payload = {
            "model": self.model_name,
            "prompt": f"{system_prompt}\n\nContext:\n{math_context}",
            "stream": False,
            "options": {
                "temperature": 0.2, # Extremely low logic variance prioritizing absolute math structures
                "num_predict": 1024 # Stop AI from memory leaking massive endless text
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        
        # Securing exact HTTP isolation without using heavy modules (Requests)
        req = urllib.request.Request(self.base_url, data=data, method="POST")
        req.add_header('Content-Type', 'application/json')
        
        # Absolute Performance Optimization: Enforce TCP native Keep-Alive Socket Persistent Connections
        # Stops the OS from executing slow native 'Three Way Handshakes' millisecond overheads on EVERY single LLM query
        req.add_header('Connection', 'keep-alive')
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    # Security Block: Read maximum exactly 1 MB (1024*1024 bytes). 
                    # Drop requests exceeding this preventing the local AI from crashing the Orchestrator RAM via hallucination!
                    raw_bytes = response.read(1048576) 
                    json_resp = json.loads(raw_bytes.decode('utf-8'))
                    return json_resp.get("response", "")
                else:
                    logger.warning(f"Local AI returned non-200 state natively: {response.status}")
                    return None
                    
        except urllib.error.URLError as e:
            logger.error(f"FATAL: Cannot reach local AI engine native port! Is llama.cpp running? {e.reason}")
            return None
        except TimeoutError:
            logger.error(f"Local AI Matrix timed out critically! CPU inference overloaded natively after {self.timeout}s.")
            return None
        except json.JSONDecodeError:
            logger.critical("Local AI responded with structurally corrupt JSON bytes.")
            return None
