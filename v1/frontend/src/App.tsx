import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CasesList from './pages/CasesList';
import CaseDashboard from './pages/CaseDashboard';
import Documents from './pages/Documents';
import DocumentDetail from './pages/DocumentDetail';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/" element={<CasesList />} />
            <Route path="/cases/:caseId" element={<CaseDashboard />} />
            <Route path="/cases/:caseId/documents" element={<Documents />} />
            <Route path="/cases/:caseId/documents/:documentId" element={<DocumentDetail />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
