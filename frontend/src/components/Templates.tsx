import React, { useState } from 'react';
import { FileText } from 'lucide-react';
import { AddToast } from '../types';

export function Templates({ addToast }: { addToast: AddToast }) {
  const [templates] = useState([
    { id: '1', name: 'Web Server', description: 'EC2 with load balancer', provider: 'AWS' },
    { id: '2', name: 'Database', description: 'RDS PostgreSQL', provider: 'AWS' },
    { id: '3', name: 'Kubernetes', description: 'EKS cluster', provider: 'AWS' },
  ]);

  const handleDeploy = (template: { id: string; name: string }) => {
    addToast('info', `Deploying "${template.name}"... (template deployment not yet implemented)`);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Templates</h1>
        <p className="page-subtitle">Infrastructure templates for quick deployment</p>
      </div>

      <div className="card">
        <div className="resource-list">
          {templates.map(template => (
            <div key={template.id} className="resource-item">
              <div className="resource-info">
                <div className="resource-icon">
                  <FileText size={20} aria-hidden="true" />
                </div>
                <div>
                  <div className="resource-name">{template.name}</div>
                  <div className="resource-type">{template.description} &bull; {template.provider}</div>
                </div>
              </div>
              <button className="btn btn-primary" onClick={() => handleDeploy(template)}>Deploy</button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
