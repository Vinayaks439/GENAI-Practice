<script setup lang="ts">
defineProps<{
  name: string
  status: 'online' | 'offline' | 'typing'
  avatar?: string
}>()
</script>

<template>
  <div class="chat-header">
    <div class="back-button">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
      </svg>
    </div>
    
    <div class="avatar">
      <span v-if="avatar">{{ avatar }}</span>
      <span v-else>{{ name.charAt(0).toUpperCase() }}</span>
    </div>
    
    <div class="header-info">
      <h3 class="name">{{ name }}</h3>
      <p class="status" :class="status">
        <span v-if="status === 'online'">online</span>
        <span v-else-if="status === 'typing'">typing...</span>
        <span v-else>last seen recently</span>
      </p>
    </div>
    
    <div class="header-actions">
      <button class="action-btn">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M15.9 14.3H15l-.3-.3c1-1.1 1.6-2.7 1.6-4.3 0-3.7-3-6.7-6.7-6.7S3 6 3 9.7s3 6.7 6.7 6.7c1.6 0 3.2-.6 4.3-1.6l.3.3v.8l5.1 5.1 1.5-1.5-5-5.2zm-6.2 0c-2.6 0-4.6-2.1-4.6-4.6s2.1-4.6 4.6-4.6 4.6 2.1 4.6 4.6-2 4.6-4.6 4.6z"/>
        </svg>
      </button>
      <button class="action-btn">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-header {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  background: linear-gradient(180deg, #075e54 0%, #128c7e 100%);
  color: white;
  gap: 12px;
}

.back-button {
  cursor: pointer;
  padding: 4px;
  margin-left: -8px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.back-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.header-info {
  flex: 1;
}

.name {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.status {
  margin: 0;
  font-size: 13px;
  opacity: 0.9;
}

.status.online {
  color: #a8f5a8;
}

.status.typing {
  color: #a8f5a8;
  font-style: italic;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: transparent;
  border: none;
  color: white;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.action-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}
</style>
