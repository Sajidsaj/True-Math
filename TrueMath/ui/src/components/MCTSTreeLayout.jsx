/**
 * MCTSTreeLayout.jsx
 * ------------------------------------------------------------
 * Renders the Monte Carlo Tree Search exploration as a visual
 * node graph. Each node represents a mathematical hypothesis
 * being evaluated by the backend engine.
 *
 * Node statuses:
 *   "frontier" - currently being explored (blue highlight)
 *   "verified" - passed Lean 4 formal verification (green)
 *   "rejected" - falsified or statistically disproven (red)
 *
 * Props:
 *   nodes  - Array of { id, label, status, parentId }
 *
 * Integration: App.jsx feeds this from the IPC WS payload
 *              type === 'mcts_update'.
 * ------------------------------------------------------------
 */

import React, { useMemo } from 'react';

/** Single visual node */
function MCTSNode({ label, status }) {
  return (
    <div className="mcts-node-wrap">
      <div className={`mcts-node ${status}`} title={label}>
        {label}
      </div>
    </div>
  );
}

/** Recursive tree renderer - renders children below each parent */
function TreeLayer({ nodes, allNodes, depth = 0 }) {
  if (!nodes || nodes.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {nodes.map(node => {
        const children = allNodes.filter(n => n.parentId === node.id);
        return (
          <div
            key={node.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 0,
              paddingLeft: depth * 24,
            }}
          >
            <MCTSNode label={node.label} status={node.status} />
            {children.length > 0 && (
              <>
                <div className="mcts-connector" />
                <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
                  <TreeLayer nodes={children} allNodes={allNodes} depth={depth + 1} />
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** Placeholder nodes for startup before backend connects */
const PLACEHOLDER_NODES = [
  { id: 'root', label: 'Riemann Hypothesis', status: 'frontier', parentId: null },
  { id: 'a',    label: 'ζ(s) zeros on Re=½', status: 'frontier', parentId: 'root' },
  { id: 'b',    label: 'Trivial zeros test',  status: 'verified', parentId: 'root' },
  { id: 'c',    label: 'Non-trivial bound',   status: 'rejected', parentId: 'a' },
];

export function MCTSTreeLayout({ nodes }) {
  const displayNodes = nodes && nodes.length > 0 ? nodes : PLACEHOLDER_NODES;

  // Find root nodes (no parent)
  const roots = useMemo(
    () => displayNodes.filter(n => !n.parentId),
    [displayNodes]
  );

  return (
    <div className="tree-panel glass-card">
      <h2>🧠 MCTS Decision Tree</h2>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        {['frontier', 'verified', 'rejected'].map(s => (
          <span key={s} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.72rem', opacity: 0.8 }}>
            <span className={`mcts-node ${s}`} style={{ padding: '2px 8px', fontSize: '0.68rem' }}>{s}</span>
          </span>
        ))}
      </div>

      <div style={{ overflowY: 'auto', maxHeight: 480 }}>
        <TreeLayer nodes={roots} allNodes={displayNodes} />
      </div>
    </div>
  );
}
