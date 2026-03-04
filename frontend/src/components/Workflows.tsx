import React, { useState } from 'react';
import { GitBranch, Zap } from 'lucide-react';
import { AddToast } from '../types';

export function Workflows({ addToast }: { addToast: AddToast }) {
  const [workflows] = useState([
    { id: '1', name: 'Deploy App', description: 'Build and deploy to production', status: 'active' },
    { id: '2', name: 'Scale Infrastructure', description: 'Auto-scale based on load', status: 'active' },
  ]);

  const handleRun = (workflow: { name: string }) => {
    addToast('info', `Running workflow "${workflow.name}"... (workflow execution not yet implemented)`);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Workflows</h1>
        <p className="page-subtitle">Automated workflows</p>
      </div>

      <div className="card">
        <div className="resource-list">
          {workflows.map(workflow => (
            <div key={workflow.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <GitBranch size={20} aria-hidden="true" />
                </div>
                <div>
                  <div className="resource-name">{workflow.name}</div>
                  <div className="resource-type">{workflow.description}</div>
                </div>
              </div>
              <button className="btn btn-primary" onClick={() => handleRun(workflow)}>
                <Zap size={16} style={{ marginRight: 8 }} />
                Run
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
