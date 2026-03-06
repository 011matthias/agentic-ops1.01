import { useEffect } from 'react';
import { AppShell } from './components/layout/AppShell.tsx';
import { useBoardStore } from './store/boardStore.ts';

export default function App() {
  const loadFromServer = useBoardStore(s => s.loadFromServer);

  useEffect(() => {
    loadFromServer(); // Try server, fallback to localStorage automatically
  }, [loadFromServer]);

  return <AppShell />;
}
