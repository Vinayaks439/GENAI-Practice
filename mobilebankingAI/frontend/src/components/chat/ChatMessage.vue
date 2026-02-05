<script setup lang="ts">
import type { Message } from './ChatContainer.vue'

const props = defineProps<{
  message: Message
}>()

const formatTime = (date: Date): string => {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const getStatusIcon = (status?: string): string => {
  switch (status) {
    case 'sent':
      return '✓'
    case 'delivered':
      return '✓✓'
    case 'read':
      return '✓✓'
    default:
      return ''
  }
}
</script>

<template>
  <div 
    class="message-wrapper" 
    :class="{ 'message-user': message.sender === 'user', 'message-bot': message.sender === 'bot' }"
  >
    <div class="message-bubble">
      <div class="message-tail"></div>
      <p class="message-text">{{ message.text }}</p>
      <div class="message-meta">
        <span class="message-time">{{ formatTime(message.timestamp) }}</span>
        <span 
          v-if="message.sender === 'user' && message.status" 
          class="message-status"
          :class="{ 'status-read': message.status === 'read' }"
        >
          {{ getStatusIcon(message.status) }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-wrapper {
  display: flex;
  margin-bottom: 2px;
}

.message-user {
  justify-content: flex-end;
}

.message-bot {
  justify-content: flex-start;
}

.message-bubble {
  position: relative;
  max-width: 75%;
  padding: 6px 12px 8px;
  border-radius: 8px;
  box-shadow: 0 1px 0.5px rgba(0, 0, 0, 0.13);
}

.message-user .message-bubble {
  background-color: #dcf8c6;
  border-top-right-radius: 0;
}

.message-bot .message-bubble {
  background-color: #ffffff;
  border-top-left-radius: 0;
}

.message-tail {
  position: absolute;
  top: 0;
  width: 12px;
  height: 12px;
}

.message-user .message-tail {
  right: -8px;
  background: linear-gradient(135deg, #dcf8c6 50%, transparent 50%);
}

.message-bot .message-tail {
  left: -8px;
  background: linear-gradient(225deg, #ffffff 50%, transparent 50%);
}

.message-text {
  margin: 0;
  font-size: 14.2px;
  line-height: 1.4;
  color: #111b21;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message-meta {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}

.message-time {
  font-size: 11px;
  color: #667781;
}

.message-status {
  font-size: 14px;
  color: #667781;
  letter-spacing: -4px;
  margin-right: -2px;
}

.message-status.status-read {
  color: #53bdeb;
}
</style>
