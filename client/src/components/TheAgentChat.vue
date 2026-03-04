<template>
  <div class="agent-chat-container">
    <!-- 聊天面板头部 -->
    <div class="agent-header">
      <div class="header-left">
        <div class="ai-avatar-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7H3a7 7 0 017-7h1V5.73A2 2 0 0110 4a2 2 0 012-2zM5 14v1a7 7 0 0014 0v-1H5zM9 17h.01M15 17h.01" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div>
          <div class="header-title">Complaint Agent</div>
          <div class="header-status">
            <span class="status-dot"></span>
            <span class="status-text">在线</span>
          </div>
        </div>
      </div>
      <button class="close-btn" @click="$emit('close')" v-if="!embedded">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M6 18L18 6M6 6l12 12" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

    <!-- 消息列表 -->
    <div class="messages-container" ref="messagesContainer">
      <div v-if="messages.length === 0" class="welcome-message">
        <div class="welcome-icon-wrap">
          <svg class="welcome-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" stroke-width="1.5"/>
            <path d="M8 13s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <p class="welcome-text">你好！我是投诉数据分析助手，试试问我：</p>
        <ul class="example-queries">
          <li @click="sendExampleQuery('显示统计数据')">
            <span class="example-icon">📊</span>
            显示统计数据
          </li>
          <li @click="sendExampleQuery('显示2024年的投诉趋势')">
            <span class="example-icon">📈</span>
            显示2024年的投诉趋势
          </li>
          <li @click="sendExampleQuery('生成本月报告')">
            <span class="example-icon">📋</span>
            生成本月报告
          </li>
        </ul>
      </div>

      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
        <div class="message-avatar" :class="msg.role">
          <svg v-if="msg.role === 'user'" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7H3a7 7 0 017-7h1V5.73A2 2 0 0110 4a2 2 0 012-2z" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="message-content">
          <div class="message-text" v-html="formatMessage(msg.content)"></div>
          <div v-if="msg.thinking" class="message-thinking">
            <details>
              <summary>
                <span class="thinking-icon">💭</span>
                思考过程
                <span class="thinking-chevron">›</span>
              </summary>
              <p>{{ msg.thinking }}</p>
            </details>
          </div>
          <div v-if="msg.action" class="message-action">
            <div class="action-badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M5 13l4 4L19 7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              已执行：{{ getActionLabel(msg.action.type) }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="isLoading" class="message assistant loading">
        <div class="message-avatar assistant">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7H3a7 7 0 017-7h1V5.73A2 2 0 0110 4a2 2 0 012-2z" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="input-container">
      <textarea
        v-model="inputMessage"
        @keydown.enter.prevent="handleSendMessage"
        placeholder="请输入您的问题..."
        :disabled="isLoading"
        rows="1"
        ref="inputTextarea"
      ></textarea>
      <button
        class="send-btn"
        @click="handleSendMessage"
        :disabled="!inputMessage.trim() || isLoading"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'

interface Message {
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  action?: {
    type: string
    data: any
    tool: string
    parameters: any
  }
}

interface Props {
  embedded?: boolean
  context?: any
}

const props = withDefaults(defineProps<Props>(), {
  embedded: false,
  context: () => ({})
})

const emit = defineEmits<{
  close: []
  action: [action: any]
}>()

const messages = ref<Message[]>([])
const inputMessage = ref('')
const isLoading = ref(false)
const messagesContainer = ref<HTMLElement>()
const inputTextarea = ref<HTMLTextAreaElement>()

async function handleSendMessage() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  messages.value.push({ role: 'user', content: userMessage })
  scrollToBottom()
  isLoading.value = true

  try {
    const response = await fetch('http://localhost:5000/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMessage, context: props.context || {} })
    })

    const data = await response.json()

    if (data.success) {
      messages.value.push({
        role: 'assistant',
        content: data.message,
        thinking: data.thinking,
        action: data.action
      })
      if (data.action) emit('action', data.action)
    } else {
      messages.value.push({
        role: 'assistant',
        content: `抱歉，${data.message || data.error || '处理失败'}`
      })
    }
  } catch (error) {
    console.error('Agent请求失败:', error)
    messages.value.push({
      role: 'assistant',
      content: '抱歉，连接失败，请确保后端服务正在运行。'
    })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

function sendExampleQuery(query: string) {
  inputMessage.value = query
  handleSendMessage()
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function formatMessage(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

function getActionLabel(type: string): string {
  const labels: Record<string, string> = {
    update_stats: '更新统计数据',
    update_trend: '更新趋势图',
    show_company: '显示企业详情',
    switch_chart_sunburst: '切换到旭日图',
    switch_chart_quadrant: '切换到散点图',
    show_report: '生成分析报告',
    show_rag: '法律咨询',
    filter_data: '筛选数据'
  }
  return labels[type] || type
}

watch(inputMessage, () => {
  nextTick(() => {
    if (inputTextarea.value) {
      inputTextarea.value.style.height = 'auto'
      inputTextarea.value.style.height = Math.min(inputTextarea.value.scrollHeight, 120) + 'px'
    }
  })
})
</script>

<style scoped>
/* ───────── 容器：铺满父级 ───────── */
.agent-chat-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  background: #f8f9ff;
  overflow: hidden;
}

/* ───────── Header ───────── */
.agent-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-avatar-header {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.ai-avatar-header svg {
  width: 17px;
  height: 17px;
  color: white;
}

.header-title {
  font-weight: 700;
  font-size: 13px;
  color: white;
  letter-spacing: 0.3px;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 1px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4ade80;
  animation: pulse-status 2s infinite;
  flex-shrink: 0;
}

@keyframes pulse-status {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}

.status-text {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.8);
}

.close-btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: white;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  border-radius: 6px;
  transition: background 0.2s;
}

.close-btn:hover { background: rgba(255, 255, 255, 0.25); }
.close-btn svg { width: 16px; height: 16px; }

/* ───────── 消息区域 ───────── */
.messages-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scroll-behavior: smooth;
}

.messages-container::-webkit-scrollbar {
  width: 4px;
}
.messages-container::-webkit-scrollbar-track {
  background: transparent;
}
.messages-container::-webkit-scrollbar-thumb {
  background: rgba(99, 102, 241, 0.2);
  border-radius: 2px;
}
.messages-container::-webkit-scrollbar-thumb:hover {
  background: rgba(99, 102, 241, 0.4);
}

/* ───────── 欢迎界面 ───────── */
.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 8px;
  text-align: center;
}

.welcome-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ede9fe, #ddd6fe);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
}

.welcome-icon {
  width: 28px;
  height: 28px;
  color: #7c3aed;
}

.welcome-text {
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 12px;
  line-height: 1.5;
}

.example-queries {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.example-queries li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
  color: #374151;
  text-align: left;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.example-queries li:hover {
  border-color: #a78bfa;
  background: #faf5ff;
  color: #7c3aed;
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.15);
}

.example-icon {
  font-size: 14px;
  flex-shrink: 0;
}

/* ───────── 消息行 ───────── */
.message {
  display: flex;
  gap: 8px;
  animation: slideIn 0.25s ease;
}

.message.user {
  flex-direction: row-reverse;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ───────── 头像 ───────── */
.message-avatar {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-avatar.user {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.35);
}

.message-avatar.assistant {
  background: linear-gradient(135deg, #e0e7ff, #ede9fe);
  color: #6366f1;
  border: 1px solid #c7d2fe;
}

.message-avatar svg {
  width: 15px;
  height: 15px;
}

/* ───────── 消息内容 ───────── */
.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.message.user .message-content {
  align-items: flex-end;
}

/* ───────── 气泡 ───────── */
.message-text {
  padding: 9px 13px;
  border-radius: 14px;
  line-height: 1.55;
  font-size: 13px;
  word-break: break-word;
  max-width: 100%;
}

.message.user .message-text {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 3px 10px rgba(99, 102, 241, 0.3);
}

.message.assistant .message-text {
  background: white;
  color: #1f2937;
  border-bottom-left-radius: 4px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

/* inline code */
.message-text :deep(code) {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
}

.message.user .message-text :deep(code) {
  background: rgba(255,255,255,0.2);
  color: white;
}

/* ───────── 思考过程 ───────── */
.message-thinking {
  font-size: 12px;
  color: #6b7280;
}

.message-thinking details {
  cursor: pointer;
  background: linear-gradient(135deg, #fafafa, #f5f3ff);
  border: 1px solid #ede9fe;
  border-radius: 10px;
  overflow: hidden;
}

.message-thinking summary {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  user-select: none;
  font-size: 11px;
  color: #7c3aed;
  font-weight: 500;
  list-style: none;
}

.message-thinking summary::-webkit-details-marker { display: none; }

.thinking-icon { font-size: 12px; }

.thinking-chevron {
  margin-left: auto;
  transition: transform 0.2s;
  font-size: 14px;
}

details[open] .thinking-chevron {
  transform: rotate(90deg);
}

.message-thinking p {
  padding: 8px 10px;
  margin: 0;
  font-size: 11px;
  line-height: 1.6;
  color: #4b5563;
  border-top: 1px dashed #ede9fe;
}

/* ───────── 动作标签 ───────── */
.message-action {
  margin-top: 2px;
}

.action-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: linear-gradient(135deg, #d1fae5, #a7f3d0);
  color: #065f46;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid #6ee7b7;
}

.action-badge svg { width: 12px; height: 12px; }

/* ───────── 打字指示器 ───────── */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  background: white;
  border-radius: 14px;
  border-bottom-left-radius: 4px;
  border: 1px solid #e5e7eb;
  width: fit-content;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.typing-indicator span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-7px); opacity: 1; }
}

/* ───────── 输入框区域 ───────── */
.input-container {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid #e5e7eb;
  background: white;
}

.input-container textarea {
  flex: 1;
  min-height: 36px;
  max-height: 120px;
  padding: 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  resize: none;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.5;
  overflow-y: auto;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #f9fafb;
  color: #1f2937;
}

.input-container textarea:focus {
  outline: none;
  border-color: #8b5cf6;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.12);
  background: white;
}

.input-container textarea:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
  color: #9ca3af;
}

.input-container textarea::placeholder {
  color: #9ca3af;
}

/* ───────── 发送按钮 ───────── */
.send-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border: none;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.45);
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.send-btn:disabled {
  background: #d1d5db;
  box-shadow: none;
  cursor: not-allowed;
}

.send-btn svg {
  width: 16px;
  height: 16px;
}
</style>
