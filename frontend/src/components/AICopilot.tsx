import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, X, Send, CheckCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { WS_BASE } from '../config';
import { Message } from '../types';

export function AICopilot() {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hi! I'm your AI infrastructure co-pilot. You can ask me to:\n\n- Create cloud providers and resources\n- Start, stop, or terminate instances\n- Analyze costs and generate reports\n- Configure monitoring and alerts\n\nWhat would you like to do?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const wsToken = localStorage.getItem('cockpit_token');
    const websocket = new WebSocket(`${WS_BASE}/ws/copilot${wsToken ? `?token=${wsToken}` : ''}`);

    websocket.onopen = () => {
      console.log('Connected to AI copilot');
    };

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'typing') {
          setIsTyping(data.typing);
        } else if (data.type === 'message') {
          const assistantMessage: Message = {
            id: Date.now().toString(),
            role: 'assistant',
            content: data.content,
            timestamp: new Date(),
            action_taken: data.action_taken
          };
          setMessages(prev => [...prev, assistantMessage]);
        }
      } catch (e) {
        // ignore malformed messages
      }
    };

    websocket.onerror = () => {
      console.error('WebSocket connection failed');
    };

    setWs(websocket);

    return () => websocket.close();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || !ws) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    const history = updatedMessages.slice(-10).map(m => ({ role: m.role, content: m.content }));
    ws.send(JSON.stringify({ type: 'message', content: input, history }));
    setInput('');
  };

  const renderContent = (content: string) => {
    return content.split('\n').map((line, i) => {
      const formatted = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      const isBullet = line.trimStart().startsWith('- ') || line.trimStart().startsWith('* ');

      return (
        <React.Fragment key={i}>
          {isBullet ? (
            <div style={{ paddingLeft: 16 }} dangerouslySetInnerHTML={{ __html: '&bull; ' + formatted.replace(/^[\s]*[-*]\s/, '') }} />
          ) : (
            <span dangerouslySetInnerHTML={{ __html: formatted }} />
          )}
          {i < content.split('\n').length - 1 && !isBullet && <br />}
        </React.Fragment>
      );
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="copilot-panel"
          role="complementary"
          aria-label="AI Co-pilot"
        >
          <div className="copilot-header">
            <MessageSquare size={20} aria-hidden="true" />
            <span className="copilot-title">AI Co-pilot</span>
            <button
              className="icon-btn"
              style={{ marginLeft: 'auto', background: 'rgba(255,255,255,0.1)' }}
              onClick={() => setIsOpen(false)}
              aria-label="Close co-pilot"
            >
              <X size={16} />
            </button>
          </div>

          <div className="copilot-messages" role="log" aria-label="Chat messages">
            {messages.map(msg => (
              <div key={msg.id} className={`message ${msg.role}`}>
                <div className="message-content">
                  {renderContent(msg.content)}
                  {msg.action_taken && (
                    <div style={{ marginTop: 8, fontSize: 11, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <CheckCircle size={12} /> Action: {msg.action_taken}
                    </div>
                  )}
                </div>
                <div className="message-time">
                  {msg.timestamp.toLocaleTimeString()}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="message assistant">
                <div className="message-content">
                  <div className="typing">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="copilot-input">
            <input
              type="text"
              placeholder="Ask me anything..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              aria-label="Chat message input"
            />
            <button onClick={handleSend} aria-label="Send message">
              <Send size={16} />
            </button>
          </div>
        </motion.div>
      )}

      {!isOpen && (
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          onClick={() => setIsOpen(true)}
          aria-label="Open AI Co-pilot"
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            width: 60,
            height: 60,
            borderRadius: '50%',
            background: 'var(--gradient)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 10px 30px rgba(99, 102, 241, 0.4)'
          }}
        >
          <MessageSquare size={24} color="white" />
        </motion.button>
      )}
    </AnimatePresence>
  );
}
