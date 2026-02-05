<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import ChatHeader from './ChatHeader.vue'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'
import { sendMessage as sendMessageApi } from '../../services/api'

export interface Message {
  id: number
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
  status?: 'sent' | 'delivered' | 'read'
}

const messages = ref<Message[]>([
  {
    id: 1,
    text: 'Hello! Welcome to Mobile Banking Assistant. I can help you with:\n\n• Check account balance & summary\n• Transfer money\n• Apply for loans\n• Invest in mutual funds\n\nWhat would you like to do today?',
    sender: 'bot',
    timestamp: new Date(Date.now() - 60000),
  },
])

const messagesContainer = ref<HTMLElement | null>(null)
const isLoading = ref(false)
const headerStatus = ref<'online' | 'offline' | 'typing'>('online')

// Quick action suggestions
const quickActions = [
  { label: 'Check Balance', message: 'Show me my account balance' },
  { label: 'Account Summary', message: 'Give me a complete account summary' },
  { label: 'Transfer Money', message: 'I want to transfer money' },
  { label: 'Apply for Loan', message: 'I need a loan' },
  { label: 'Invest', message: 'I want to invest in mutual funds' },
]

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

watch(messages, scrollToBottom, { deep: true })

const sendMessage = async (text: string) => {
  const userMessage: Message = {
    id: Date.now(),
    text,
    sender: 'user',
    timestamp: new Date(),
    status: 'sent',
  }
  messages.value.push(userMessage)
  
  isLoading.value = true
  headerStatus.value = 'typing'

  try {
    // Call backend API
    const response = await sendMessageApi(text)
    
    const botMessage: Message = {
      id: response.id,
      text: response.text,
      sender: 'bot',
      timestamp: new Date(response.timestamp),
    }
    messages.value.push(botMessage)

    // Update user message status
    userMessage.status = 'read'
  } catch (error) {
    console.error('Failed to send message:', error)
    
    // Show error message
    const errorMessage: Message = {
      id: Date.now() + 1,
      text: 'Sorry, I couldn\'t process your request. Please try again.',
      sender: 'bot',
      timestamp: new Date(),
    }
    messages.value.push(errorMessage)
    userMessage.status = 'delivered'
  } finally {
    isLoading.value = false
    headerStatus.value = 'online'
  }
}

const handleQuickAction = (message: string) => {
  sendMessage(message)
}
</script>

<template>
  <div class="chat-container">
    <ChatHeader 
      name="Banking Assistant" 
      :status="headerStatus"
      avatar="🏦"
    />
    
    <div ref="messagesContainer" class="messages-container">
      <div class="messages-wrapper">
        <ChatMessage
          v-for="message in messages"
          :key="message.id"
          :message="message"
        />
        
        <!-- Typing indicator -->
        <div v-if="isLoading" class="typing-indicator">
          <div class="message-bubble bot">
            <div class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Quick Actions -->
    <div class="quick-actions" v-if="messages.length <= 2">
      <button 
        v-for="action in quickActions" 
        :key="action.label"
        class="quick-action-btn"
        @click="handleQuickAction(action.message)"
      >
        {{ action.label }}
      </button>
    </div>
    
    <ChatInput @send="sendMessage" :disabled="isLoading" />
  </div>
</template>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 500px;
  margin: 0 auto;
  background-color: #e5ddd5;
  background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23c5bfb5' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  scroll-behavior: smooth;
}

.messages-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* Quick Actions */
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 16px;
  background-color: rgba(255, 255, 255, 0.9);
  border-top: 1px solid #e0e0e0;
}

.quick-action-btn {
  padding: 8px 16px;
  background-color: #128c7e;
  color: white;
  border: none;
  border-radius: 18px;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.2s, transform 0.1s;
}

.quick-action-btn:hover {
  background-color: #075e54;
  transform: scale(1.02);
}

.quick-action-btn:active {
  transform: scale(0.98);
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  justify-content: flex-start;
  margin-top: 4px;
}

.typing-indicator .message-bubble {
  background-color: white;
  padding: 12px 16px;
  border-radius: 8px;
  border-top-left-radius: 0;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  background-color: #888;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.7);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Custom scrollbar */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}
</style>
