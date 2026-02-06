import { addClient, removeClient } from '../plugins/websocket'

// Track authenticated peers (token validated on first message)
const authenticatedPeers = new WeakSet<any>()

function isAuthRequired(): boolean {
  return !!process.env.SWARMOPS_API_TOKEN
}

function validateToken(token: string): boolean {
  const expected = process.env.SWARMOPS_API_TOKEN
  if (!expected) return true
  if (token.length !== expected.length) return false
  let result = 0
  for (let i = 0; i < token.length; i++) {
    result |= token.charCodeAt(i) ^ expected.charCodeAt(i)
  }
  return result === 0
}

export default defineWebSocketHandler({
  open(peer) {
    if (!isAuthRequired()) {
      // No auth configured - add immediately
      authenticatedPeers.add(peer)
      addClient(peer)
    } else {
      // Require auth message before adding to broadcast
      peer.send(JSON.stringify({ type: 'auth_required' }))
    }
  },
  close(peer) {
    removeClient(peer)
  },
  error(peer, error) {
    console.log(`[websocket] Connection error: ${error.message}`)
    removeClient(peer)
  },
  message(peer, message) {
    // Handle auth message if not yet authenticated
    if (!authenticatedPeers.has(peer)) {
      try {
        const data = JSON.parse(message.text())
        if (data.type === 'auth' && validateToken(data.token || '')) {
          authenticatedPeers.add(peer)
          addClient(peer)
          peer.send(JSON.stringify({ type: 'auth_ok' }))
        } else {
          peer.send(JSON.stringify({ type: 'auth_failed' }))
          peer.close()
        }
      } catch {
        peer.send(JSON.stringify({ type: 'auth_failed' }))
        peer.close()
      }
      return
    }
    // Echo back or handle client messages if needed
  }
})
