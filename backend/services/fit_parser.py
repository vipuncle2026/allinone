"""FIT 文件解析服务（支持 Garmin 等设备导出格式）"""
import json
import statistics
from fitparse import FitFile

from .coord_transform import wgs84_to_gcj02

# Garmin semicircles → degrees 转换系数
SEMICIRCLE_TO_DEG = 180.0 / (2 ** 31)


def parse_fit(file_path: str) -> dict:
    ff = FitFile(file_path)

    records = []
    for msg in ff.get_messages("record"):
        r = {f.name: f.value for f in msg}
        records.append(r)

    if not records:
        raise ValueError("FIT 文件中未找到 record 数据")

    # 读取 session 汇总数据（Garmin 设备会写入）
    session_data = {}
    for msg in ff.get_messages("session"):
        session_data = {f.name: f.value for f in msg}
        break  # 取第一个 session

    # 提取并转换轨迹点（WGS-84 → GCJ-02）
    track_points = []
    for r in records:
        lat = r.get("position_lat")
        lon = r.get("position_long")
        if lat is None or lon is None:
            continue
        # Garmin 使用 semicircles 编码，需转换
        lat_deg = lat * SEMICIRCLE_TO_DEG if isinstance(lat, int) else lat
        lon_deg = lon * SEMICIRCLE_TO_DEG if isinstance(lon, int) else lon
        # WGS-84 → GCJ-02（国内地图偏移修正）
        gcj_lat, gcj_lon = wgs84_to_gcj02(lat_deg, lon_deg)

        track_points.append({
            "lat": round(gcj_lat, 6),
            "lon": round(gcj_lon, 6),
            "ele": round(r["altitude"], 1) if r.get("altitude") is not None else None,
            "time": str(r["timestamp"]) if r.get("timestamp") else None,
            "power": r.get("power"),
            "heart_rate": r.get("heart_rate"),
            "cadence": r.get("cadence"),
            "speed": round(r["speed"] * 3.6, 2) if r.get("speed") else None,
        })

    # 统计数据优先从 session 取，否则自行计算
    distance_m = session_data.get("total_distance") or 0
    duration_sec = int(session_data.get("total_timer_time") or 0)
    elevation_gain = session_data.get("total_ascent")
    elevation_loss = session_data.get("total_descent")
    avg_speed_raw = session_data.get("avg_speed")
    max_speed_raw = session_data.get("max_speed")

    # 从 record 中提取海拔极值
    altitudes = [r.get("altitude") for r in records if r.get("altitude") is not None]
    max_elevation = round(max(altitudes), 1) if altitudes else None
    min_elevation = round(min(altitudes), 1) if altitudes else None

    # 功率
    powers = [r.get("power") for r in records if r.get("power") is not None]
    avg_power = round(statistics.mean(powers)) if powers else None
    max_power = max(powers) if powers else None
    np_power = _calc_normalized_power(powers) if len(powers) > 30 else None

    # 心率
    hrs = [r.get("heart_rate") for r in records if r.get("heart_rate") is not None]
    avg_hr = round(statistics.mean(hrs)) if hrs else None
    max_hr = max(hrs) if hrs else None

    # 踏频 — 优先使用 session 汇总值
    cadences = [r.get("cadence") for r in records if r.get("cadence") is not None]
    avg_cad = session_data.get("avg_cadence") or (round(statistics.mean(cadences)) if cadences else None)
    max_cad = session_data.get("max_cadence") or (max(cadences) if cadences else None)

    # 卡路里
    calories = session_data.get("total_calories")
    tss = _calc_tss(np_power, duration_sec, ftp=200) if np_power and duration_sec else None

    # 起止时间
    start_time = track_points[0]["time"] if track_points else None
    end_time = track_points[-1]["time"] if track_points else None

    # 压缩轨迹用于地图渲染
    compressed = _compress_track(track_points, max_points=600)

    return {
        "distance_km": round(distance_m / 1000, 2),
        "duration_sec": duration_sec,
        "elevation_gain": round(elevation_gain, 1) if elevation_gain else None,
        "elevation_loss": round(elevation_loss, 1) if elevation_loss else None,
        "max_elevation": max_elevation,
        "min_elevation": min_elevation,
        "avg_speed_kmh": round(avg_speed_raw * 3.6, 2) if avg_speed_raw else None,
        "max_speed_kmh": round(max_speed_raw * 3.6, 2) if max_speed_raw else None,
        "avg_power_w": avg_power,
        "max_power_w": max_power,
        "normalized_power": round(np_power, 1) if np_power else None,
        "tss": round(tss, 1) if tss else None,
        "avg_heart_rate": avg_hr,
        "max_heart_rate": max_hr,
        "avg_cadence": avg_cad,
        "max_cadence": max_cad,
        "calories": calories,
        "start_time": start_time,
        "end_time": end_time,
        "track_points": track_points,
        "track_json": json.dumps(compressed, ensure_ascii=False),
    }


def _calc_normalized_power(powers: list) -> float:
    """计算标准化功率 NP（30秒滚动均值的4次方均值的4次方根）"""
    if len(powers) < 30:
        return statistics.mean(powers)
    rolling = []
    for i in range(29, len(powers)):
        rolling.append(statistics.mean(powers[i - 29: i + 1]))
    fourth_powers = [p ** 4 for p in rolling]
    return statistics.mean(fourth_powers) ** 0.25


def _calc_tss(np_power: float, duration_sec: int, ftp: int = 200) -> float:
    """计算训练压力分 TSS = (duration * NP * IF) / (FTP * 3600) * 100"""
    intensity_factor = np_power / ftp
    return (duration_sec * np_power * intensity_factor) / (ftp * 3600) * 100


def _compress_track(points: list, max_points: int = 600) -> list:
    if len(points) <= max_points:
        return points
    step = len(points) // max_points
    result = points[::step]
    if result[-1] != points[-1]:
        result.append(points[-1])
    return result
