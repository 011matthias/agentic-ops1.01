import { Sidebar } from './Sidebar.tsx';
import { Board } from '../board/Board.tsx';
import { GlobalOverview } from '../overview/GlobalOverview.tsx';
import { CardModal } from '../board/CardModal.tsx';
import { useBoardStore } from '../../store/boardStore.ts';
import { useUIStore } from '../../store/uiStore.ts';
import { FolderOpen } from 'lucide-react';

export function AppShell() {
  const { activeProjectId, isGlobalOverview } = useBoardStore();
  const activeModal = useUIStore(s => s.activeModal);

  const renderMain = () => {
    if (isGlobalOverview) return <GlobalOverview />;
    if (activeProjectId)  return <Board projectId={activeProjectId} />;
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        <div className="text-center">
          <FolderOpen size={48} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">Select a project from the sidebar or view the Global Overview.</p>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-hidden flex">
        {renderMain()}
      </main>
      {activeModal && <CardModal />}
    </div>
  );
}
