const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export interface SendMessageRequest {
  message: string
}

export interface SendMessageResponse {
  id: number
  text: string
  sender: 'user' | 'bot'
  timestamp: number
}

export async function sendMessage(message: string): Promise<SendMessageResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sendMessage`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message } as SendMessageRequest),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(error.error || `HTTP error ${response.status}`)
  }

  return response.json()
}
