<template>
  <div style="width: 100%; height: 100%; position: relative">
    <!-- 瓦片切换按钮 -->
    <div v-if="showTileBar" style="position: absolute; top: 8px; right: 8px; z-index: 1000; display: flex; gap: 4px">
      <a-button
        v-for="t in tileOptions" :key="t.key"
        :type="activeTile === t.key ? 'primary' : 'default'"
        size="small"
        @click="switchTile(t.key)"
      >{{ t.label }}</a-button>
    </div>
    <div ref="mapEl" style="width: 100%; height: 100%"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import L from 'leaflet'

// 修复 Leaflet 默认图标路径问题
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: '/leaflet/images/marker-icon-2x.png',
  iconUrl: '/leaflet/images/marker-icon.png',
  shadowUrl: '/leaflet/images/marker-shadow.png',
})

const props = defineProps({
  trackPoints: { type: Array, default: () => [] },
  showTileBar: { type: Boolean, default: false },
  defaultTile: { type: String, default: 'gaode-normal' },
  trackColor: { type: String, default: '#FF6B35' },
  coordType: { type: String, default: 'gcj02' }, // 'gcj02' | 'wgs84'
})

const mapEl = ref(null)
let map = null
let tileLayer = null
let polyline = null
let startMarker = null
let endMarker = null
let activeTile = props.defaultTile

// ─── 瓦片源（参考 sports 项目） ───
const tileOptions = [
  { key: 'gaode-normal', label: '普通', url: 'https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}' },
  { key: 'gaode-satellite', label: '卫星', url: 'https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}' },
  { key: 'gaode-hybrid', label: '混合', url: 'https://webst01.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}' },
  { key: 'osm', label: 'OSM', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png' },
]

// ─── WGS84 → GCJ02 坐标转换（国测局坐标，高德地图使用） ───
// 参考 sports 项目中的实现
const PI = Math.PI
const ee = 0.00669342162296594323
const a = 6378245.0

function outOfChina(lat, lng) {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
}

function transformLat(x, y) {
  let r = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  r += (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3
  r += (20 * Math.sin(y * PI) + 40 * Math.sin(y / 3 * PI)) * 2 / 3
  r += (160 * Math.sin(y / 12 * PI) + 320 * Math.sin(y * PI / 30)) * 2 / 3
  return r
}

function transformLng(x, y) {
  let r = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  r += (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3
  r += (20 * Math.sin(x * PI) + 40 * Math.sin(x / 3 * PI)) * 2 / 3
  r += (150 * Math.sin(x / 12 * PI) + 300 * Math.sin(x / 30 * PI)) * 2 / 3
  return r
}

function wgs84ToGcj02(lat, lng) {
  if (outOfChina(lat, lng)) return [lat, lng]
  let dLat = transformLat(lng - 105, lat - 35)
  let dLng = transformLng(lng - 105, lat - 35)
  const radLat = lat / 180 * PI
  let magic = Math.sin(radLat)
  magic = 1 - ee * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180) / ((a * (1 - ee)) / (magic * sqrtMagic) * PI)
  dLng = (dLng * 180) / (a / sqrtMagic * Math.cos(radLat) * PI)
  return [lat + dLat, lng + dLng]
}

function gcj02ToWgs84(lat, lng) {
  if (outOfChina(lat, lng)) return [lat, lng]
  let dLat = transformLat(lng - 105, lat - 35)
  let dLng = transformLng(lng - 105, lat - 35)
  const radLat = lat / 180 * PI
  let magic = Math.sin(radLat)
  magic = 1 - ee * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180) / ((a * (1 - ee)) / (magic * sqrtMagic) * PI)
  dLng = (dLng * 180) / (a / sqrtMagic * Math.cos(radLat) * PI)
  return [lat - dLat, lng - dLng]
}

// ─── 瓦片切换 ───
function switchTile(key) {
  const prevTile = activeTile
  activeTile = key
  if (!map) return
  if (tileLayer) map.removeLayer(tileLayer)
  const t = tileOptions.find(t => t.key === key)
  tileLayer = L.tileLayer(t.url, { attribution: '© 高德地图', maxZoom: 18 }).addTo(map)

  // 如果坐标系发生变化（高德↔OSM），需要重新绘制轨迹
  const prevIsGaode = prevTile.startsWith('gaode')
  const nowIsGaode = key.startsWith('gaode')
  if (prevIsGaode !== nowIsGaode && props.trackPoints.length) {
    renderTrack()
  }
}

onMounted(() => {
  initMap()
  if (props.trackPoints.length) renderTrack()
})

watch(() => props.trackPoints, () => {
  if (props.trackPoints.length) renderTrack()
})

onUnmounted(() => {
  if (map) { map.remove(); map = null }
})

function initMap() {
  if (!mapEl.value || map) return
  map = L.map(mapEl.value, { zoomControl: true })
  const t = tileOptions.find(t => t.key === activeTile)
  tileLayer = L.tileLayer(t.url, { attribution: '© 高德地图', maxZoom: 18 }).addTo(map)
}

function renderTrack() {
  if (!map) return
  // 清除旧轨迹
  if (polyline) map.removeLayer(polyline)
  if (startMarker) map.removeLayer(startMarker)
  if (endMarker) map.removeLayer(endMarker)

  const useGaode = activeTile.startsWith('gaode')

  const pts = props.trackPoints
    .map(p => {
      let lat, lon
      if (Array.isArray(p)) { lat = +p[0]; lon = +p[1] }
      else { lat = +p.lat; lon = +p.lon }
      if (!lat || !lon) return null

      // 坐标转换逻辑：根据输入坐标类型和当前瓦片坐标系决定
      if (props.coordType === 'gcj02') {
        // 输入是 GCJ-02，高德直接用，OSM 需要反转为 WGS-84
        return useGaode ? [lat, lon] : gcj02ToWgs84(lat, lon)
      } else {
        // 输入是 WGS-84，OSM 直接用，高德需要转为 GCJ-02
        return useGaode ? wgs84ToGcj02(lat, lon) : [lat, lon]
      }
    })
    .filter(Boolean)

  if (!pts.length) return

  const latlngs = pts.map(p => [p[0], p[1]])

  // 绘制轨迹线
  polyline = L.polyline(latlngs, {
    color: props.trackColor,
    weight: 4,
    opacity: 0.85,
  }).addTo(map)

  // 起点（绿色）
  startMarker = L.circleMarker(latlngs[0], {
    radius: 8, color: '#fff', fillColor: '#22c55e', fillOpacity: 1, weight: 2
  }).addTo(map).bindPopup('起点')

  // 终点（红色）
  endMarker = L.circleMarker(latlngs[latlngs.length - 1], {
    radius: 8, color: '#fff', fillColor: '#ef4444', fillOpacity: 1, weight: 2
  }).addTo(map).bindPopup('终点')

  // 自适应视野
  map.fitBounds(polyline.getBounds(), { padding: [30, 30] })
}

// 暴露 switchTile 方法供父组件调用
defineExpose({ switchTile })
</script>
