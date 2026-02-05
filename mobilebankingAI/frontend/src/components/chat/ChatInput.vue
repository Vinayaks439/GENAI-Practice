<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  send: [text: string]
}>()

const inputText = ref('')
const isRecording = ref(false)

const handleSend = () => {
  const text = inputText.value.trim()
  if (text) {
    emit('send', text)
    inputText.value = ''
  }
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

const toggleRecording = () => {
  isRecording.value = !isRecording.value
}
</script>

<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <button class="emoji-btn">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M9.153 11.603c.795 0 1.439-.879 1.439-1.962s-.644-1.962-1.439-1.962-1.439.879-1.439 1.962.644 1.962 1.439 1.962zm5.693 0c.795 0 1.439-.879 1.439-1.962s-.644-1.962-1.439-1.962-1.439.879-1.439 1.962.644 1.962 1.439 1.962zM12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 18c-4.411 0-8-3.589-8-8s3.589-8 8-8 8 3.589 8 8-3.589 8-8 8zm0-6c-2.172 0-4.084 1.063-5.272 2.686l1.544 1.076A4.986 4.986 0 0112 16c1.682 0 3.167.828 4.072 2.098l1.544-1.076C16.084 15.063 14.172 14 12 14z"/>
        </svg>
      </button>
      
      <textarea
        v-model="inputText"
        class="message-input"
        placeholder="Type a message"
        rows="1"
        @keydown="handleKeydown"
      ></textarea>
      
      <button class="attach-btn">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5a2.5 2.5 0 015 0v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5a2.5 2.5 0 005 0V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/>
        </svg>
      </button>
    </div>
    
    <button 
      v-if="inputText.trim()" 
      class="send-btn"
      @click="handleSend"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
      </svg>
    </button>
    
    <button 
      v-else 
      class="mic-btn"
      :class="{ 'recording': isRecording }"
      @click="toggleRecording"
    >
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15a.998.998 0 00-.98-.85c-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08a6.993 6.993 0 005.91-5.78c.1-.6-.39-1.14-1-1.14z"/>
      </svg>
    </button>
  </div>
</template>

<style scoped>
.chat-input-container {
  display: flex;
  align-items: flex-end;
  padding: 8px 12px;
  gap: 8px;
  background-color: #f0f2f5;
}

.input-wrapper {
  display: flex;
  align-items: center;
  flex: 1;
  background-color: white;
  border-radius: 24px;
  padding: 6px 12px;
  gap: 8px;
}

.emoji-btn,
.attach-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: #54656f;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.emoji-btn:hover,
.attach-btn:hover {
  color: #128c7e;
}

.message-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  line-height: 20px;
  max-height: 100px;
  resize: none;
  font-family: inherit;
  color: #111b21;
}

.message-input::placeholder {
  color: #667781;
}

.send-btn,
.mic-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: none;
  background-color: #00a884;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s, transform 0.1s;
  flex-shrink: 0;
}

.send-btn:hover,
.mic-btn:hover {
  background-color: #008f72;
}

.send-btn:active,
.mic-btn:active {
  transform: scale(0.95);
}

.mic-btn.recording {
  background-color: #ef5350;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(239, 83, 80, 0.4);
  }
  50% {
    box-shadow: 0 0 0 12px rgba(239, 83, 80, 0);
  }
}
</style>
