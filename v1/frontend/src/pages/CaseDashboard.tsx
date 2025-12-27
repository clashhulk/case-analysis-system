import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { casesApi } from '@/api/client';
import {
  FileText,
  MessageSquare,
  Calendar,
  AlertTriangle,
  FileSearch,
  Settings,
} from 'lucide-react';

const modules = [
  {
    id: 'documents',
    title: 'Documents',
    description: 'Individual document analysis',
    icon: FileText,
    stats: 'Coming soon',
    color: 'blue',
  },
  {
    id: 'summary',
    title: 'Case Summary',
    description: 'Combined case analysis',
    icon: FileSearch,
    stats: 'Coming soon',
    color: 'green',
  },
  {
    id: 'chat',
    title: 'Chat',
    description: 'Ask questions about this case',
    icon: MessageSquare,
    stats: 'Coming soon',
    color: 'purple',
  },
  {
    id: 'timeline',
    title: 'Timeline',
    description: 'Case timeline',
    icon: Calendar,
    stats: 'Coming soon',
    color: 'indigo',
  },
  {
    id: 'conflicts',
    title: 'Conflicts',
    description: 'Findings and conclusions',
    icon: AlertTriangle,
    stats: 'Coming soon',
    color: 'red',
  },
  {
    id: 'settings',
    title: 'Settings',
    description: 'Case options',
    icon: Settings,
    stats: '',
    color: 'gray',
  },
];

export default function CaseDashboard() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => casesApi.get(caseId!),
    enabled: !!caseId,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading case...</div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Case not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <button
                onClick={() => navigate('/')}
                className="text-blue-600 hover:text-blue-800 mb-2 text-sm"
              >
                ← Back to Cases
              </button>
              <h1 className="text-3xl font-bold text-gray-900">{caseData.title}</h1>
              <p className="text-gray-500 mt-1">Case #{caseData.case_number}</p>
            </div>
            <div className="text-right">
              <span className={`px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full ${
                caseData.status === 'active' ? 'bg-green-100 text-green-800' :
                caseData.status === 'archived' ? 'bg-gray-100 text-gray-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {caseData.status}
              </span>
              <p className="text-gray-500 text-sm mt-2">
                Created {new Date(caseData.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Module Cards Grid */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {modules.map((module) => {
            const Icon = module.icon;
            return (
              <div
                key={module.id}
                className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition cursor-pointer border-2 border-transparent hover:border-blue-300"
                onClick={() => {
                  if (module.id === 'documents') {
                    navigate(`/cases/${caseId}/documents`);
                  } else {
                    alert(`${module.title} module coming soon!`);
                  }
                }}
              >
                <div className="flex items-start justify-between">
                  <div className={`p-3 rounded-lg bg-${module.color}-100`}>
                    <Icon className={`h-6 w-6 text-${module.color}-600`} />
                  </div>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-gray-900">{module.title}</h3>
                <p className="mt-1 text-sm text-gray-500">{module.description}</p>
                {module.stats && (
                  <p className="mt-3 text-sm font-medium text-gray-600">{module.stats}</p>
                )}
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
