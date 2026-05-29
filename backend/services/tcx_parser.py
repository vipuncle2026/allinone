"""TCX (Training Center XML) 文件解析器
支持 Garmin 设备导出的 .tcx 文件，解析徒步/跑步等运动数据。
"""

from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET

from .coord_transform import wgs84_to_gcj02

# 北京时区
_BJT = timezone(timedelta(hours=8))


# TCX 命名空间
NS = {
    "tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ns3": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
    "ns5": "http://www.garmin.com/xmlschemas/ActivityGoals/v1",
}


def parse_tcx(filepath: str) -> dict:
    """解析 TCX 文件，返回统一的运动数据字典

    返回字段与 gpx_parser / fit_parser 保持一致：
    - start_time, distance_km, duration_sec
    - avg_speed_kmh, max_speed_kmh
    - elevation_gain, elevation_loss, max_elevation, min_elevation
    - avg_heart_rate, max_heart_rate
    - calories, avg_cadence, max_cadence
    - track_points (精简轨迹)
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    # 查找第一个 Activity
    activity = root.find(".//tcx:Activity", NS)
    if activity is None:
        raise ValueError("未找到 Activity 节点")

    result = {
        "start_time": None,
        "distance_km": 0,
        "duration_sec": 0,
        "avg_speed_kmh": 0,
        "max_speed_kmh": 0,
        "elevation_gain": 0,
        "elevation_loss": 0,
        "max_elevation": None,
        "min_elevation": None,
        "avg_heart_rate": None,
        "max_heart_rate": None,
        "calories": 0,
        "avg_cadence": None,
        "max_cadence": None,
        "steps": None,
        "track_points": [],
    }

    # ── 汇总 Lap 数据 ────────────────────────────────────────
    laps = activity.findall("tcx:Lap", NS)
    total_distance = 0.0
    total_time = 0.0
    total_calories = 0
    global_max_speed = 0.0
    all_avg_hr = []
    all_max_hr = []
    all_avg_cadence = []
    all_max_cadence = []
    track_points = []
    prev_alt = None
    elev_gain = 0.0
    elev_loss = 0.0
    elev_max = -float("inf")
    elev_min = float("inf")

    for lap in laps:
        # Lap 级汇总
        dist = _float(lap, "tcx:DistanceMeters")
        t = _float(lap, "tcx:TotalTimeSeconds")
        cal = _float(lap, "tcx:Calories")
        max_spd = _float(lap, "tcx:MaximumSpeed")

        total_distance += dist
        total_time += t
        total_calories += cal
        if max_spd > global_max_speed:
            global_max_speed = max_spd

        # 心率
        avg_hr = _int_in(lap, "tcx:AverageHeartRateBpm/tcx:Value")
        max_hr = _int_in(lap, "tcx:MaximumHeartRateBpm/tcx:Value")
        if avg_hr is not None:
            all_avg_hr.append(avg_hr)
        if max_hr is not None:
            all_max_hr.append(max_hr)

        # 踏频 (Lap Extensions)
        lap_ext = lap.find("tcx:Extensions", NS)
        if lap_ext is not None:
            lx = lap_ext.find("ns3:LX", NS)
            if lx is not None:
                avg_cad = _int_in(lx, "ns3:AvgRunCadence")
                max_cad = _int_in(lx, "ns3:MaxRunCadence")
                if avg_cad is not None and avg_cad > 0:
                    all_avg_cadence.append(avg_cad)
                if max_cad is not None and max_cad > 0:
                    all_max_cadence.append(max_cad)

        # Trackpoints (轨迹点)
        tracks = lap.findall("tcx:Track", NS)
        for track in tracks:
            for tp in track.findall("tcx:Trackpoint", NS):
                time_el = tp.find("tcx:Time", NS)
                lat_el = tp.find("tcx:Position/tcx:LatitudeDegrees", NS)
                lon_el = tp.find("tcx:Position/tcx:LongitudeDegrees", NS)
                alt_el = tp.find("tcx:AltitudeMeters", NS)
                dist_el = tp.find("tcx:DistanceMeters", NS)
                hr_el = tp.find("tcx:HeartRateBpm/tcx:Value", NS)

                if time_el is None or time_el.text is None:
                    continue

                pt = {"time": time_el.text}

                if lat_el is not None and lon_el is not None:
                    wgs_lat, wgs_lon = float(lat_el.text), float(lon_el.text)
                    gcj_lat, gcj_lon = wgs84_to_gcj02(wgs_lat, wgs_lon)
                    pt["lat"] = gcj_lat
                    pt["lon"] = gcj_lon

                if alt_el is not None and alt_el.text:
                    alt = float(alt_el.text)
                    pt["alt"] = round(alt, 1)

                    # 海拔统计
                    if prev_alt is not None:
                        diff = alt - prev_alt
                        if diff > 0:
                            elev_gain += diff
                        else:
                            elev_loss += abs(diff)
                    prev_alt = alt
                    if alt > elev_max:
                        elev_max = alt
                    if alt < elev_min:
                        elev_min = alt

                if dist_el is not None and dist_el.text:
                    pt["distance"] = round(float(dist_el.text), 1)

                if hr_el is not None and hr_el.text:
                    pt["heart_rate"] = int(hr_el.text)

                # 速度（来自 Trackpoint Extension ns3:Speed，单位 m/s → km/h）
                spd_el = tp.find("tcx:Extensions/ns3:TPX/ns3:Speed", NS)
                if spd_el is not None and spd_el.text:
                    try:
                        pt["speed"] = round(float(spd_el.text) * 3.6, 2)
                    except ValueError:
                        pass

                track_points.append(pt)

    # ── 组装结果 ──────────────────────────────────────────────
    # 活动时间：取第一个/最后一个 trackpoint 的时间（UTC → 北京时间）
    if track_points:
        result["start_time"] = _utc_to_local(track_points[0].get("time"))
        result["end_time"] = _utc_to_local(track_points[-1].get("time"))

    result["distance_km"] = round(total_distance / 1000, 2)
    result["duration_sec"] = int(total_time)
    result["calories"] = total_calories
    result["max_speed_kmh"] = round(global_max_speed * 3.6, 2)

    if total_time > 0:
        result["avg_speed_kmh"] = round((total_distance / total_time) * 3.6, 2)

    result["elevation_gain"] = round(elev_gain, 1)
    result["elevation_loss"] = round(elev_loss, 1)
    result["max_elevation"] = round(elev_max, 1) if elev_max > -float("inf") else None
    result["min_elevation"] = round(elev_min, 1) if elev_min < float("inf") else None

    # 心率（取所有 Lap 平均）
    if all_avg_hr:
        result["avg_heart_rate"] = round(sum(all_avg_hr) / len(all_avg_hr))
    if all_max_hr:
        result["max_heart_rate"] = max(all_max_hr)

    # 踏频（TCX 中 RunCadence 是 rpm 转/分钟，步频需 ×2：左右脚各一步 = 1 转）
    if all_avg_cadence:
        result["avg_cadence"] = round(sum(all_avg_cadence) / len(all_avg_cadence)) * 2
    if all_max_cadence:
        result["max_cadence"] = max(all_max_cadence) * 2

    # 步数估算：根据平均步频和活动时长（步频 rpm = 步/分钟）
    # TCX 标准不含 Steps 字段，用 avg_cadence × duration_min 近似计算
    if result["avg_cadence"] and total_time > 0:
        result["steps"] = round(result["avg_cadence"] * (total_time / 60))

    # 精简轨迹（每 20 个点取 1 个，保留首尾）
    if len(track_points) > 200:
        step = max(1, len(track_points) // 200)
        simplified = track_points[::step]
        if simplified[-1] != track_points[-1]:
            simplified.append(track_points[-1])
        track_points = simplified

    # 图表序列精简（最多 500 点）
    chart_raw = track_points
    if len(chart_raw) > 500:
        step2 = max(1, len(chart_raw) // 500)
        chart_raw = chart_raw[::step2]

    # 轨迹点：含 lat/lon 的保留位置；所有点都保留 heart_rate/speed/distance/alt/time 用于图表
    # 分两组：地图轨迹（只要有坐标的）、图表序列（全部点）
    chart_points = [
        {k: v for k, v in pt.items() if k in ("time", "alt", "heart_rate", "speed", "distance")}
        for pt in chart_raw
    ]
    map_points = [
        {k: v for k, v in pt.items() if k in ("lat", "lon", "alt", "time")}
        for pt in track_points
        if "lat" in pt and "lon" in pt
    ]
    result["track_points"] = map_points
    result["chart_points"] = chart_points

    return result


# ── 辅助函数 ────────────────────────────────────────────────

def _utc_to_local(time_str: str | None) -> str | None:
    """将 UTC 时间字符串转为北京时间字符串（ISO 格式，无时区后缀）"""
    if not time_str:
        return None
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        local_dt = dt.astimezone(_BJT)
        return local_dt.strftime("%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        return time_str


def _float(parent, path: str) -> float:
    """在父元素下查找子元素，返回浮点数"""
    el = parent.find(path, NS)
    if el is not None and el.text:
        try:
            return float(el.text)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _int_in(parent, path: str) -> int | None:
    """在父元素下查找子元素，返回整数（可能为 None）"""
    el = parent.find(path, NS)
    if el is not None and el.text:
        try:
            v = int(el.text)
            return v if v > 0 else None
        except (ValueError, TypeError):
            pass
    return None
