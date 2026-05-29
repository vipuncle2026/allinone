"""账单解析服务：支持支付宝 CSV / 微信 CSV+XLSX 导入"""
import csv
import io
import json
import re
from typing import List, Tuple, Optional
from datetime import datetime

import openpyxl

from sqlalchemy.orm import Session
from models.finance import FinanceTransaction, FinanceCategoryRule, ALL_CATEGORIES


# ─── 平台识别 ───────────────────────────────────────────────

def detect_source(file_bytes: bytes, filename: str = "") -> str:
    """根据文件名和内容自动识别账单来源。
    返回: 'alipay' / 'wechat' / 'unknown'
    """
    name_lower = filename.lower()

    # 先根据文件名判断
    if "alipay" in name_lower or "支付宝" in filename:
        return "alipay"
    if "wechat" in name_lower or "微信" in filename:
        return "wechat"

    # xlsx 文件且非支付宝 → 微信
    if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        return "wechat"

    # 再根据内容判断
    # 支付宝：UTF-8 编码，列名包含"交易号"
    try:
        text = file_bytes.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        pass
    else:
        lines = text.split("\n", 5)
        for line in lines[:5]:
            if "交易号" in line and "交易时间" in line:
                return "alipay"
            if "交易号" in line:
                return "alipay"

    # 微信：GBK 编码，列名包含"交易时间"
    try:
        text = file_bytes.decode("gbk").strip()
    except (UnicodeDecodeError, LookupError):
        pass
    else:
        lines = text.split("\n", 5)
        for line in lines[:5]:
            if "微信支付账单" in line or "微信支付" in line:
                return "wechat"
            if "交易单号" in line and "商品" in line:
                return "wechat"
            # 支付宝也可能是 GBK 编码
            if "支付宝" in line or "交易订单号" in line:
                return "alipay"
            if "交易号" in line and ("金额" in line or "商品说明" in line):
                return "alipay"

    return "unknown"


# ─── 支付宝解析 ─────────────────────────────────────────────

# 支付宝 CSV 列名映射（可能存在别名，取第一个匹配的）
_ALIPAY_COLUMNS = {
    "trade_no": ["交易号", "交易编号", "交易订单号"],
    "trade_time": ["交易时间", "付款时间", "收款时间"],
    "description": ["商品说明", "商品名称", "商品"],
    "counterparty": ["交易对方", "对方"],
    "amount": ["金额（元）", "金额(元)", "金额"],
    "direction": ["收/支", "收/支"],
    "status": ["交易状态"],
    "pay_method": ["付款方式", "支付方式", "收/付款方式"],
    "category_merchant": ["交易分类", "商户类别"],
}

_ALIPAY_TRANSFER_KEYWORDS = [
    "余额宝", "余额", "转入", "转出", "提现", "充值", "还款",
    "信用卡", "花呗", "借呗", "转账", "红包", "退款", "理财",
]

_ALIPAY_INCOME_KEYWORDS = ["收入", "收款", "奖金", "红包", "退款"]


def _find_column_index(headers: List[str], aliases: List[str]) -> int:
    """在表头列表中查找匹配的列索引"""
    for h in headers:
        h_stripped = h.strip().strip('"')
        for alias in aliases:
            if alias in h_stripped:
                return headers.index(h)
    return -1


def parse_alipay(file_bytes: bytes) -> List[dict]:
    """解析支付宝 CSV 账单，返回标准化记录列表"""
    # 支付宝导出可能是 GBK 或 UTF-8 编码
    text = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            text = file_bytes.decode(encoding).strip()
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text is None:
        raise ValueError("无法解码支付宝账单文件，请确认编码正确")

    # 支付宝 CSV 可能有空行分隔的标题信息，找到真正的表头行
    lines = text.split("\n")
    header_idx = -1
    for i, line in enumerate(lines):
        if "交易号" in line or "交易时间" in line:
            header_idx = i
            break

    if header_idx < 0:
        raise ValueError("无法识别支付宝账单表头，请确认文件格式正确")

    headers = [h.strip().strip('"') for h in lines[header_idx].split(",")]
    data_lines = [l for l in lines[header_idx + 1:] if l.strip()]

    # 建立列索引映射
    col_map = {}
    for key, aliases in _ALIPAY_COLUMNS.items():
        idx = _find_column_index(headers, aliases)
        if idx >= 0:
            col_map[key] = idx

    records = []
    for line in data_lines:
        fields = _smart_split_csv(line)
        if len(fields) < 5:
            continue

        raw = {k: fields[v].strip().strip('"').strip("\t") if v < len(fields) else "" for k, v in col_map.items()}

        # 跳过标题行和空行
        if not raw.get("trade_no") and not raw.get("description"):
            continue

        record = _normalize_alipay_record(raw)
        if record:
            records.append(record)

    return records


def _smart_split_csv(line: str) -> List[str]:
    """CSV 字段分割，处理引号内的逗号"""
    result = []
    current = []
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ',' and not in_quotes:
            result.append("".join(current))
            current = []
        else:
            current.append(ch)
    result.append("".join(current))
    return result


def _normalize_alipay_record(raw: dict) -> Optional[dict]:
    """标准化支付宝单条记录"""
    amount_str = raw.get("amount", "").replace(",", "").replace('"', "").strip()
    direction = raw.get("direction", "").strip()
    status = raw.get("status", "").strip()

    # 跳过无效记录
    if not amount_str or not direction:
        return None
    # 跳过未成功交易
    if "等待付款" in status or "交易关闭" in status:
        return None

    try:
        amount = abs(float(amount_str))
    except ValueError:
        return None

    if amount == 0:
        return None

    # 判断收入/支出
    direction_lower = direction.lower()
    if direction_lower in ("收入", "收入（他人转账）", "收款"):
        txn_type = "income"
    elif direction_lower in ("支出",):
        txn_type = "expense"
    else:
        # "不计收支"等非收支类型直接跳过
        if "不计收支" in direction or "不计" in direction:
            return None
        txn_type = "expense" if amount_str.startswith("-") or "支出" in direction else "income"

    # 判断是否转账类
    desc = raw.get("description", "")
    counterparty = raw.get("counterparty", "")
    is_transfer = 0
    for kw in _ALIPAY_TRANSFER_KEYWORDS:
        if kw in desc or kw in counterparty:
            is_transfer = 1
            break

    # 解析时间
    trade_time = raw.get("trade_time", "").strip()
    date_str = _parse_datetime(trade_time)

    return {
        "source": "alipay",
        "trade_no": raw.get("trade_no", "").strip(),
        "date": date_str,
        "time": trade_time,
        "type": txn_type,
        "description": desc,
        "counterparty": counterparty,
        "amount": round(amount, 2),
        "pay_method": raw.get("pay_method", "").strip(),
        "is_transfer": is_transfer,
        "category": "",  # 待自动分类
        "raw": json.dumps(raw, ensure_ascii=False),
    }


# ─── 微信解析 ───────────────────────────────────────────────

_WECHAT_COLUMNS = {
    "trade_time": ["交易时间"],
    "trade_type": ["交易类型"],
    "counterparty": ["交易对方"],
    "description": ["商品"],
    "direction": ["收/支"],
    "amount": ["金额(元)", "金额（元）", "金额"],
    "pay_method": ["支付方式"],
    "status": ["当前状态"],
    "trade_no": ["交易单号"],
    "merchant_no": ["商户单号"],
    "remark": ["备注"],
}

_WECHAT_TRANSFER_KEYWORDS = [
    "转账", "红包", "提现", "充值", "零钱通", "理财通",
    "信用卡", "还款", "退款", "群收款",
]


def _parse_wechat_xlsx(file_bytes: bytes) -> List[dict]:
    """解析微信支付 XLSX 账单"""
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        raise ValueError("微信 XLSX 账单为空文件")

    # 找到表头行
    header_idx = -1
    for i, row in enumerate(rows):
        if row and "交易时间" in str(row[0] if row else ""):
            header_idx = i
            break
        # 也检查整行
        row_str = " ".join(str(c) for c in row if c)
        if "交易时间" in row_str and ("交易单号" in row_str or "商品" in row_str):
            header_idx = i
            break

    if header_idx < 0:
        raise ValueError("无法识别微信 XLSX 账单表头，请确认文件格式正确")

    headers = [str(c).strip() if c else "" for c in rows[header_idx]]

    # 建立列索引映射
    col_map = {}
    for key, aliases in _WECHAT_COLUMNS.items():
        idx = _find_column_index(headers, aliases)
        if idx >= 0:
            col_map[key] = idx

    records = []
    for row in rows[header_idx + 1:]:
        if not row or not any(row):
            continue

        # 处理每列值
        row_values = []
        for cell in row:
            if cell is None:
                row_values.append("")
            elif isinstance(cell, datetime):
                row_values.append(cell.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                row_values.append(str(cell).strip())

        if len(row_values) < 5:
            continue

        raw = {k: row_values[v] if v < len(row_values) else "" for k, v in col_map.items()}

        if not raw.get("trade_no") and not raw.get("description"):
            continue

        record = _normalize_wechat_record(raw)
        if record:
            records.append(record)

    return records


def parse_wechat(file_bytes: bytes, filename: str = "") -> List[dict]:
    """解析微信支付账单，支持 CSV 和 XLSX 格式"""
    name_lower = filename.lower()
    if name_lower.endswith(".xlsx"):
        return _parse_wechat_xlsx(file_bytes)
    return _parse_wechat_csv(file_bytes)


def _parse_wechat_csv(file_bytes: bytes) -> List[dict]:
    """解析微信支付 CSV 账单"""
    # 微信账单用 GBK 编码，但部分新版也用 UTF-8
    text = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            text = file_bytes.decode(encoding).strip()
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        raise ValueError("无法解码微信账单文件，请确认编码正确")

    lines = text.split("\n")

    # 微信账单可能有多行标题注释，找到表头行
    header_idx = -1
    for i, line in enumerate(lines):
        if "交易时间" in line and "交易单号" in line:
            header_idx = i
            break
        # 也可能是制表符分隔
        if "交易时间\t" in line or "交易时间," in line:
            header_idx = i
            break

    if header_idx < 0:
        raise ValueError("无法识别微信账单表头，请确认文件格式正确")

    header_line = lines[header_idx]
    # 判断分隔符
    delimiter = "\t" if "\t" in header_line else ","

    headers = [h.strip().strip('"') for h in header_line.split(delimiter)]
    data_lines = [l for l in lines[header_idx + 1:] if l.strip()]

    # 建立列索引映射
    col_map = {}
    for key, aliases in _WECHAT_COLUMNS.items():
        idx = _find_column_index(headers, aliases)
        if idx >= 0:
            col_map[key] = idx

    records = []
    for line in data_lines:
        fields = [f.strip().strip('"') for f in line.split(delimiter)]
        if len(fields) < 5:
            continue

        raw = {k: fields[v].strip().strip('"').strip("\t") if v < len(fields) else "" for k, v in col_map.items()}

        if not raw.get("trade_no") and not raw.get("description"):
            continue

        record = _normalize_wechat_record(raw)
        if record:
            records.append(record)

    return records


def _normalize_wechat_record(raw: dict) -> Optional[dict]:
    """标准化微信单条记录"""
    amount_str = raw.get("amount", "").replace(",", "").replace('"', "").strip()
    direction = raw.get("direction", "").strip()
    status = raw.get("status", "").strip()

    if not amount_str or not direction:
        return None
    # 跳过未成功交易
    if "未支付" in status or "已关闭" in status:
        return None

    try:
        amount = abs(float(amount_str))
    except ValueError:
        return None

    if amount == 0:
        return None

    # 判断收入/支出
    if "收入" in direction:
        txn_type = "income"
    elif "支出" in direction:
        txn_type = "expense"
    else:
        # 非收支类型直接跳过
        return None

    # 判断是否转账类
    desc = raw.get("description", "")
    counterparty = raw.get("counterparty", "")
    trade_type = raw.get("trade_type", "")
    is_transfer = 0
    for kw in _WECHAT_TRANSFER_KEYWORDS:
        if kw in desc or kw in counterparty or kw in trade_type:
            is_transfer = 1
            break

    # 解析时间
    trade_time = raw.get("trade_time", "").strip()
    date_str = _parse_datetime(trade_time)

    return {
        "source": "wechat",
        "trade_no": raw.get("trade_no", "").strip(),
        "date": date_str,
        "time": trade_time,
        "type": txn_type,
        "description": desc,
        "counterparty": counterparty,
        "amount": round(amount, 2),
        "pay_method": raw.get("pay_method", "").strip(),
        "is_transfer": is_transfer,
        "category": "",  # 待自动分类
        "raw": json.dumps(raw, ensure_ascii=False),
    }


# ─── 时间解析 ───────────────────────────────────────────────

def _parse_datetime(time_str: str) -> str:
    """解析各种时间格式，返回 YYYY-MM-DD"""
    if not time_str:
        return ""
    time_str = time_str.strip()

    # 常见格式: 2024-01-15 12:30:45 / 2024-01-15 12:30:45 +0800
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S %z",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(time_str[:25], fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # 兜底：取前10位
    return time_str[:10] if len(time_str) >= 10 else time_str


# ─── 去重 ──────────────────────────────────────────────────

def deduplicate(records: List[dict], db: Session) -> Tuple[List[dict], List[dict]]:
    """
    去重判断：platform + trade_no + amount + date
    返回 (new_records, duplicate_records)
    """
    if not records:
        return [], []

    # 批量查询已有记录的去重键
    platforms = set(r["source"] for r in records)
    dates = set(r["date"] for r in records)

    existing = set()
    for platform in platforms:
        for date in dates:
            rows = db.query(FinanceTransaction.trade_no, FinanceTransaction.amount, FinanceTransaction.date) \
                .filter(
                    FinanceTransaction.source == platform,
                    FinanceTransaction.date == date,
                    FinanceTransaction.trade_no != "",
                ).all()
            for row in rows:
                key = (platform, row.trade_no, row.amount, row.date)
                existing.add(key)

    new_records = []
    duplicate_records = []
    for r in records:
        dedup_key = (r["source"], r.get("trade_no", ""), r["amount"], r["date"])
        if r.get("trade_no") and dedup_key in existing:
            r["_is_duplicate"] = True
            duplicate_records.append(r)
        else:
            r["_is_duplicate"] = False
            new_records.append(r)

    return new_records, duplicate_records


# ─── 自动分类 ───────────────────────────────────────────────

def auto_classify(records: List[dict], db: Session) -> List[dict]:
    """根据分类规则自动分类"""
    rules = db.query(FinanceCategoryRule) \
        .filter(FinanceCategoryRule.is_enabled == 1) \
        .order_by(FinanceCategoryRule.priority, FinanceCategoryRule.id) \
        .all()

    if not rules:
        for r in records:
            if not r.get("category"):
                r["category"] = "其他支出" if r.get("type") == "expense" else "其他收入"
        return records

    for r in records:
        if r.get("category"):
            continue  # 已有分类不覆盖

        matched = False
        for rule in rules:
            # 检查收支类型和平台是否匹配
            if rule.txn_type != "all" and rule.txn_type != r.get("type"):
                continue
            if rule.platform != "all" and rule.platform != r.get("source"):
                continue

            # 获取匹配值
            match_text = r.get(rule.match_field, "")
            pattern = rule.match_value

            if rule.match_type == "contains":
                patterns = [p.strip() for p in pattern.split("\n") if p.strip()]
                if any(p in match_text for p in patterns):
                    r["category"] = rule.category
                    matched = True
                    break
            elif rule.match_type == "equals":
                patterns = [p.strip() for p in pattern.split("\n") if p.strip()]
                if match_text.strip() in patterns:
                    r["category"] = rule.category
                    matched = True
                    break
            elif rule.match_type == "regex":
                try:
                    if re.search(pattern, match_text):
                        r["category"] = rule.category
                        matched = True
                        break
                except re.error:
                    continue

        if not matched:
            r["category"] = "其他支出" if r.get("type") == "expense" else "其他收入"

    return records


# ─── 统一解析入口 ───────────────────────────────────────────

def parse_bill(file_bytes: bytes, filename: str) -> Tuple[str, List[dict]]:
    """统一解析入口。返回 (source, records)"""
    source = detect_source(file_bytes, filename)
    if source == "alipay":
        records = parse_alipay(file_bytes)
    elif source == "wechat":
        records = parse_wechat(file_bytes, filename)
    else:
        # 先尝试按 csv 解析支付宝
        try:
            records = parse_alipay(file_bytes)
            if records:
                source = "alipay"
            else:
                # 尝试微信（可能是 xlsx）
                records = parse_wechat(file_bytes, filename)
                if records:
                    source = "wechat"
        except Exception:
            records = []

    return source, records
