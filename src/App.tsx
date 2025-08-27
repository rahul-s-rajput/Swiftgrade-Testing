import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AssessmentProvider } from './context/AssessmentContext';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { NewAssessment } from './pages/NewAssessment';
import { Review } from './pages/Review';

function App() {
  return (
    <AssessmentProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/new-assessment" element={<NewAssessment />} />
            <Route path="/review/:id" element={<Review />} />
          </Routes>
        </Layout>
      </Router>
    </AssessmentProvider>
  );
}

export default App;