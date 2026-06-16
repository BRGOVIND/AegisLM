import React, { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';

const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Models = React.lazy(() => import('./pages/Models'));
const Attacks = React.lazy(() => import('./pages/Attacks'));
const RunTests = React.lazy(() => import('./pages/RunTests'));
const Hallucination = React.lazy(() => import('./pages/Hallucination'));
const Reports = React.lazy(() => import('./pages/Reports'));
const Comparison = React.lazy(() => import('./pages/Comparison'));
const Analytics = React.lazy(() => import('./pages/Analytics'));
const Mutations = React.lazy(() => import('./pages/Mutations'));
const RedTeamAgent = React.lazy(() => import('./pages/RedTeamAgent'));
const Leaderboard = React.lazy(() => import('./pages/Leaderboard'));
const History = React.lazy(() => import('./pages/History'));
const Dataset = React.lazy(() => import('./pages/Dataset'));

const Fallback = () => (
  <div className="flex items-center justify-center h-full w-full text-gray-400 text-sm">
    Loading...
  </div>
);

export default function App() {
  return (
    <Layout>
      <Suspense fallback={<Fallback />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/models" element={<Models />} />
          <Route path="/attacks" element={<Attacks />} />
          <Route path="/run" element={<RunTests />} />
          <Route path="/hallucination" element={<Hallucination />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/compare" element={<Comparison />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/mutations" element={<Mutations />} />
          <Route path="/agent" element={<RedTeamAgent />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/dataset" element={<Dataset />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
