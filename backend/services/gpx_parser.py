"""GPX 文件解析服务"""
import gpxpy
import json
from datetime import datetime

from .coord_transform import wgs84_to_gcj02


def parse_gpx(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    if not gpx.tracks:
        raise ValueError("GPX 文件中未找到轨迹数据")

    track = gpx.tracks[0]

    # 提取所有轨迹点（WGS-84 → GCJ-02）
    points = []
    for segment in track.segments:
        for p in segment.points:
            if p.latitude is not None and p.longitude is not None:
                gcj_lat, gcj_lon = wgs84_to_gcj02(p.latitude, p.longitude)
                points.append({
                    "lat": round(gcj_lat, 6),
                    "lon": round(gcj_lon, 6),
                    "ele": round(p.elevation, 1) if p.elevation else None,
                    "time": p.time.isoformat() if p.time else None,
                })

    if not points:
        raise ValueError("GPX 文件中未找到有效坐标点")

    # 使用 gpxpy 计算统计数据
    moving_data = gpx.get_moving_data()
    uphill, downhill = gpx.get_uphill_downhill()
    elevation_extremes = gpx.get_elevation_extremes()

    duration_sec = int(moving_data.moving_time) if moving_data.moving_time else 0
    distance_m = moving_data.moving_distance or 0

    avg_speed = round(distance_m / duration_sec * 3.6, 2) if duration_sec > 0 else 0

    # 起止时间
    start_time = None
    end_time = None
    if points[0].get("time"):
        start_time = points[0]["time"]
    if points[-1].get("time"):
        end_time = points[-1]["time"]

    # 压缩轨迹点（最多 600 点用于地图渲染）
    compressed = _compress_track(points, max_points=600)

    return {
        "distance_km": round(distance_m / 1000, 2),
        "duration_sec": duration_sec,
        "elevation_gain": round(uphill, 1) if uphill else None,
        "elevation_loss": round(downhill, 1) if downhill else None,
        "max_elevation": round(elevation_extremes.maximum, 1) if elevation_extremes.maximum else None,
        "min_elevation": round(elevation_extremes.minimum, 1) if elevation_extremes.minimum else None,
        "avg_speed_kmh": avg_speed,
        "max_speed_kmh": None,
        "start_time": start_time,
        "end_time": end_time,
        "track_points": points,           # 完整点（供海拔图使用）
        "track_json": json.dumps(compressed, ensure_ascii=False),
    }


def _compress_track(points: list, max_points: int = 600) -> list:
    """轨迹点降采样，保留首尾"""
    if len(points) <= max_points:
        return points
    step = len(points) // max_points
    result = points[::step]
    if result[-1] != points[-1]:
        result.append(points[-1])
    return result
