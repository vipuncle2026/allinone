<template>
  <div class="dashboard">
    <!-- 骨架屏：首次加载时显示 -->
    <div v-if="loading" class="dashboard-skeleton">
      <div style="display: flex; gap: 16px; margin-bottom: 20px">
        <div style="flex-shrink: 0; width: 280px"><a-skeleton active :paragraph="false" :title="{ width: '60%' }" /></div>
        <div style="flex: 1; display: flex; gap: 16px">
          <div style="flex: 1"><a-skeleton active :paragraph="false" :title="{ width: '80%' }" /></div>
          <div style="flex: 1"><a-skeleton active :paragraph="false" :title="{ width: '80%' }" /></div>
          <div style="flex: 1"><a-skeleton active :paragraph="false" :title="{ width: '80%' }" /></div>
          <div style="flex: 1"><a-skeleton active :paragraph="false" :title="{ width: '80%' }" /></div>
        </div>
      </div>
      <a-row :gutter="16" style="margin-bottom: 20px">
        <a-col :span="12"><a-skeleton active paragraph /></a-col>
        <a-col :span="12"><a-skeleton active paragraph /></a-col>
      </a-row>
      <a-row :gutter="16">
        <a-col :span="12"><a-skeleton active paragraph /></a-col>
        <a-col :span="12"><a-skeleton active paragraph /></a-col>
      </a-row>
    </div>

    <!-- 实际内容：loading 完成后显示 -->
    <div v-if="!loading">
    <!-- 财务概览：总资产主视觉，后面四张卡片等宽 -->
    <div style="display: flex; gap: 16px; margin-bottom: 20px; align-items: stretch">
      <div style="flex-shrink: 0; width: 280px">
        <div class="stat-card stat-asset stat-asset-hero">
          <div class="stat-icon-bg"><span>💰</span></div>
          <div class="stat-info">
            <div class="stat-label">总资产</div>
            <div class="stat-value stat-value-hero">{{ formatMoney(financeStats.total_assets) }}</div>
          </div>
        </div>
      </div>
      <div style="flex: 1; display: flex; gap: 16px; min-width: 0">
        <div style="flex: 1; min-width: 0">
          <div class="stat-card stat-debt stat-sub-card">
            <div class="stat-icon-bg stat-icon-sm"><span>📉</span></div>
            <div class="stat-info">
              <div class="stat-label">总负债</div>
              <div class="stat-value stat-value-sub">{{ formatMoney(financeStats.total_debt) }}</div>
            </div>
          </div>
        </div>
        <div style="flex: 1; min-width: 0">
          <div class="stat-card stat-net stat-sub-card">
            <div class="stat-icon-bg stat-icon-sm"><span>✨</span></div>
            <div class="stat-info">
              <div class="stat-label">净资产</div>
              <div class="stat-value stat-value-sub">{{ formatMoney(financeStats.net_assets) }}</div>
            </div>
          </div>
        </div>
        <div style="flex: 1; min-width: 0">
          <div class="stat-card stat-fund stat-sub-card">
            <div class="stat-icon-bg stat-icon-sm"><span>📈</span></div>
            <div class="stat-info">
              <div class="stat-label">基金市值</div>
              <div class="stat-value stat-value-sub">{{ formatMoney(fundStats.totalMarketValue) }}</div>
            </div>
          </div>
        </div>
        <div style="flex: 1; min-width: 0">
          <div class="stat-card stat-lucky stat-sub-card">
            <div class="stat-icon-bg stat-icon-sm"><span>🧧</span></div>
            <div class="stat-info">
              <div class="stat-label">压岁钱</div>
              <div class="stat-value stat-value-sub">{{ formatMoney(financeStats.red_envelope_amount) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 今日/本周运动摘要 -->
    <a-row :gutter="16" style="margin-bottom: 20px; align-items: stretch" v-if="summary">
      <a-col :span="12">
        <div class="summary-card summary-today">
          <div class="summary-header">
            <span class="summary-badge today-badge">📅 昨日</span>
            <span class="summary-date">{{ summary.today.date }}</span>
          </div>
          <div class="summary-sports">
            <div class="summary-sport-item">
              <div class="sport-icon cycling-icon">🚴</div>
              <div class="sport-data">
                <div class="sport-count">{{ summary.today.cycling.count || '—' }}<span class="sport-unit">次</span></div>
                <div class="sport-sub" v-if="summary.today.cycling.count > 0">{{ summary.today.cycling.km }}km · ↑{{ summary.today.cycling.gain }}m</div>
                <div class="sport-sub sport-sub-empty" v-else>昨日暂无骑行记录</div>
              </div>
            </div>
            <div class="summary-sport-item">
              <div class="sport-icon hiking-icon">🥾</div>
              <div class="sport-data">
                <div class="sport-count">{{ summary.today.hiking.count || '—' }}<span class="sport-unit">次</span></div>
                <div class="sport-sub" v-if="summary.today.hiking.count > 0">{{ summary.today.hiking.km }}km · ↑{{ summary.today.hiking.gain }}m</div>
                <div class="sport-sub sport-sub-empty" v-else>昨日暂无徒步记录</div>
              </div>
            </div>
            <div class="summary-sport-item">
              <div class="sport-icon running-icon">🏃</div>
              <div class="sport-data">
                <div class="sport-count">{{ summary.today.running.count || '—' }}<span class="sport-unit">次</span></div>
                <div class="sport-sub" v-if="summary.today.running.count > 0">{{ summary.today.running.km }}km · {{ summary.today.running.hours }}h</div>
                <div class="sport-sub sport-sub-empty" v-else>昨日暂无跑步记录</div>
              </div>
            </div>
          </div>
        </div>
      </a-col>
      <a-col :span="12">
        <div class="summary-card summary-week">
          <div class="summary-header">
            <span class="summary-badge week-badge">📆 本周</span>
            <span class="summary-date summary-date-week">{{ summary.week.start_date }} ~ {{ summary.week.end_date }}</span>
          </div>
          <div class="summary-sports">
            <div class="summary-sport-item">
              <div class="sport-icon cycling-icon">🚴</div>
              <div class="sport-data">
                <div class="sport-count">{{ summary.week.cycling.count }}<span class="sport-unit">次</span></div>
                <div class="sport-sub">{{ summary.week.cycling.km }}km · {{ summary.week.cycling.hours }}h · ↑{{ summary.week.cycling.gain }}m</div>
              </div>
            </div>
            <div class="summary-sport-item">
              <div class="sport-icon hiking-icon">🥾</div>
              <div class="sport-data">
                <div class="sport-count">{{ summary.week.hiking.count }}<span class="sport-unit">次</span></div>
                <div class="sport-sub">{{ summary.week.hiking.km }}km · {{ summary.week.hiking.hours }}h · ↑{{ summary.week.hiking.gain }}m</div>
              </div>
            </div>
            <div class="summary-sport-item">
              <div class="sport-icon running-icon">🏃</div>
              <div class="sport-data">
                <div class="sport-count">{{ summary.week.running.count }}<span class="sport-unit">次</span></div>
                <div class="sport-sub">{{ summary.week.running.km }}km · {{ summary.week.running.hours }}h</div>
              </div>
            </div>
          </div>
        </div>
      </a-col>
    </a-row>

    <!-- 第一行：运动+车辆（4个） -->
    <div class="module-cards-row" style="margin-bottom: 16px; flex-wrap: wrap">
      <!-- 骑行 -->
      <div class="module-card card-cycling" :class="{ 'module-card-empty': cyclingStats.total_km == 0 }">
        <div class="card-topbar cycling-topbar"></div>
        <div class="module-card-header">
          <div class="module-icon cycling-icon">🚴</div>
          <span class="module-title">骑行管理</span>
          <a-button type="link" size="small" @click="$router.push({ name: 'cycling-list' })">查看全部 →</a-button>
        </div>
        <div class="module-stats-row">
          <div class="mini-stat mini-stat-hero">
            <div class="mini-value mini-value-hero">{{ cyclingStats.total_km }}</div>
            <div class="mini-label">总里程(km)</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ cyclingStats.total_activities }}</div>
            <div class="mini-label">总次数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ cyclingStats.total_hours }}</div>
            <div class="mini-label">总时长(h)</div>
          </div>
        </div>
        <div class="module-card-footer">
          <span>累计爬升 <strong>{{ cyclingStats.total_elevation_gain }}</strong>m</span>
          <a-button type="primary" size="small" class="btn-sport" @click="$router.push({ name: 'cycling-bikes', query: { upload: '1' } })">+ 上传</a-button>
        </div>
      </div>
      <!-- 徒步 -->
      <div class="module-card card-hiking" :class="{ 'module-card-empty': hikingStats.total_km == 0 }">
        <div class="card-topbar hiking-topbar"></div>
        <div class="module-card-header">
          <div class="module-icon hiking-icon">🥾</div>
          <span class="module-title">徒步管理</span>
          <a-button type="link" size="small" @click="$router.push({ name: 'hiking-list' })">查看全部 →</a-button>
        </div>
        <div class="module-stats-row">
          <div class="mini-stat mini-stat-hero">
            <div class="mini-value mini-value-hero">{{ hikingStats.total_km }}</div>
            <div class="mini-label">总里程(km)</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ hikingStats.total_activities }}</div>
            <div class="mini-label">总次数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ hikingStats.total_hours }}</div>
            <div class="mini-label">总时长(h)</div>
          </div>
        </div>
        <div class="module-card-footer">
          <span>累计爬升 <strong>{{ hikingStats.total_elevation_gain }}</strong>m</span>
          <a-button size="small" class="btn-sport" @click="$router.push({ name: 'hiking-upload' })">+ 导入</a-button>
        </div>
      </div>
      <!-- 跑步 -->
      <div class="module-card card-running" :class="{ 'module-card-empty': runningStats.total_km == 0 }">
        <div class="card-topbar running-topbar"></div>
        <div class="module-card-header">
          <div class="module-icon running-icon">🏃</div>
          <span class="module-title">跑步管理</span>
          <a-button type="link" size="small" @click="$router.push({ name: 'running-list' })">查看全部 →</a-button>
        </div>
        <div class="module-stats-row">
          <div class="mini-stat mini-stat-hero">
            <div class="mini-value mini-value-hero">{{ runningStats.total_km }}</div>
            <div class="mini-label">总里程(km)</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ runningStats.total_activities }}</div>
            <div class="mini-label">总次数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ runningStats.total_hours }}</div>
            <div class="mini-label">总时长(h)</div>
          </div>
        </div>
        <div class="module-card-footer">
          <span>累计消耗 <strong>{{ runningStats.total_calories }}</strong> kcal</span>
          <a-button size="small" class="btn-sport" @click="$router.push({ name: 'running-upload' })">+ 导入</a-button>
        </div>
      </div>
      <!-- 车辆 -->
      <div class="module-card card-vehicle">
        <div class="card-topbar vehicle-topbar"></div>
        <div class="module-card-header">
          <div class="module-icon vehicle-icon">🚗</div>
          <span class="module-title">车辆管理</span>
          <a-button type="link" size="small" @click="$router.push('/vehicle')">查看全部 →</a-button>
        </div>
        <div class="module-stats-row">
          <div class="mini-stat mini-stat-hero">
            <div class="mini-value mini-value-hero">{{ vehicleStats.count }}</div>
            <div class="mini-label">车辆数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ vehicleStats.fuelCount }}</div>
            <div class="mini-label">加油次数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ vehicleStats.expenseCount }}</div>
            <div class="mini-label">费用笔数</div>
          </div>
        </div>
        <div class="module-card-footer">
          <span class="footer-amount">总支出 ¥<strong>{{ vehicleStats.totalSpending }}</strong></span>
          <a-button size="small" class="btn-asset" @click="$router.push('/vehicle')">管理</a-button>
        </div>
      </div>
    </div>

    <!-- 第二行：财务+基金+物品+旅行（4个） -->
    <div class="module-cards-row module-cards-row-2" style="margin-bottom: 20px">
      <!-- 财务 -->
      <div class="module-card card-finance">
        <div class="card-topbar finance-topbar"></div>
        <div class="module-card-header">
          <div class="module-icon finance-icon">💰</div>
          <span class="module-title">财务管理</span>
          <a-button type="link" size="small" @click="$router.push({ name: 'finance-accounts-list' })">查看全部 →</a-button>
        </div>
        <div class="module-stats-row">
          <div class="mini-stat">
            <div class="mini-value">{{ financeStats.account_count }}</div>
            <div class="mini-label">账户数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ formatMoney(financeStats.month_income) }}</div>
            <div class="mini-label">本月收入</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ formatMoney(financeStats.month_expense) }}</div>
            <div class="mini-label">本月支出</div>
          </div>
        </div>
        <div class="module-card-footer">
          <span class="footer-amount">净资产 <strong>{{ formatMoney(financeStats.net_assets) }}</strong></span>
          <a-button size="small" class="btn-asset" @click="$router.push({ name: 'finance-accounts-list' })">管理</a-button>
        </div>
      </div>
      <!-- 基金 -->
      <div class="module-card card-fund">
        <div class="card-topbar fund-topbar"></div>
        <div class="module-card-header">
          <div class="module-icon fund-icon">📈</div>
          <span class="module-title">基金管理</span>
          <a-button type="link" size="small" @click="$router.push('/fund/list')">查看全部 →</a-button>
        </div>
        <div class="module-stats-row">
          <div class="mini-stat">
            <div class="mini-value">{{ fundStats.favoriteCount }}</div>
            <div class="mini-label">自选基金</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ fundStats.holdingCount }}</div>
            <div class="mini-label">持仓基金</div>
          </div>
        </div>
        <div class="module-card-footer">
          <span class="footer-amount">市值 <strong>{{ formatMoney(fundStats.totalMarketValue) }}</strong></span>
          <a-button size="small" class="btn-asset" @click="$router.push('/fund/list')">自选</a-button>
        </div>
      </div>
      <!-- 物品 -->
      <div class="module-card card-item" :class="{ 'module-card-empty': itemStats.total == 0 }">
        <div class="card-topbar item-topbar"></div>
        <div class="module-card-header">
          <div class="module-icon item-icon">📦</div>
          <span class="module-title">物品管理</span>
          <a-button type="link" size="small" @click="$router.push('/item')">查看全部 →</a-button>
        </div>
        <div class="module-stats-row">
          <div class="mini-stat">
            <div class="mini-value">{{ itemStats.total }}</div>
            <div class="mini-label">物品总数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ itemStats.categoryCount }}</div>
            <div class="mini-label">分类数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ itemStats.importantCount }}</div>
            <div class="mini-label">重要物品</div>
          </div>
        </div>
        <div class="module-card-footer">
          <span class="footer-amount">购入 <strong>{{ formatMoney(itemStats.totalPurchase) }}</strong></span>
          <a-button size="small" class="btn-asset" @click="$router.push('/item')">管理</a-button>
        </div>
      </div>
      <!-- 旅行 -->
      <div class="module-card card-travel" :class="{ 'module-card-empty': travelStats.tripCount == 0 }">
        <div class="card-topbar travel-topbar"></div>
        <div class="module-card-header">
          <div class="module-icon travel-icon">✈️</div>
          <span class="module-title">旅行管理</span>
          <a-button type="link" size="small" @click="$router.push('/travel')">查看全部 →</a-button>
        </div>
        <div class="module-stats-row">
          <div class="mini-stat mini-stat-hero">
            <div class="mini-value mini-value-hero">{{ travelStats.tripCount }}</div>
            <div class="mini-label">总次数</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">¥{{ travelStats.totalExpense }}</div>
            <div class="mini-label">总支出</div>
          </div>
          <div class="mini-stat">
            <div class="mini-value">{{ travelStats.totalKm }}</div>
            <div class="mini-label">总里程</div>
          </div>
        </div>
        <div class="module-card-footer">
          <span class="footer-amount">累计 <strong>{{ travelStats.tripCount }}</strong> 次</span>
          <a-button size="small" class="btn-asset" @click="$router.push('/travel')">管理</a-button>
        </div>
      </div>
    </div>

    <!-- 近期动态时间线 + 运动月历 + 基金持仓 -->
    <a-row :gutter="16" align="stretch">
      <!-- 时间线 40% -->
      <a-col :span="10" style="display: flex; flex-direction: column">
        <a-card title="🕐 近期动态" :bordered="false" size="small" class="timeline-card" style="flex: 1">
          <template #extra>
            <a-button type="link" size="small" style="padding: 0; font-size: 12px" @click="loadTimeline">刷新</a-button>
          </template>
          <div v-if="!timeline.length" class="tl-empty">
            <div style="font-size: 32px">📭</div>
            <div style="color: #94a3b8; font-size: 13px; margin-top: 6px">暂无动态</div>
          </div>
          <div class="tl-list" v-else>
            <div
              v-for="(ev, i) in timeline"
              :key="i"
              class="tl-item"
              :class="{ 'tl-item-last': i === timeline.length - 1 }"
              @click="ev.link && $router.push(ev.link)"
            >
              <div class="tl-dot" :style="{ background: ev.color }">{{ ev.icon }}</div>
              <div class="tl-line" v-if="i < timeline.length - 1"></div>
              <div class="tl-content">
                <div class="tl-header">
                  <span class="tl-tag" :style="{ color: ev.color }">{{ ev.tag }}</span>
                  <span class="tl-date">{{ ev.date }}</span>
                </div>
                <div class="tl-title">{{ ev.title }}</div>
                <div class="tl-meta">{{ ev.meta }}</div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
      <!-- 运动月历热力 -->
      <a-col :span="7" style="display: flex; flex-direction: column">
        <a-card :bordered="false" size="small" class="calendar-card" style="flex: 1">
          <template #title>
            <span style="display: flex; align-items: center; gap: 8px">
              🏃 {{ calendarYear }} 运动月历
            </span>
          </template>
          <template #extra>
            <span style="font-size: 11px; color: #94a3b8">
              🚴{{ calendarTotals.cycling_km }}km · 🥾{{ calendarTotals.hiking_km }}km · 🏃{{ calendarTotals.running_km }}km
            </span>
          </template>
          <div class="cal-grid">
            <div
              v-for="m in calendarData"
              :key="m.month"
              class="cal-cell"
              :style="{ '--intensity': calIntensity(m.total_km) }"
              @mouseenter="calHover = m"
              @mouseleave="calHover = null"
            >
              <div class="cal-month">{{ m.month }}月</div>
              <div class="cal-count" v-if="m.total_count > 0">{{ m.total_count }}次</div>
              <div v-if="m.total_count === 0" class="cal-dot-empty"></div>
            </div>
          </div>
          <!-- 图例 -->
          <div style="display: flex; align-items: center; gap: 6px; margin-top: 12px; justify-content: center">
            <span style="font-size: 11px; color: #94a3b8">少</span>
            <span class="cal-legend" style="--intensity: 0.1"></span>
            <span class="cal-legend" style="--intensity: 0.3"></span>
            <span class="cal-legend" style="--intensity: 0.5"></span>
            <span class="cal-legend" style="--intensity: 0.75"></span>
            <span class="cal-legend" style="--intensity: 1"></span>
            <span style="font-size: 11px; color: #94a3b8">多</span>
          </div>
          <!-- hover 提示 -->
          <div v-if="calHover && calHover.total_count > 0" class="cal-tooltip">
            <div style="font-weight: 600; margin-bottom: 4px">{{ calHover.month }}月</div>
            <div v-if="calHover.cycling_count > 0" style="color: #93c5fd">🚴 骑行 {{ calHover.cycling_count }}次 / {{ calHover.cycling_km }}km</div>
            <div v-if="calHover.hiking_count > 0" style="color: #86efac">🥾 徒步 {{ calHover.hiking_count }}次 / {{ calHover.hiking_km }}km</div>
            <div v-if="calHover.running_count > 0" style="color: #fed7aa">🏃 跑步 {{ calHover.running_count }}次 / {{ calHover.running_km }}km</div>
          </div>
        </a-card>

        <!-- 重要物品轮播 -->
        <div v-if="importantItems.length > 0" class="item-carousel-wrap">
          <a-carousel :dots="true" :autoplay="importantItems.length > 1" :autoplay-speed="3000" class="item-carousel">
            <div v-for="item in importantItems" :key="item.id" class="carousel-slide">
              <div class="item-card-single" @click="$router.push('/item')">
                <div class="item-card-photo">
                  <img :src="'/' + item.photo_path" :alt="item.name" />
                </div>
                <div class="item-card-info">
                  <div class="item-card-name">{{ item.name }}</div>
                  <div class="item-card-meta">
                    <span class="item-cat-tag">{{ item.category }}</span>
                    <span class="item-status-tag" :class="'status-' + (item.status || '在用')">{{ item.status || '在用' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </a-carousel>
        </div>
      </a-col>
      <!-- 基金持仓快览 -->
      <a-col :span="7" style="display: flex; flex-direction: column">
        <a-card :bordered="false" size="small" class="fund-card-dash" style="flex: 1">
          <template #title>
            <span style="display: flex; align-items: center; gap: 8px">📈 基金持仓</span>
          </template>
          <template #extra>
            <a-button type="link" size="small" style="padding: 0; font-size: 12px" @click="$router.push('/fund/holding')">详情 →</a-button>
          </template>
          <div v-if="fundHoldings.length === 0" class="fund-empty">
            <div style="color: #94a3b8; padding: 20px 0; font-size: 13px">暂无持仓</div>
          </div>
          <div class="fund-summary-bar" v-if="fundHoldings.length > 0">
            <div class="fund-summary-item">
              <span class="fund-summary-label">持仓市值</span>
              <span class="fund-summary-value">{{ formatMoney(fundSummary.total_market) }}</span>
            </div>
            <div class="fund-summary-item">
              <span class="fund-summary-label">总收益</span>
              <span class="fund-summary-value" :style="{ color: fundSummary.total_gain >= 0 ? '#e63946' : '#16a34a' }">
                {{ fundSummary.total_gain >= 0 ? '+' : '' }}{{ formatMoney(fundSummary.total_gain) }}
              </span>
            </div>
          </div>
          <div class="fund-list" v-if="fundHoldings.length > 0">
            <div
              v-for="h in fundHoldings"
              :key="h.code"
              class="fund-row"
              @click="$router.push('/fund/holding')"
            >
              <div class="fund-row-left">
                <div class="fund-name">{{ h.name }}</div>
                <div class="fund-shares">{{ h.shares }}份 · 净值 {{ h.cur_nav }}</div>
              </div>
              <div class="fund-row-right">
                <div class="fund-market">¥{{ h.market_value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</div>
                <div
                  class="fund-chg"
                  :style="{ color: (h.day_chg || 0) >= 0 ? '#e63946' : '#16a34a' }"
                >
                  {{ (h.day_chg || 0) >= 0 ? '+' : '' }}{{ (h.day_chg || 0).toFixed(2) }}%
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
  <!-- loading 结束标签 -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { cyclingApi, financeApi, fundApi, hikingApi, runningApi, vehicleApi, travelApi, dashboardApi, itemApi } from '@/api/index'

const router = useRouter()

// 加载状态
const loading = ref(true)

// 数据
const timeline = ref([])
const cyclingStats = ref({ total_km: 0, total_activities: 0, total_hours: 0, total_elevation_gain: 0 })
const hikingStats = ref({ total_km: 0, total_activities: 0, total_hours: 0, total_elevation_gain: 0 })
const runningStats = ref({ total_km: 0, total_activities: 0, total_hours: 0, total_calories: 0 })
const financeStats = ref({ total_assets: 0, total_debt: 0, net_assets: 0, red_envelope_amount: 0 })
const fundStats = ref({ favoriteCount: 0, holdingCount: 0, totalMarketValue: 0 })
const vehicleStats = ref({ count: 0, fuelCount: 0, expenseCount: 0, totalSpending: '0' })
const travelStats = ref({ tripCount: 0, totalExpense: '0', totalKm: '0', expenseCount: 0, totalBudget: '0', yearTrips: 0, yearExpense: '0', yearKm: '0', accommodationExpense: '0', diningExpense: '0', transportExpense: '0' })
const itemStats = ref({ total: 0, categoryCount: 0, importantCount: 0, totalPurchase: 0 })

// 运动月历
const calendarData = ref([])
const calendarYear = ref(new Date().getFullYear())
const calHover = ref(null)
const calendarTotals = computed(() => {
  const data = calendarData.value
  return {
    cycling_km: data.reduce((s, m) => s + m.cycling_km, 0).toFixed(1),
    hiking_km: data.reduce((s, m) => s + m.hiking_km, 0).toFixed(1),
    running_km: data.reduce((s, m) => s + (m.running_km || 0), 0).toFixed(1),
  }
})

// 基金持仓
const fundHoldings = ref([])
const fundSummary = ref({ total_market: 0, total_cost: 0, total_gain: 0, total_rate: 0 })

// 重要物品轮播
const importantItems = ref([])

// 今日/本周摘要
const summary = ref(null)

function formatMoney(val) {
  if (!val || val === 0) return '¥0.00'
  return '¥' + Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 运动月历热力色：根据里程计算 0~1
// maxKm=150：骑行+徒步合计超过150km/月视为满格，适配大多数人的月运动量
function calIntensity(km) {
  const maxKm = 150
  if (km <= 0) return 0
  return Math.min(Math.round((km / maxKm) * 10) / 10, 1)
}

async function loadTimeline() {
  try {
    const { data } = await dashboardApi.getTimeline(15)
    timeline.value = data || []
  } catch (e) { /* ignore */ }
}

async function loadCalendar() {
  try {
    const { data } = await dashboardApi.getActivityCalendar(calendarYear.value)
    calendarData.value = data?.months || []
  } catch (e) { /* ignore */ }
}

async function loadSummary() {
  try {
    const { data } = await dashboardApi.getSummary()
    summary.value = data
  } catch (e) { /* ignore */ }
}

async function loadFundHoldings() {
  try {
    const { data } = await fundApi.holdingSummary()
    fundSummary.value = {
      total_market: data.total_market || 0,
      total_cost: data.total_cost || 0,
      total_gain: data.total_gain || 0,
      total_rate: data.total_rate || 0,
    }
    // 只显示前 6 只
    fundHoldings.value = (data.holdings || []).slice(0, 6)
  } catch (e) { /* ignore */ }
}

async function loadImportantItems() {
  try {
    const { data } = await itemApi.listAll()
    // 筛选有照片的重要物品，按创建时间倒序取前 6
    importantItems.value = (data || [])
      .filter(item => item.is_important && item.photo_path)
      .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
      .slice(0, 6)
  } catch (e) { /* ignore */ }
}

onMounted(async () => {
  // 骑行统计
  try {
    const { data } = await cyclingApi.getStats()
    cyclingStats.value = data
  } catch (e) { /* ignore */ }

  // 徒步统计
  try {
    const { data } = await hikingApi.getStats()
    hikingStats.value = data
  } catch (e) { /* ignore */ }

  // 跑步统计
  try {
    const { data } = await runningApi.getStats()
    runningStats.value = data
  } catch (e) { /* ignore */ }

  // 财务统计
  try {
    const { data } = await financeApi.getStats()
    financeStats.value = data
  } catch (e) { /* ignore */ }

  // 基金统计（使用持仓分析接口的 total_market，与持仓分析页面一致）
  try {
    const [listRes, summaryRes] = await Promise.all([
      fundApi.list(),
      fundApi.holdingSummary(),
    ])
    const funds = listRes.data
    fundStats.value.favoriteCount = funds.length || 0
    fundStats.value.holdingCount = funds.filter(f => f.shares > 0).length
    fundStats.value.totalMarketValue = summaryRes.data.total_market || 0
  } catch (e) { /* ignore */ }

  // 车辆统计
  try {
    const { data: vehicles } = await vehicleApi.list()
    vehicleStats.value.count = vehicles.length
    vehicleStats.value.fuelCount = vehicles.reduce((s, v) => s + (v.fuel_count || 0), 0)
    vehicleStats.value.expenseCount = vehicles.reduce((s, v) => s + (v.expense_count || 0), 0)
    const totalSpending = vehicles.reduce((s, v) => s + (v.total_spending || 0), 0)
    vehicleStats.value.totalSpending = totalSpending.toLocaleString(undefined, { maximumFractionDigits: 0 })
  } catch (e) { /* ignore */ }

  // 旅行统计
  try {
    const { data } = await travelApi.listTrips()
    const trips = data || []
    travelStats.value.tripCount = trips.length
    travelStats.value.totalExpense = trips.reduce((s, t) => s + (t.total_expense || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    travelStats.value.totalKm = trips.reduce((s, t) => s + (t.total_km || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
    travelStats.value.expenseCount = trips.reduce((s, t) => s + (t.expense_count || 0), 0)
    travelStats.value.totalBudget = trips.reduce((s, t) => s + (t.budget || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    // 分类支出统计（住宿/餐饮/交通）
    try {
      const { data: catStats } = await travelApi.getCategoryStats()
      if (catStats && catStats.length > 0) {
        const fmt = (v) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        const find = (name) => (catStats.find(c => c.category === name) || {}).total || 0
        travelStats.value.accommodationExpense = fmt(find('住宿'))
        travelStats.value.diningExpense = fmt(find('餐饮'))
        travelStats.value.transportExpense = fmt(find('交通'))
      }
    } catch (e) { /* ignore */ }
    // 今年统计
    const thisYear = new Date().getFullYear()
    const yearTrips = trips.filter(t => t.start_date && t.start_date.startsWith(String(thisYear)))
    travelStats.value.yearTrips = yearTrips.length
    travelStats.value.yearExpense = yearTrips.reduce((s, t) => s + (t.total_expense || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    travelStats.value.yearKm = yearTrips.reduce((s, t) => s + (t.total_km || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
  } catch (e) { /* ignore */ }

  // 近期动态时间线
  loadTimeline()

  // 运动月历
  loadCalendar()

  // 今日/本周摘要
  loadSummary()

  // 基金持仓快览
  loadFundHoldings()

  // 重要物品轮播
  loadImportantItems()

  // 物品统计
  try {
    const { data } = await itemApi.getStats()
    itemStats.value = {
      total: data.total || 0,
      categoryCount: (data.by_category || []).length,
      importantCount: data.important_count || 0,
      totalPurchase: data.total_cost || 0,
    }
  } catch (e) { /* ignore */ }

  // 标记加载完成
  loading.value = false
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
}

/* 骨架屏样式 */
.dashboard-skeleton {
  padding: 0;
}
.dashboard-skeleton :deep(.ant-skeleton) {
  background: rgba(30, 32, 44, 0.8);
  border-radius: 8px;
  padding: 16px;
  min-height: 80px;
}
.dashboard-skeleton :deep(.ant-skeleton-content .ant-skeleton-title) {
  background: rgba(255, 255, 255, 0.1);
  height: 24px;
}
.dashboard-skeleton :deep(.ant-skeleton-content .ant-skeleton-paragraph > li) {
  background: rgba(255, 255, 255, 0.08);
  height: 14px;
  margin-top: 12px;
}

/* ─── 移动端响应式 ───────────────────── */
@media (max-width: 767px) {
  .dashboard > .ant-row:first-child .ant-col { flex: 0 0 50% !important; max-width: 50% !important; }
  .module-cards-row { flex-wrap: wrap; }
  .module-cards-row > .module-card { flex: 0 0 calc(50% - 8px) !important; min-width: calc(50% - 8px) !important; }
  .dashboard .ant-row .ant-col[style*="12"] { flex: 0 0 100% !important; max-width: 100% !important; }
  .dashboard .ant-row:last-child .ant-col { flex: 0 0 100% !important; max-width: 100% !important; }
  .tl-list { max-height: 280px !important; }
  .fund-list { max-height: 220px !important; }
  .mini-value { font-size: 16px !important; }
  .stat-value-hero { font-size: 20px !important; }
  .stat-value-sub { font-size: 16px !important; }
}

/* ══════════════════════════════════════════
   1. 财务概览卡片
   主视觉：总资产 40% 宽，其他三项各 20%
   色调：资产=蓝 / 负债=橙 / 净资产=绿 / 基金=紫
══════════════════════════════════════════ */
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 18px 16px 18px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 88px;
  height: 100%;
  box-sizing: border-box;
  border: 1px solid #f1f5f9;
  position: relative;
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.07); }

/* 左边条 */
.stat-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
}
.stat-asset::before  { background: #3b82f6; }
.stat-debt::before  { background: #f59e0b; }
.stat-net::before   { background: #10b981; }
.stat-fund::before  { background: #8b5cf6; }
.stat-lucky::before { background: #ef4444; }

/* 彩色图标 */
.stat-icon-bg {
  width: 40px; height: 40px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.stat-asset .stat-icon-bg  { background: #eff6ff; }
.stat-debt .stat-icon-bg   { background: #fff7ed; }
.stat-net .stat-icon-bg    { background: #f0fdf4; }
.stat-fund .stat-icon-bg   { background: #f5f3ff; }
.stat-lucky .stat-icon-bg  { background: #fef2f2; }
.stat-icon-bg span { font-size: 20px; }

/* 主视觉：总资产放大 */
.stat-asset-hero { min-height: 88px; }
.stat-asset-hero .stat-icon-bg { width: 48px; height: 48px; border-radius: 14px; }
.stat-asset-hero .stat-icon-bg span { font-size: 24px; }
.stat-asset-hero .stat-label { font-size: 13px; }
.stat-value-hero {
  font-size: 26px;
  font-weight: 800;
  color: #1e293b;
  letter-spacing: -1px;
}

/* 辅助卡片：略小 */
.stat-sub-card .stat-icon-sm { width: 32px; height: 32px; border-radius: 8px; }
.stat-sub-card .stat-icon-sm span { font-size: 16px; }
.stat-value-sub { font-size: 18px; font-weight: 700; color: #334155; letter-spacing: -0.3px; }

.stat-info { flex: 1; min-width: 0; }
.stat-label { font-size: 12px; color: #94a3b8; margin-bottom: 3px; font-weight: 500; }
.stat-value { color: #1e293b; }

/* ══════════════════════════════════════════
   2. 今日 / 本周摘要
   图标与数字垂直居中对齐，空状态柔和提示
══════════════════════════════════════════ */
.summary-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
  padding: 16px 20px;
  height: 100%;
  box-sizing: border-box;
}
.summary-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.summary-badge {
  font-size: 12px; font-weight: 600;
  padding: 3px 10px; border-radius: 20px;
}
.today-badge { background: #eff6ff; color: #3b82f6; }
.week-badge  { background: #f0fdf4; color: #10b981; }
.summary-date { font-size: 12px; color: #94a3b8; }
.summary-date-week { font-size: 11px; }

.summary-sports { display: flex; gap: 16px; }
.summary-sport-item {
  display: flex; align-items: center; gap: 10px; flex: 1;
}
.sport-icon {
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.cycling-icon  { background: #eff6ff; }
.hiking-icon   { background: #f0fdf4; }
.running-icon  { background: #fff7ed; }

.sport-data { min-width: 0; display: flex; flex-direction: column; justify-content: center; }
.sport-count {
  font-size: 18px; font-weight: 700;
  color: #1e293b; line-height: 1.2;
}
.sport-unit { font-size: 11px; font-weight: 400; color: #94a3b8; margin-left: 1px; }
.sport-sub { font-size: 11px; color: #94a3b8; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sport-sub-empty { color: #cbd5e1; }

/* ══════════════════════════════════════════
   3. 六大模块卡片
   间距 16px，运动类统一蓝色按钮，资产类统一灰蓝按钮
   关键数据（第一个 mini-stat）放大
══════════════════════════════════════════ */
.module-cards-row {
  display: flex;
  gap: 16px;
  align-items: stretch;
  flex-wrap: wrap;
}
.module-cards-row > .module-card { flex: 1; min-width: 0; }
.module-cards-row-2 > .module-card { flex: 1; min-width: 0; }

.module-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
  padding: 16px;
  min-height: 128px;
  display: flex; flex-direction: column;
  box-sizing: border-box;
  transition: box-shadow 0.2s, transform 0.2s;
  position: relative; overflow: hidden;
}
.module-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.07); transform: translateY(-1px); }

/* 空数据置灰 */
.module-card-empty { opacity: 0.55; filter: saturate(0.4); }
.module-card-empty:hover { opacity: 0.75; }

/* 顶部彩色条 */
.card-topbar { position: absolute; top: 0; left: 0; right: 0; height: 3px; border-radius: 12px 12px 0 0; }
.cycling-topbar { background: #3b82f6; }
.hiking-topbar  { background: #10b981; }
.running-topbar { background: #f97316; }
.vehicle-topbar { background: #475569; }
.finance-topbar { background: #3b82f6; }
.fund-topbar    { background: #8b5cf6; }
.item-topbar    { background: #64748b; }
.travel-topbar  { background: #f59e0b; }

/* 模块头部 */
.module-card-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 10px;
  white-space: nowrap; overflow: hidden;
}
.module-icon {
  width: 28px; height: 28px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex-shrink: 0;
}
.cycling-icon  { background: #eff6ff; }
.hiking-icon   { background: #f0fdf4; }
.running-icon  { background: #fff7ed; }
.vehicle-icon  { background: #f8fafc; }
.finance-icon  { background: #f0f9ff; }
.fund-icon     { background: #f5f3ff; }
.item-icon     { background: #f8fafc; }
.travel-icon   { background: #fffbeb; }

.module-title { font-size: 14px; font-weight: 600; color: #1e293b; flex: 1; }
.module-card-header .ant-btn-link { font-size: 12px; padding: 0; height: auto; color: #94a3b8 !important; }
.module-card-header .ant-btn-link:hover { color: #475569 !important; }

/* 统计数字行 */
.module-stats-row { display: flex; gap: 8px; flex: 1; }
.module-stats-row .mini-stat { flex: 1; text-align: center; padding: 4px 0; }

/* 关键数据放大 */
.mini-stat-hero .mini-value-hero {
  font-size: 22px !important;
  font-weight: 800 !important;
  color: #1e293b !important;
}
.mini-value { font-size: 18px; font-weight: 700; color: #334155; line-height: 1.2; }
.mini-label { font-size: 11px; color: #94a3b8; margin-top: 2px; }

/* 卡片底部 */
.module-card-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding-top: 10px; border-top: 1px solid #f8fafc;
  font-size: 12px; color: #64748b;
  white-space: nowrap; margin-top: 4px;
}
.module-card-footer strong { color: #475569; font-weight: 600; }
.footer-amount { text-align: left; }
.footer-amount strong { color: #334155; }

/* 统一按钮风格：运动类=主蓝色，资产类=灰蓝 */
.btn-sport { background: #3b82f6 !important; border-color: #3b82f6 !important; color: #fff !important; border-radius: 8px !important; font-size: 12px !important; padding: 0 14px !important; height: 28px !important; }
.btn-asset { background: #475569 !important; border-color: #475569 !important; color: #fff !important; border-radius: 8px !important; font-size: 12px !important; padding: 0 14px !important; height: 28px !important; }

/* ══════════════════════════════════════════
   4. 时间线（保留，色已柔和）
══════════════════════════════════════════ */
.timeline-card :deep(.ant-card-body) { padding: 12px 16px; }
.tl-empty { text-align: center; padding: 40px 0; }
.tl-list { display: flex; flex-direction: column; max-height: 460px; overflow-y: auto; padding-right: 2px; }
.tl-list::-webkit-scrollbar { width: 3px; }
.tl-list::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 2px; }
.tl-item {
  display: flex; gap: 12px; position: relative;
  cursor: pointer; padding: 6px 4px; border-radius: 8px;
  transition: background .15s;
}
.tl-item:hover { background: #f8fafc; }
.tl-dot {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex-shrink: 0; margin-top: 2px; opacity: .85;
}
.tl-line { position: absolute; left: 19px; top: 42px; width: 2px; height: calc(100% - 14px); background: #f1f5f9; }
.tl-content { flex: 1; min-width: 0; padding-bottom: 8px; }
.tl-header { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.tl-tag { font-size: 11px; font-weight: 600; }
.tl-date { font-size: 11px; color: #94a3b8; margin-left: auto; }
.tl-title { font-size: 13px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tl-meta { font-size: 12px; color: #64748b; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ══════════════════════════════════════════
   5. 运动月历（热力色更淡，只有高强度才明显）
══════════════════════════════════════════ */
.calendar-card :deep(.ant-card-body) { padding: 12px 16px; }
.cal-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.cal-cell {
  position: relative; border-radius: 8px;
  padding: 10px 6px; text-align: center;
  /* 柔和蓝灰热力：强度高时才显色，低强度几乎不可见 */
  background: rgba(59, 130, 246, calc(var(--intensity, 0) * 0.18));
  transition: background .2s, transform .15s;
  cursor: default; min-height: 52px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
}
.cal-cell:hover { transform: scale(1.05); box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.cal-month { font-size: 12px; font-weight: 600; color: #64748b; }
.cal-count { font-size: 11px; color: #2563eb; font-weight: 500; }
.cal-dot-empty { width: 6px; height: 6px; border-radius: 50%; background: #e2e8f0; }
.cal-legend { width: 16px; height: 16px; border-radius: 4px; background: rgba(59, 130, 246, calc(var(--intensity, 0) * 0.2)); }
.cal-tooltip {
  position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%);
  background: #1e293b; color: #f1f5f9; font-size: 12px;
  padding: 8px 12px; border-radius: 8px; white-space: nowrap; z-index: 10;
  box-shadow: 0 4px 12px rgba(0,0,0,.2); line-height: 1.6;
}

/* ══════════════════════════════════════════
   6. 基金持仓（收益色统一为 A 股红涨绿跌）
══════════════════════════════════════════ */
.fund-card-dash :deep(.ant-card-body) { padding: 12px 16px; }
.fund-empty { text-align: center; }
.fund-summary-bar { display: flex; gap: 16px; padding: 8px 12px; background: #f8fafc; border-radius: 8px; margin-bottom: 10px; }
.fund-summary-item { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.fund-summary-label { font-size: 11px; color: #94a3b8; }
.fund-summary-value { font-size: 15px; font-weight: 700; color: #1e293b; }
.fund-list { display: flex; flex-direction: column; gap: 6px; max-height: 360px; overflow-y: auto; padding-right: 2px; }
.fund-list::-webkit-scrollbar { width: 3px; }
.fund-list::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 2px; }
.fund-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border-radius: 8px; cursor: pointer; transition: background .15s;
}
.fund-row:hover { background: #f8fafc; }
.fund-row-left { min-width: 0; flex: 1; }
.fund-name { font-size: 13px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fund-shares { font-size: 11px; color: #94a3b8; margin-top: 1px; }
.fund-row-right { text-align: right; flex-shrink: 0; margin-left: 12px; }
.fund-market { font-size: 13px; font-weight: 600; color: #1e293b; }
.fund-chg { font-size: 12px; font-weight: 500; margin-top: 1px; }

/* ══════════════════════════════════════════
   7. 重要物品轮播
══════════════════════════════════════════ */
.item-carousel-wrap { margin-top: 8px; }
.item-carousel :deep(.slick-slider) { padding-bottom: 20px; }
.item-carousel :deep(.slick-dots) { bottom: 0; }
.item-carousel :deep(.slick-dots li button) { width: 5px; height: 5px; border-radius: 50%; background: #cbd5e1; }
.item-carousel :deep(.slick-dots li.slick-active button) { background: #6366f1; }
.item-carousel :deep(.slick-prev),
.item-carousel :deep(.slick-next) { width: 18px; height: 18px; font-size: 14px; z-index: 2; }
.item-carousel :deep(.slick-prev) { left: 6px; }
.item-carousel :deep(.slick-next) { right: 6px; }
.item-carousel :deep(.slick-prev::before),
.item-carousel :deep(.slick-next::before) { font-size: 18px; color: #94a3b8; }
.carousel-slide { padding: 2px 2px 0; }
.item-card-single {
  border-radius: 10px; overflow: hidden; background: #fff;
  border: 1px solid #f1f5f9; box-shadow: 0 2px 8px rgba(0,0,0,.06);
  cursor: pointer; transition: box-shadow .2s;
}
.item-card-single:hover { box-shadow: 0 4px 14px rgba(0,0,0,.1); }
.item-card-photo { width: 100%; aspect-ratio: 16/9; overflow: hidden; background: #f8fafc; }
.item-card-photo img { width: 100%; height: 100%; object-fit: cover; }
.item-card-info { padding: 8px 12px; }
.item-card-name { font-size: 13px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }
.item-card-meta { display: flex; align-items: center; justify-content: space-between; gap: 4px; }
.item-cat-tag { font-size: 11px; color: #6366f1; background: #f5f3ff; border-radius: 4px; padding: 1px 5px; }
.item-status-tag { font-size: 10px; border-radius: 4px; padding: 1px 5px; }
.status-在用 { color: #16a34a; background: #f0fdf4; }
.status-闲置 { color: #f59e0b; background: #fffbeb; }
.status-出借 { color: #3b82f6; background: #eff6ff; }
.status-已出售 { color: #94a3b8; background: #f8fafc; }
</style>
