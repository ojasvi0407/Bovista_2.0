import { useApp } from '../App';

export default function LiveWorkspaceStatus() {
  const { workspace, workspaceError, workspaceLoading, reloadWorkspace } = useApp();
  const totalRecords = Object.values(workspace).reduce((total, records) => total + records.length, 0);

  if (workspaceLoading) return <p className="text-xs text-gray-500" role="status">Loading live, scope-limited records…</p>;
  if (workspaceError) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800" role="alert">
        <span>Live data is unavailable: {workspaceError}</span>
        <button className="font-semibold underline" onClick={() => void reloadWorkspace()} type="button">Retry</button>
      </div>
    );
  }
  return <p className="text-xs text-green-700">● Live data · {totalRecords} records in your authorized scope</p>;
}
