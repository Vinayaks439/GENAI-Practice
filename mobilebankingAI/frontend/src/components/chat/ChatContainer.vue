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
    text: 'Hello! Welcome to Mobile Banking Assistant. How can I help you today?',
    sender: 'bot',
    timestamp: new Date(Date.now() - 60000),
  },
])

const messagesContainer = ref<HTMLElement | null>(null)
const isLoading = ref(false)
const headerStatus = ref<'online' | 'offline' | 'typing'>('online')

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
      </div>
    </div>
    
    <ChatInput @send="sendMessage" />
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
