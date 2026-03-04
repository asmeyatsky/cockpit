export interface Provider {
  id: string;
  provider_type: string;
  name: string;
  status: string;
  region: string;
}

export interface Resource {
  id: string;
  resource_type: string;
  name: string;
  state: string;
  region: string;
}

export interface Agent {
  id: string;
  name: string;
  provider: string;
  model: string;
  status: string;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: Date;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  action_taken?: string;
}

export type AddToast = (type: Notification['type'], msg: string) => void;
