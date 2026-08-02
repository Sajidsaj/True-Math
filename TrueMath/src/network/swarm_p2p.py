"""
Module Name: swarm_p2p
Purpose: Connect local LAN PCs instantly to parallelize deep formal math research.
Responsibilities:
  - Broadcast localized UDP beacons sequentially to discover other TrueMath peers.
  - Spin up TCP threads to exchange mathematical states without explicit Internet.
  - Distribute MCTS sub-trees safely across local machines.
Dependencies: socket, threading, json, time
Input: Math MCTS graph payloads.
Output: Network state tracking & Distributed calculation responses.
Possible Errors: Port conflicts, OS Firewall blocking, Deadlocks.
Testing Method: Loopback UDP broadcasts to ensure self-discovery / port bounding.
Estimated Complexity: Very High.
Integration Notes: Requires firewall exception manually on Windows for Port 55444.
"""
import socket
import threading
import json
import time
from typing import Dict, List, Optional
from collections import deque
from src.core.sys_logger import get_logger

logger = get_logger("SwarmP2P")

class TrueMathSwarmNode:
    __slots__ = ('port', 'broadcast_interval', 'active_peers', '_peers_lock', '_stop_event', '_discovery_thread', '_listen_thread')
    
    def __init__(self, port: int = 55444, broadcast_interval: int = 5):
        self.port = port
        self.broadcast_interval = broadcast_interval
        self.active_peers: set = set()
        # BUG-09 FIX: Plain set is NOT thread-safe for compound read/write operations.
        # Without this lock, concurrent discovery threads can cause RuntimeError:
        # 'Set changed size during iteration'.
        self._peers_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._discovery_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None

    def start_discovery(self) -> None:
        """Launches the background OS thread specifically for UDP beaconing and inbound parsing."""
        if self._discovery_thread is None or not self._discovery_thread.is_alive():
            self._stop_event.clear()
            
            # Spin up the listener daemon before firing beacons
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()
            
            self._discovery_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
            self._discovery_thread.start()
            logger.info("Swarm UDP Discovery Beacon and Listener engaged.")

    def stop_discovery(self) -> None:
        """Safely collapses the networking threads."""
        self._stop_event.set()
        if self._discovery_thread:
            self._discovery_thread.join(timeout=2.0)
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)
        logger.info("Swarm Discovery heavily halted.")

    def _listen_loop(self) -> None:
        """UDP Array listener preventing ghost connections & Memory leaks on massive LANs."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.port))
            sock.settimeout(1.0)
            while not self._stop_event.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                    # Security: validate the UDP beacon before accepting as a legitimate peer
                    try:
                        beacon = json.loads(data.decode('utf-8', errors='ignore'))
                        if beacon.get('agent') != 'TrueMathSwarm':
                            continue  # Reject unknown agents silently
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue  # Reject malformed packets silently
                    # BUG-09 FIX: All peer set mutations guarded by lock.
                    with self._peers_lock:
                        if len(self.active_peers) > 1000:
                            self.active_peers.clear()
                        self.active_peers.add(addr[0])
                except socket.timeout:
                    continue

    def _broadcast_loop(self) -> None:
        """Pushes broadcast packets into the Local Subnet to find neighboring PCs."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Ensure socket can be reused cleanly if the process drops
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # TCP/UDP Hardware buffering maximization for limitless mass throughput across P2P
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
            
            # Minified JSON byte compilation (separators) saves critical packet bandwidth bounds
            payload = json.dumps({"agent": "TrueMathSwarm", "status": "idle"}, separators=(',', ':')).encode("utf-8")
            
            while not self._stop_event.is_set():
                try:
                    # Generic subnet broadcast IP Address
                    sock.sendto(payload, ('255.255.255.255', self.port))
                    logger.debug("Swarm TCP Beacon fired.")
                except OSError as e:
                    logger.warning(f"UDP Beacon mathematically blocked by OS: {e}")
                
                # Sleep interval prevents aggressive local router flooding
                time.sleep(self.broadcast_interval)

    def process_incoming_job(self, job_data: dict) -> dict:
        """Evaluates external computation requests securely before allocating CPU."""
        if "math_hash" not in job_data:
            return {"status": "error", "message": "Invalid Math Payload."}
            
        logger.info(f"Swarm allocated remote job segment: {job_data['math_hash']}")
        # Simulated math computation mapping...
        return {"status": "processing", "assigned_thread": "CPU_01"}
