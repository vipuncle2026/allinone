<template>
  <div class="achievements-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h2>🏆 运动成就</h2>
      <p class="page-desc">记录你每一次的突破与辉煌</p>
    </div>

    <!-- 成就加载状态 -->
    <div v-if="loading" class="achievements-loading">
      <a-spin size="large" tip="加载成就数据..." />
    </div>

    <!-- 成就内容 -->
    <div v-else class="achievements-content">

      <!-- 骑行成就卡片 -->
      <div class="sport-section">
        <div class="section-header">
          <span class="section-icon">🚴</span>
          <span class="section-title">骑行成就</span>
          <span class="section-summary">{{ cyclingStats.total_km || 0 }} km · {{ cyclingStats.total_activities || 0 }} 次</span>
        </div>
        <div class="achievement-grid">
          <!-- 最长距离 -->
          <div class="achievement-item" :class="{ unlocked: cyclingAchievements.longest_distance }">
            <div class="item-icon">📏</div>
            <div class="item-content">
              <div class="item-label">最长距离</div>
              <div class="item-value" v-if="cyclingAchievements.longest_distance">
                {{ cyclingAchievements.longest_distance.value }} <span class="unit">km</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="cyclingAchievements.longest_distance">{{ cyclingAchievements.longest_distance.date }}</div>
            </div>
          </div>

          <!-- 最长时长 -->
          <div class="achievement-item" :class="{ unlocked: cyclingAchievements.longest_duration }">
            <div class="item-icon">⏱️</div>
            <div class="item-content">
              <div class="item-label">最长时长</div>
              <div class="item-value" v-if="cyclingAchievements.longest_duration">
                {{ formatDuration(cyclingAchievements.longest_duration.value) }}
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="cyclingAchievements.longest_duration">{{ cyclingAchievements.longest_duration.date }}</div>
            </div>
          </div>

          <!-- 最高海拔 -->
          <div class="achievement-item" :class="{ unlocked: cyclingAchievements.highest_elevation }">
            <div class="item-icon">🏔️</div>
            <div class="item-content">
              <div class="item-label">最高海拔</div>
              <div class="item-value" v-if="cyclingAchievements.highest_elevation">
                {{ cyclingAchievements.highest_elevation.value }} <span class="unit">m</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="cyclingAchievements.highest_elevation">{{ cyclingAchievements.highest_elevation.date }}</div>
            </div>
          </div>

          <!-- 最高速度 -->
          <div class="achievement-item" :class="{ unlocked: cyclingAchievements.max_speed }">
            <div class="item-icon">💨</div>
            <div class="item-content">
              <div class="item-label">最高速度</div>
              <div class="item-value" v-if="cyclingAchievements.max_speed">
                {{ cyclingAchievements.max_speed.value }} <span class="unit">km/h</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="cyclingAchievements.max_speed">{{ cyclingAchievements.max_speed.date }}</div>
            </div>
          </div>

          <!-- 累计爬升 -->
          <div class="achievement-item unlocked" :class="{ highlight: cyclingStats.total_elevation_gain }">
            <div class="item-icon">⬆️</div>
            <div class="item-content">
              <div class="item-label">累计爬升</div>
              <div class="item-value" v-if="cyclingStats.total_elevation_gain">
                {{ cyclingStats.total_elevation_gain }} <span class="unit">m</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date">总爬升高度</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 徒步成就卡片 -->
      <div class="sport-section">
        <div class="section-header hiking-header">
          <span class="section-icon">🥾</span>
          <span class="section-title">徒步成就</span>
          <span class="section-summary">{{ hikingStats.total_km || 0 }} km · {{ hikingStats.total_activities || 0 }} 次</span>
        </div>
        <div class="achievement-grid">
          <!-- 最长距离 -->
          <div class="achievement-item" :class="{ unlocked: hikingAchievements.longest_distance }">
            <div class="item-icon">📏</div>
            <div class="item-content">
              <div class="item-label">最长距离</div>
              <div class="item-value" v-if="hikingAchievements.longest_distance">
                {{ hikingAchievements.longest_distance.value }} <span class="unit">km</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="hikingAchievements.longest_distance">{{ hikingAchievements.longest_distance.date }}</div>
            </div>
          </div>

          <!-- 最长时长 -->
          <div class="achievement-item" :class="{ unlocked: hikingAchievements.longest_duration }">
            <div class="item-icon">⏱️</div>
            <div class="item-content">
              <div class="item-label">最长时长</div>
              <div class="item-value" v-if="hikingAchievements.longest_duration">
                {{ formatDuration(hikingAchievements.longest_duration.value) }}
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="hikingAchievements.longest_duration">{{ hikingAchievements.longest_duration.date }}</div>
            </div>
          </div>

          <!-- 最快10公里 -->
          <div class="achievement-item" :class="{ unlocked: hikingAchievements.fastest_10km }">
            <div class="item-icon">⚡</div>
            <div class="item-content">
              <div class="item-label">最快 10km</div>
              <div class="item-value" v-if="hikingAchievements.fastest_10km">
                {{ formatDuration(hikingAchievements.fastest_10km.value) }}
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="hikingAchievements.fastest_10km">{{ hikingAchievements.fastest_10km.date }}</div>
            </div>
          </div>

          <!-- 最高海拔 -->
          <div class="achievement-item" :class="{ unlocked: hikingAchievements.highest_elevation }">
            <div class="item-icon">🏔️</div>
            <div class="item-content">
              <div class="item-label">最高海拔</div>
              <div class="item-value" v-if="hikingAchievements.highest_elevation">
                {{ hikingAchievements.highest_elevation.value }} <span class="unit">m</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="hikingAchievements.highest_elevation">{{ hikingAchievements.highest_elevation.date }}</div>
            </div>
          </div>

          <!-- 累计爬升 -->
          <div class="achievement-item unlocked" :class="{ highlight: hikingStats.total_elevation_gain }">
            <div class="item-icon">⬆️</div>
            <div class="item-content">
              <div class="item-label">累计爬升</div>
              <div class="item-value" v-if="hikingStats.total_elevation_gain">
                {{ hikingStats.total_elevation_gain }} <span class="unit">m</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date">总爬升高度</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 跑步成就卡片 -->
      <div class="sport-section">
        <div class="section-header running-header">
          <span class="section-icon">🏃</span>
          <span class="section-title">跑步成就</span>
          <span class="section-summary">{{ runningStats.total_km || 0 }} km · {{ runningStats.total_activities || 0 }} 次</span>
        </div>
        <div class="achievement-grid">
          <!-- 最长距离 -->
          <div class="achievement-item" :class="{ unlocked: runningAchievements.longest_distance }">
            <div class="item-icon">📏</div>
            <div class="item-content">
              <div class="item-label">最长距离</div>
              <div class="item-value" v-if="runningAchievements.longest_distance">
                {{ runningAchievements.longest_distance.value }} <span class="unit">km</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="runningAchievements.longest_distance">{{ runningAchievements.longest_distance.date }}</div>
            </div>
          </div>

          <!-- 最长时长 -->
          <div class="achievement-item" :class="{ unlocked: runningAchievements.longest_duration }">
            <div class="item-icon">⏱️</div>
            <div class="item-content">
              <div class="item-label">最长时长</div>
              <div class="item-value" v-if="runningAchievements.longest_duration">
                {{ formatDuration(runningAchievements.longest_duration.value) }}
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="runningAchievements.longest_duration">{{ runningAchievements.longest_duration.date }}</div>
            </div>
          </div>

          <!-- 最快5公里 -->
          <div class="achievement-item" :class="{ unlocked: runningAchievements.fastest_5km }">
            <div class="item-icon">⚡</div>
            <div class="item-content">
              <div class="item-label">最快 5km</div>
              <div class="item-value" v-if="runningAchievements.fastest_5km">
                {{ formatDuration(runningAchievements.fastest_5km.value) }}
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="runningAchievements.fastest_5km">{{ runningAchievements.fastest_5km.date }}</div>
            </div>
          </div>

          <!-- 最快10公里 -->
          <div class="achievement-item" :class="{ unlocked: runningAchievements.fastest_10km }">
            <div class="item-icon">⚡⚡</div>
            <div class="item-content">
              <div class="item-label">最快 10km</div>
              <div class="item-value" v-if="runningAchievements.fastest_10km">
                {{ formatDuration(runningAchievements.fastest_10km.value) }}
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="runningAchievements.fastest_10km">{{ runningAchievements.fastest_10km.date }}</div>
            </div>
          </div>

          <!-- 最快半马 -->
          <div class="achievement-item" :class="{ unlocked: runningAchievements.fastest_halfmarathon }">
            <div class="item-icon">🏅</div>
            <div class="item-content">
              <div class="item-label">最快半马</div>
              <div class="item-value" v-if="runningAchievements.fastest_halfmarathon">
                {{ formatDuration(runningAchievements.fastest_halfmarathon.value) }}
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="runningAchievements.fastest_halfmarathon">{{ runningAchievements.fastest_halfmarathon.date }}</div>
            </div>
          </div>

          <!-- 最快全马 -->
          <div class="achievement-item" :class="{ unlocked: runningAchievements.fastest_marathon }">
            <div class="item-icon">🏆</div>
            <div class="item-content">
              <div class="item-label">最快全马</div>
              <div class="item-value" v-if="runningAchievements.fastest_marathon">
                {{ formatDuration(runningAchievements.fastest_marathon.value) }}
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date" v-if="runningAchievements.fastest_marathon">{{ runningAchievements.fastest_marathon.date }}</div>
            </div>
          </div>

          <!-- 累计消耗 -->
          <div class="achievement-item unlocked" :class="{ highlight: runningStats.total_calories }">
            <div class="item-icon">🔥</div>
            <div class="item-content">
              <div class="item-label">累计消耗</div>
              <div class="item-value" v-if="runningStats.total_calories">
                {{ runningStats.total_calories }} <span class="unit">kcal</span>
              </div>
              <div class="item-empty" v-else>--</div>
              <div class="item-date">总热量消耗</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { cyclingApi, hikingApi, runningApi } from '@/api/index'

// 统计数据
const cyclingStats = ref({ total_km: 0, total_activities: 0, total_hours: 0, total_elevation_gain: 0 })
const hikingStats = ref({ total_km: 0, total_activities: 0, total_hours: 0, total_elevation_gain: 0 })
const runningStats = ref({ total_km: 0, total_activities: 0, total_hours: 0, total_calories: 0 })

// 成就数据
const cyclingAchievements = ref({})
const hikingAchievements = ref({})
const runningAchievements = ref({})

// 加载状态
const loading = ref(true)

// 格式化时长（秒转为 h:m:s 或 m:s）
function formatDuration(seconds) {
  if (!seconds) return '--'
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}m${s.toString().padStart(2, '0')}s`
  }
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h${m.toString().padStart(2, '0')}m`
}

onMounted(async () => {
  loading.value = true

  try {
    // 并行加载所有数据
    const [cyclingRes, hikingRes, runningRes] = await Promise.all([
      Promise.all([cyclingApi.getStats(), cyclingApi.getAchievements()]),
      Promise.all([hikingApi.getStats(), hikingApi.getAchievements()]),
      Promise.all([runningApi.getStats(), runningApi.getAchievements()]),
    ])

    // 骑行
    cyclingStats.value = cyclingRes[0].data || {}
    cyclingAchievements.value = cyclingRes[1].data || {}

    // 徒步
    hikingStats.value = hikingRes[0].data || {}
    hikingAchievements.value = hikingRes[1].data || {}

    // 跑步
    runningStats.value = runningRes[0].data || {}
    runningAchievements.value = runningRes[1].data || {}

  } catch (e) {
    console.error('加载成就失败:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.achievements-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: #000;
}

.page-desc {
  color: #333;
  margin: 0;
}

.achievements-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.achievements-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 运动分类区块 */
.sport-section {
  background: rgba(30, 32, 44, 0.85);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.section-header.hiking-header {
  border-bottom-color: rgba(16, 185, 129, 0.3);
}

.section-header.running-header {
  border-bottom-color: rgba(249, 115, 22, 0.3);
}

.section-icon {
  font-size: 28px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.section-summary {
  margin-left: auto;
  font-size: 14px;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.05);
  padding: 4px 12px;
  border-radius: 16px;
}

/* 成就网格 */
.achievement-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.achievement-item {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: all 0.2s ease;
}

.achievement-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
}

.achievement-item.unlocked {
  border-color: rgba(99, 102, 241, 0.25);
}

.achievement-item.highlight {
  background: rgba(99, 102, 241, 0.12);
  border-color: rgba(99, 102, 241, 0.35);
}

.item-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-label {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.item-value {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  line-height: 1.2;
}

.item-value .unit {
  font-size: 13px;
  font-weight: 400;
  color: #94a3b8;
}

.item-empty {
  font-size: 20px;
  font-weight: 600;
  color: #475569;
}

.item-date {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 移动端适配 */
@media (max-width: 767px) {
  .achievements-page {
    padding: 16px;
  }

  .achievement-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .achievement-item {
    padding: 12px;
  }

  .item-icon {
    font-size: 20px;
  }

  .item-value {
    font-size: 16px;
  }

  .section-summary {
    display: none;
  }
}
</style>
