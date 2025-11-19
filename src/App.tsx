import { useEffect, useState } from 'react'
import HerodotusExplorer from './components/HerodotusExplorer'
import Footer from './components/Footer'
import { sdk } from '@farcaster/miniapp-sdk'
import './App.css'

function App() {
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        // Try to signal ready, but don't block forever
        console.log("Initializing Farcaster SDK...");
        // Race condition: If SDK takes too long, just load the app
        const timeout = new Promise(resolve => setTimeout(resolve, 1000));
        await Promise.race([sdk.actions.ready(), timeout]);
        console.log("SDK Ready (or timed out)");
      } catch (err) {
        console.error("SDK Error:", err);
      } finally {
        setIsLoaded(true);
      }
    };
    init();
  }, []);

  // Render immediately, don't wait for SDK to prevent white screen
  return (
    <div className="app-container">
      <HerodotusExplorer />
      <Footer />
    </div>
  )
}

export default App