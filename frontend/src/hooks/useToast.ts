import { useState, useCallback } from 'react';
import { Notification } from '../types';

export function useToast() {
  const [toasts, setToasts] = useState<Notification[]>([]);

  const addToast = useCallback((type: Notification['type'], message: string) => {
    const toast: Notification = {
      id: Date.now().toString(),
      type,
      message,
      timestamp: new Date()
    };
    setToasts(prev => [...prev, toast]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== toast.id));
    }, 5000);
  }, []);

  return { toasts, addToast };
}
