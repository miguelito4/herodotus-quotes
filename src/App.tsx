import { useEffect } from 'react'
import HerodotusExplorer from './components/HerodotusExplorer.jsx'
import Footer from './components/Footer.jsx'
import './App.css'
// 1. Import the SDK
import { sdk } from '@farcaster/miniapp-sdk'

function App() {
  useEffect(() => {
    const init = async () => {
      // 2. Tell Farcaster we are ready (Removes the splash screen)
      await sdk.actions.ready();
    };
    init();
  }, []);

  return (
    <>
      <HerodotusExplorer />
      <Footer />
    </>
  )
}

export default App