<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
    </div>
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">AIO</div>
        <h1 class="login-title">All-in-One</h1>
        <p class="login-subtitle">个人管理系统</p>
      </div>
      <a-form :model="form" @finish="handleLogin" class="login-form">
        <a-form-item name="username" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input
            v-model:value="form.username"
            size="large"
            placeholder="用户名"
            :prefix="h(UserOutlined)"
            @pressEnter="$refs.pwdInput.focus()"
          />
        </a-form-item>
        <a-form-item name="password" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password
            ref="pwdInput"
            v-model:value="form.password"
            size="large"
            placeholder="密码"
            :prefix="h(LockOutlined)"
          />
        </a-form-item>
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            :loading="loading"
            block
            class="login-btn"
          >
            登 录
          </a-button>
        </a-form-item>
      </a-form>
      <div class="login-footer">
        <div class="login-hint">默认用户名/密码：admin / admin，登录后及时设置安全码</div>
        <a class="login-forgot" @click="showReset = true">忘记密码？</a>
      </div>
    </div>

    <!-- 忘记密码弹窗 -->
    <a-modal
      v-model:open="showReset"
      title="重置密码"
      :footer="null"
      :width="400"
      centered
      :mask-closable="false"
    >
      <p style="color: #94a3b8; font-size: 13px; margin-bottom: 20px;">
        请输入用户名和安全码来重置密码。如果尚未设置安全码，请先登录后在设置中配置。
      </p>
      <a-form :model="resetForm" @finish="handleReset" layout="vertical">
        <a-form-item label="用户名" name="username" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input v-model:value="resetForm.username" placeholder="用户名" />
        </a-form-item>
        <a-form-item label="安全码" name="security_code" :rules="[{ required: true, message: '请输入安全码' }]">
          <a-input-password v-model:value="resetForm.security_code" placeholder="安全码" />
        </a-form-item>
        <a-form-item label="新密码" name="new_password" :rules="[{ required: true, message: '请输入新密码' }, { min: 4, message: '至少 4 个字符' }]">
          <a-input-password v-model:value="resetForm.new_password" placeholder="新密码（至少 4 个字符）" />
        </a-form-item>
        <a-form-item label="确认新密码" name="confirm_password" :rules="[
          { required: true, message: '请确认新密码' },
          { validator: (_, v) => v === resetForm.new_password ? Promise.resolve() : Promise.reject('两次密码不一致') }
        ]">
          <a-input-password v-model:value="resetForm.confirm_password" placeholder="再次输入新密码" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="resetLoading" block>
            重置密码
          </a-button>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { reactive, ref, h } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { authApi, markJustLoggedIn } from '@/api'

const router = useRouter()
const loading = ref(false)
const pwdInput = ref(null)

const form = reactive({
  username: '',
  password: '',
})

const showReset = ref(false)
const resetLoading = ref(false)
const resetForm = reactive({
  username: '',
  security_code: '',
  new_password: '',
  confirm_password: '',
})

async function handleLogin() {
  loading.value = true
  try {
    const { data } = await authApi.login(form.username, form.password)
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify(data.user))
    markJustLoggedIn()
    console.log('[登录] token 已保存:', data.token?.substring(0, 16) + '...', '准备跳转 /dashboard')
    message.success('登录成功')
    router.push('/dashboard')
  } catch (e) {
    const msg = e.response?.data?.detail || '登录失败'
    message.error(msg)
  } finally {
    loading.value = false
  }
}

async function handleReset() {
  resetLoading.value = true
  try {
    await authApi.resetPassword(resetForm.username, resetForm.security_code, resetForm.new_password)
    message.success('密码重置成功，请使用新密码登录')
    showReset.value = false
    Object.assign(resetForm, { username: '', security_code: '', new_password: '', confirm_password: '' })
  } catch (e) {
    const msg = e.response?.data?.detail || '重置失败'
    message.error(msg)
  } finally {
    resetLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #f1f5f9 0%, #e8edf2 40%, #dde5ee 100%);
  position: relative;
  overflow: hidden;
}
.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.bg-circle {
  position: absolute;
  border-radius: 50%;
}
.bg-circle-1 {
  width: 480px;
  height: 480px;
  background: radial-gradient(circle, rgba(99, 115, 144, 0.12) 0%, transparent 70%);
  top: -160px;
  right: -80px;
}
.bg-circle-2 {
  width: 320px;
  height: 320px;
  background: radial-gradient(circle, rgba(148, 163, 184, 0.1) 0%, transparent 70%);
  bottom: -80px;
  left: -60px;
}
.bg-circle-3 {
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(148, 163, 184, 0.08) 0%, transparent 70%);
  top: 60%;
  left: 55%;
  transform: translate(-50%, -50%);
}
.login-card {
  width: 400px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 20px;
  padding: 48px 40px 36px;
  position: relative;
  z-index: 1;
  box-shadow: 0 4px 40px rgba(71, 85, 105, 0.12), 0 1px 3px rgba(71, 85, 105, 0.06);
}
.login-header {
  text-align: center;
  margin-bottom: 36px;
}
.login-logo {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.5px;
  box-shadow: 0 4px 16px rgba(124, 58, 237, 0.3);
  margin-bottom: 16px;
}
.login-title {
  color: #1e293b;
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 4px;
  letter-spacing: -0.3px;
}
.login-subtitle {
  color: #94a3b8;
  font-size: 14px;
  margin: 0;
}
.login-form :deep(.ant-input-affix-wrapper) {
  background: #f8fafc !important;
  border-color: #e2e8f0 !important;
  border-radius: 12px !important;
  height: 48px;
  font-size: 15px;
  padding: 0 16px;
}
.login-form :deep(.ant-input-affix-wrapper input) {
  background: transparent !important;
  color: #334155 !important;
  font-size: 15px;
}
.login-form :deep(.ant-input-affix-wrapper:hover),
.login-form :deep(.ant-input-affix-wrapper-focused) {
  border-color: #94a3b8 !important;
  box-shadow: 0 0 0 2px rgba(148, 163, 184, 0.15) !important;
}
.login-form :deep(.ant-input-affix-wrapper input::placeholder) {
  color: #94a3b8 !important;
}
.login-form :deep(.ant-input-prefix) {
  color: #94a3b8;
  margin-right: 10px;
  font-size: 16px;
}
.login-btn {
  height: 48px !important;
  border-radius: 12px !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  background: linear-gradient(135deg, #475569, #64748b) !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(71, 85, 105, 0.25);
  letter-spacing: 2px;
}
.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(71, 85, 105, 0.3) !important;
}
.login-footer {
  text-align: center;
  margin-top: 8px;
}
.login-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}
.login-forgot {
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s;
}
.login-forgot:hover {
  color: #475569;
  text-decoration: underline;
}
</style>
