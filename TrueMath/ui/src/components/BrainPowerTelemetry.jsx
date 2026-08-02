/**
 * BrainPowerTelemetry.jsx
 * ------------------------------------------------------------
 * A premium, animated stats panel that visualises backend AI
 * performance metrics in real-time via the Telemetry JSON feed.
 *
 * Props:
 *   data  - Object: the telemetry snapshot from backend IPC.
 *           Shape: { uptime_seconds, mcts_nodes, lean4_success_ratio,
 *                    lean4_executed, new_operators }
 *
 * Integration: Parent (`App.jsx`) feeds this via the WebSocket
 *              TelemetryEngine.generate_snapshot() JSON payload.
 * ------------------------------------------------------------
 */

import React from 'react';

/** Formats raw seconds into HH:MM:SS display string */
function formatUptime(secs) {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  return [h, m, s].map(v => String(v).padStart(2, '0')).join(':');
}

function StatCard({ label, value, unit, progress }) {
  return (
    <div className="stat-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {unit && <div className="unit">{unit}</div>}
      {progress !== undefined && (
        <div className="progress-bar-track">
          <div
            className="progress-bar-fill"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}

export function BrainPowerTelemetry({ data }) {
  if (!data) {
    return (
      <div className="telemetry-panel glass-card">
        <h2>⚡ Brain Power</h2>
        <div className="stat-card">
          <div className="label">Status</div>
          <div className="value" style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>
            Waiting for Engine…
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="telemetry-panel glass-card">
      <h2>⚡ Brain Power</h2>

      <StatCard
        label="Engine Uptime"
        value={formatUptime(data.uptime_seconds ?? 0)}
        unit="HH : MM : SS"
      />

      <StatCard
        label="MCTS Nodes Explored"
        value={(data.mcts_nodes ?? 0).toLocaleString()}
        unit="mathematical branches"
      />

      <StatCard
        label="Lean 4 Truth Ratio"
        value={`${(data.lean4_success_ratio ?? 0).toFixed(1)}%`}
        unit={`${data.lean4_executed ?? 0} proofs executed`}
        progress={data.lean4_success_ratio ?? 0}
      />

      <StatCard
        label="New Operators Invented"
        value={data.new_operators ?? 0}
        unit="novel mathematical symbols"
      />
    </div>
  );
}
