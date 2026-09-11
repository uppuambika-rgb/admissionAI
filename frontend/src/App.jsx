import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import TopicPage from './pages/TopicPage';

export default function App() {
  return (
    <div className="app-root">
      <Navbar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/topic/:topicId" element={<TopicPage />} />
          {/* Fallback — redirect unknown routes to home */}
          <Route path="*" element={<HomePage />} />
        </Routes>
      </main>
    </div>
  );
}
