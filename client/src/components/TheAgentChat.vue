<template>
  <div class="agent-chat-container">
    <!-- 聊天面板头部 -->
    <div class="agent-header">
      <div class="header-title">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>Complaint Agent</span>
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
        <svg class="welcome-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="12" cy="12" r="10" stroke-width="2"/>
          <path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <p>你好！我可以帮你查询投诉数据、生成分析报告等。试试问我：</p>
        <ul class="example-queries">
          <li @click="sendExampleQuery('显示统计数据')">显示统计数据</li>
          <li @click="sendExampleQuery('显示2024年的投诉趋势')">显示2024年的投诉趋势</li>
          <li @click="sendExampleQuery('生成本月报告')">生成本月报告</li>
        </ul>
      </div>

      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
        <div class="message-avatar">
          <svg v-if="msg.role === 'user'" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 9h-2V5h2v6zm0 4h-2v-2h2v2z"/>
          </svg>
        </div>
        <div class="message-content">
          <div class="message-text" v-html="formatMessage(msg.content)"></div>
          <div v-if="msg.thinking" class="message-thinking">
            <details>
              <summary>💭 思考过程</summary>
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
        <div class="message-avatar">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 9h-2V5h2v6zm0 4h-2v-2h2v2z"/>
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
  context?: any  // 新增：从父组件传入的上下文数据
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

// 发送消息
async function handleSendMessage() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: userMessage
  })

  scrollToBottom()
  isLoading.value = true

  try {
    // 调用后端API - 包含上下文数据
    const response = await fetch('http://localhost:5000/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: userMessage,
        context: props.context || {}  // 传递上下文数据
      })
    })

    const data = await response.json()

    if (data.success) {
      // 添加assistant消息
      messages.value.push({
        role: 'assistant',
        content: data.message,
        thinking: data.thinking,
        action: data.action
      })

      // 如果有动作，通知父组件执行
      if (data.action) {
        emit('action', data.action)
      }
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

// 发送示例查询
function sendExampleQuery(query: string) {
  inputMessage.value = query
  handleSendMessage()
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 格式化消息（支持简单的markdown）
function formatMessage(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
}

// 获取动作标签
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

// 自动调整文本框高度
watch(inputMessage, () => {
  nextTick(() => {
    if (inputTextarea.value) {
      inputTextarea.value.style.height = 'auto'
      inputTextarea.value.style.height = inputTextarea.value.scrollHeight + 'px'
    }
  })
})
</script>

<style scoped>
.agent-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.agent-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}

.header-title .icon {
  width: 20px;
  height: 20px;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.close-btn:hover {
  opacity: 1;
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-message {
  text-align: center;
  padding: 32px 16px;
  color: #666;
}

.welcome-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  color: #667eea;
}

.example-queries {
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.example-queries li {
  padding: 8px 16px;
  background: #f5f5f5;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.example-queries li:hover {
  background: #667eea;
  color: white;
  transform: translateY(-1px);
}

.message {
  display: flex;
  gap: 12px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message.user .message-avatar {
  background: #667eea;
  color: white;
}

.message.assistant .message-avatar {
  background: #f0f0f0;
  color: #666;
}

.message-avatar svg {
  width: 20px;
  height: 20px;
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.5;
  font-size: 14px;
}

.message.user .message-text {
  background: #667eea;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-text {
  background: #f5f5f5;
  color: #333;
  border-bottom-left-radius: 4px;
}

.message-thinking {
  font-size: 13px;
  color: #666;
}

.message-thinking details {
  cursor: pointer;
}

.message-thinking summary {
  padding: 8px;
  background: #fafafa;
  border-radius: 8px;
  user-select: none;
}

.message-thinking p {
  padding: 8px;
  margin: 4px 0 0;
  background: #f9f9f9;
  border-radius: 8px;
  font-size: 12px;
}

.message-action {
  margin-top: 4px;
}

.action-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.action-badge svg {
  width: 14px;
  height: 14px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: #f5f5f5;
  border-radius: 12px;
  width: fit-content;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.input-container {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  background: white;
}

.input-container textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  max-height: 120px;
  overflow-y: auto;
}

.input-container textarea:focus {
  outline: none;
  border-color: #667eea;
}

.input-container textarea:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.send-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border: none;
  background: #667eea;
  color: white;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #5568d3;
  transform: translateY(-1px);
}

.send-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.send-btn svg {
  width: 20px;
  height: 20px;
}
</style>
