import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { AssessmentProvider } from './context/AssessmentContext';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { NewAssessment } from './pages/NewAssessment';
import { Review } from './pages/Review';
import { Settings } from './pages/Settings';
import { SetupWizard } from './components/SetupWizard';

// Check if running in Tauri
const isTauri = () => {
  return window.__TAURI__ !== undefined;
};

function App() {
  const [isSetupComplete, setIsSetupComplete] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [backendPort, setBackendPort] = useState<number | null>(null);
  const [backendStatus, setBackendStatus] = useState<string>('initializing');

  useEffect(() => {
    const initializeApp = async () => {
      if (!isTauri()) {
        // Not running in Tauri, use regular web mode
        setIsSetupComplete(true);
        setIsLoading(false);
        return;
      }

      try {
        // Set up event listeners
        const unlistenOutput = await listen('backend-output', (event: any) => {
          console.log('Backend output:', event.payload);
        });
        
        const unlistenError = await listen('backend-error', (event: any) => {
          console.error('Backend error:', event.payload);
        });
        
        const unlistenTerminated = await listen('backend-terminated', (event: any) => {
          console.warn('Backend terminated:', event.payload);
          setBackendStatus('terminated');
        });
        
        // Check if environment is configured
        console.log('Checking environment configuration...');
        const hasConfig = await invoke<boolean>('check_env_config');
        console.log('Environment configured:', hasConfig);
        
        if (hasConfig) {
          setBackendStatus('starting');
          console.log('Starting backend...');
          
          try {
            // Start backend
            const port = await invoke<number>('start_backend');
            console.log('Backend started on port:', port);
            setBackendPort(port);
            setBackendStatus('running');
            
            // Update API base URL
            const backendUrl = `http://127.0.0.1:${port}`;
            
            // Import and update API base
            const { setApiBase } = await import('./utils/api');
            setApiBase(backendUrl);
            
            // Verify backend is accessible
            const response = await fetch(`${backendUrl}/health`);
            if (response.ok) {
              console.log('Backend health check passed');
            } else {
              console.error('Backend health check failed');
            }
          } catch (e) {
            console.error('Failed to start backend:', e);
            console.error('Error details:', JSON.stringify(e));
            setBackendStatus('error');
          }
          
          setIsSetupComplete(true);
        } else {
          console.log('Environment not configured, showing setup wizard');
          setIsSetupComplete(false);
        }
        
        // Cleanup on unmount
        return () => {
          unlistenOutput();
          unlistenError();
          unlistenTerminated();
        };
      } catch (e) {
        console.error('Failed to initialize app:', e);
        setIsSetupComplete(true); // Fall back to web mode
      } finally {
        setIsLoading(false);
      }
    };

    initializeApp();
  }, []);

  // Show loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading Mark Grading Assistant...</p>
          {backendPort && (
            <p className="mt-2 text-sm text-gray-500">Backend running on port {backendPort}</p>
          )}
          <p className="mt-1 text-xs text-gray-400">Status: {backendStatus}</p>
        </div>
      </div>
    );
  }

  // Show setup wizard if needed
  if (isTauri() && isSetupComplete === false) {
    return <SetupWizard onComplete={() => setIsSetupComplete(true)} />;
  }

  // Normal app
  return (
    <AssessmentProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/new-assessment" element={<NewAssessment />} />
            <Route path="/review/:id" element={<Review />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Layout>
      </Router>
    </AssessmentProvider>
  );
}

export default App;
