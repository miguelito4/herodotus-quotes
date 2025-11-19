import React, { useState } from 'react';
import { Code2, Wallet, X } from 'lucide-react';
import { ethers } from 'ethers';

const Footer = () => {
  const [showTipModal, setShowTipModal] = useState(false);
  const [showAlert, setShowAlert] = useState(false);
  const [alertStatus, setAlertStatus] = useState('');
  const [amount, setAmount] = useState('');
  const [selectedToken, setSelectedToken] = useState('ETH');

  const WALLET_ADDRESS = '0x91735d001f5278520a8a91EDAc1eb134dF69439a'; // = herodotus.eth address
  const TOKEN_CONFIGS = {
    ETH: {
      name: 'ETH',
      chain: 'any',
      decimals: 18
    },
    USDC: {
      name: 'USDC',
      chain: 'any',
      decimals: 6,
      address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' // Base USDC address
    }
  };

  // Base chain parameters
  const BASE_CHAIN_ID = '0x2105';
  const BASE_CHAIN_PARAMS = {
    chainId: '0x2105',
    chainName: 'Base',
    nativeCurrency: {
      name: 'Ethereum',
      symbol: 'ETH',
      decimals: 18
    },
    rpcUrls: ['https://mainnet.base.org'],
    blockExplorerUrls: ['https://basescan.org']
  };

  const switchToBase = async () => {
    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: BASE_CHAIN_ID }],
      });
    } catch (switchError) {
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [BASE_CHAIN_PARAMS],
          });
        } catch (addError) {
          throw new Error('Failed to add Base network');
        }
      } else {
        throw new Error('Failed to switch to Base network');
      }
    }
  };

  const handleTip = async () => {
    if (typeof window.ethereum === 'undefined') {
      setAlertStatus('Please install a Web3 wallet like MetaMask to tip.');
      setShowAlert(true);
      return;
    }

    if (!amount || isNaN(amount) || parseFloat(amount) <= 0) {
      setAlertStatus('Please enter a valid amount.');
      setShowAlert(true);
      return;
    }

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();

      const tokenConfig = TOKEN_CONFIGS[selectedToken];

      // Check if we need to switch networks for Base-specific tokens
      if (tokenConfig.chain === 'base') {
        const network = await provider.getNetwork();
        if (network.chainId !== 8453n) { // Base Chain ID is 8453 (0x2105)
          await switchToBase();
        }
      }

      if (selectedToken === 'ETH') {
        const tx = await signer.sendTransaction({
          to: WALLET_ADDRESS,
          value: ethers.parseEther(amount)
        });
        await tx.wait();
      } else {
        // For ERC-20 tokens
        const abi = [
          "function transfer(address to, uint256 value) returns (bool)"
        ];
        const contract = new ethers.Contract(tokenConfig.address, abi, signer);

        const amountInTokens = ethers.parseUnits(amount, tokenConfig.decimals);
        const tx = await contract.transfer(WALLET_ADDRESS, amountInTokens);
        await tx.wait();
      }

      setAlertStatus('Thank you for your support!');
      setShowAlert(true);
      setShowTipModal(false);
      setAmount('');
    } catch (error) {
      console.error(error);
      setAlertStatus(error.message || 'Transaction failed. Please try again.');
      setShowAlert(true);
    }
  };

  return (
    <footer className="mt-16 border-t border-gray-200 py-8">
      <div className="max-w-4xl mx-auto px-6 md:px-8">
        {showAlert && (
          <div className="mb-6 bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between">
            <p className="font-sans text-sm text-ink">{alertStatus}</p>
            <button
              onClick={() => setShowAlert(false)}
              className="text-gray-400 hover:text-ink transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {showTipModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-sans text-lg font-semibold text-ink">Support This Project</h3>
                <button
                  onClick={() => setShowTipModal(false)}
                  className="text-gray-400 hover:text-ink transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block font-sans text-sm text-accent mb-2">
                    Amount
                  </label>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0.00"
                    step="0.01"
                    min="0"
                    className="w-full px-4 py-2 border rounded-lg font-sans text-lg"
                  />
                </div>

                <div>
                  <label className="block font-sans text-sm text-accent mb-2">
                    Token
                  </label>
                  <select
                    value={selectedToken}
                    onChange={(e) => setSelectedToken(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg font-sans"
                  >
                    {Object.entries(TOKEN_CONFIGS).map(([key, token]) => (
                      <option key={key} value={key}>
                        {token.name} {token.chain === 'base' ? '(Base)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={handleTip}
                  className="w-full px-4 py-2 bg-accent text-white rounded-lg hover:bg-ink transition-colors font-sans"
                >
                  Send Tip
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <h3 className="font-sans text-lg font-semibold text-ink">About This Project</h3>
            <p className="font-sans text-gray-500 text-sm leading-relaxed">
              This explorer was created to make Herodotus's Histories more accessible and searchable. The project was built with Python, React, and Project Gutenberg's texts, and revivified by Google Antigravity.
            </p>
            <div className="flex items-center justify-center">
              <a
                href="https://github.com/yourusername/herodotus-explorer"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-accent hover:text-ink transition-colors"
              >
                <Code2 className="h-5 w-5 mr-2" />
                <span className="font-sans text-sm">View Source</span>
              </a>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="font-sans text-lg font-semibold text-ink">Support This Project</h3>
            <p className="font-sans text-gray-500 text-sm leading-relaxed">
              If you find this tool edifying and fun, consider supporting its development
              by sending some ETH or USDC to herodotus.eth on Base.
            </p>
            <button
              onClick={() => setShowTipModal(true)}
              className="inline-flex items-center px-4 py-2 bg-accent text-white rounded-lg hover:bg-ink transition-colors font-sans text-sm"
            >
              <Wallet className="h-4 w-4 mr-2" />
              Send Tip
            </button>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-200 text-center">
          <p className="font-sans text-sm text-gray-500">
            © {new Date().getFullYear()} Mike Casey. MIT License. Texts sourced from{' '}
            <a
              href="https://www.gutenberg.org"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-ink transition-colors"
            >
              Project Gutenberg
            </a>
            .
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;