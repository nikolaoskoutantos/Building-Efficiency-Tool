// src/networks/baseSepolia.js
import { defineChain } from '@reown/appkit/networks'

export const baseSepolia = defineChain({
  id: 84532,
  name: 'Base Sepolia',
  caipNetworkId: 'eip155:84532',
  chainNamespace: 'eip155',
  nativeCurrency: {
    name: 'Ethereum',
    symbol: 'ETH',
    decimals: 18
  },
  rpcUrls: {
    default: { http: ['https://sepolia.base.org'] }
  },
  blockExplorers: {
    default: { name: 'Basescan', url: 'https://sepolia.basescan.org' }
  },
  testnet: true
})
