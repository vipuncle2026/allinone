"""基金业务逻辑层 — 从 routers/fund.py 拆出"""
import asyncio
import httpx
import json
import re
from datetime import datetime, date as date_type
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.fund import FundFavorite, FundGroup, FundLibrary, FundSnapshot, FundSnapshotItem


# ============================================================
# 第三方 API 代理
# ============================================================

async def fetch_fund_valuation(code: str) -> dict:
    """场外基金估值 - 天天基金网

    正常基金返回实时估算；QDII/新基金等无估算的，fallback 到 pingzhongdata
    提取最新公布净值，避免显示"暂无估算"。
    """
    url = f"https://fundgz.1234567.com.cn/js/{code}.js?rt={int(datetime.now().timestamp()*1000)}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        text = resp.text.strip()

    # 解析 JSONP: jsonpgz({...})
    match = re.search(r'jsonpgz\((.+)\);?\s*$', text)
    if match:
        json_str = match.group(1)
        if json_str.strip() and json_str.strip() != "()":
            try:
                data = json.loads(json_str)
                if data and data.get("name"):
                    return {
                        "code": data.get("fundcode", code),
                        "name": data.get("name", ""),
                        "nav": float(data.get("dwjz", 0)),
                        "est_nav": float(data.get("gsz", 0)),
                        "day_chg": float(data.get("gszzl", 0)),
                        "val_time": data.get("gztime", ""),
                        "nav_date": data.get("jzrq", ""),
                        "type": data.get("fundtype", "混合型"),
                        "no_estimate": False,
                    }
            except json.JSONDecodeError:
                pass

    # fallback: fundgz 无估算数据 → 从 pingzhongdata 提取最新净值
    return await _fetch_fund_nav_from_pingzhongdata(code)


async def _fetch_fund_nav_from_pingzhongdata(code: str) -> dict:
    """从 pingzhongdata 提取最新净值（QDII/新基金等无 fundgz 估值时 fallback）"""
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        text = resp.text

    # 提取名称
    name = ""
    m_name = re.search(r'fS_name\s*=\s*"(.+?)"', text)
    if m_name:
        name = m_name.group(1)

    # 提取历史净值趋势 Data_netWorthTrend = [{"x": 毫秒, "y": nav}, ...]
    m = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', text, re.DOTALL)
    if not m:
        return {"no_estimate": True}

    try:
        trend = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {"no_estimate": True}

    if not trend:
        return {"no_estimate": True}

    latest = trend[-1]
    ts = latest.get("x", 0) / 1000
    nav = float(latest.get("y", 0))

    if nav <= 0:
        return {"no_estimate": True}

    # 计算日涨跌幅（用前一日净值）
    day_chg = 0.0
    if len(trend) >= 2:
        prev = trend[-2]
        prev_nav = float(prev.get("y", 0))
        if prev_nav > 0:
            day_chg = (nav - prev_nav) / prev_nav * 100

    date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
    val_time = f"{date_str} 19:00:00" if date_str else ""

    # 尝试提取基金类型
    fund_type = "混合型"
    m_type = re.search(r'Data_fundType\s*=\s*"(.+?)"', text)
    if m_type:
        fund_type = m_type.group(1)

    return {
        "code": code,
        "name": name,
        "nav": nav,
        "est_nav": nav,
        "day_chg": round(day_chg, 2),
        "val_time": val_time,
        "nav_date": date_str,
        "type": fund_type,
        "no_estimate": False,
    }


async def fetch_fund_basic_info(code: str) -> dict:
    """获取基金基本信息（名称等）- 天天基金 pingzhongdata 接口"""
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        text = resp.text

    m = re.search(r'fS_name\s*=\s*"(.+?)"', text)
    if not m:
        return {}

    info = {"name": m.group(1)}

    # 尝试提取基金经理
    m2 = re.search(r'fS_manager\s*=\s*"(.+?)"', text)
    if m2:
        info["manager"] = m2.group(1)

    return info


async def fetch_etf_price(code: str) -> dict:
    """场内 ETF 实时行情 - 东方财富"""
    prefix = "1" if code.startswith("5") else "0"
    url = (
        f"https://push2.eastmoney.com/api/qt/ulist.np/get"
        f"?fltt=2&invt=2&secids={prefix}.{code}"
        f"&fields=f12,f14,f2,f3,f4&_={int(datetime.now().timestamp()*1000)}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        data = resp.json()

    items = data.get("data", {}).get("diff", [])
    if not items:
        raise HTTPException(status_code=404, detail="未找到ETF数据")

    d = items[0]
    price = float(d.get("f2", 0))
    chg_amount = float(d.get("f4", 0))
    yclose = price - chg_amount
    day_chg = float(d.get("f3", 0))
    if day_chg == 0 and yclose > 0:
        day_chg = (price - yclose) / yclose * 100

    now = datetime.now()
    val_time = now.strftime("%Y-%m-%d %H:%M:%S")

    return {
        "code": d.get("f12", code),
        "name": d.get("f14", ""),
        "nav": price,
        "est_nav": price,
        "day_chg": day_chg,
        "val_time": val_time,
        "nav_date": "",
        "type": "ETF",
        "no_estimate": False,
    }


# ============================================================
# 搜索 / 添加辅助
# ============================================================

async def search_fund_data(code: str, db: Session) -> dict:
    """查询基金信息（不添加），返回预览数据"""
    code = code.strip().zfill(6)
    if len(code) != 6 or not code.isdigit():
        raise HTTPException(400, "请输入6位数字基金代码")

    existing = db.query(FundFavorite).filter(FundFavorite.code == code).first()
    if existing:
        raise HTTPException(400, f"该基金已在自选中：{existing.name}")

    result = {"code": code, "name": "", "nav": 0, "est_nav": 0, "day_chg": 0, "type": "", "no_estimate": False}

    lib = db.query(FundLibrary).filter(FundLibrary.code == code).first()
    if lib:
        result["name"] = lib.name
        result["type"] = lib.type or ""
        result["is_etf"] = lib.is_etf

    try:
        data = await fetch_fund_valuation(code)
        if not data.get("no_estimate"):
            result["name"] = data.get("name") or result["name"]
            result["nav"] = data.get("nav", 0)
            result["est_nav"] = data.get("est_nav", 0)
            result["day_chg"] = data.get("day_chg", 0)
            result["type"] = data.get("type") or result["type"]
        else:
            result["no_estimate"] = True
    except Exception:
        result["no_estimate"] = True
        try:
            etf_data = await fetch_etf_price(code)
            result["nav"] = etf_data.get("nav", 0)
            result["est_nav"] = etf_data.get("est_nav", 0)
            result["day_chg"] = etf_data.get("day_chg", 0)
            if etf_data.get("name"):
                result["name"] = etf_data["name"]
            result["type"] = etf_data.get("type") or result["type"]
            result["no_estimate"] = False
        except Exception:
            pass

    if not result["name"]:
        try:
            info = await fetch_fund_basic_info(code)
            if info.get("name"):
                result["name"] = info["name"]
        except Exception:
            pass

    if not result["name"]:
        raise HTTPException(404, f"未找到基金代码 {code}，请确认后重试")

    return result


async def build_new_fund(code: str, group_id: str, shares: float, cost_nav: float, db: Session) -> FundFavorite:
    """构建新 FundFavorite 对象（含 API 数据填充），但不 commit"""
    code = code.strip().zfill(6)
    if len(code) != 6 or not code.isdigit():
        raise HTTPException(400, "请输入6位数字基金代码")

    existing = db.query(FundFavorite).filter(FundFavorite.code == code).first()
    if existing:
        raise HTTPException(400, "该基金已在自选中")

    lib = db.query(FundLibrary).filter(FundLibrary.code == code).first()
    group_id = group_id if group_id != "all" else "default"

    fund = FundFavorite(
        code=code,
        name=lib.name if lib else f"基金{code}",
        type=lib.type if lib else "混合型",
        is_etf=lib.is_etf if lib else False,
        group_id=group_id,
        manager=lib.manager if lib else "--",
        company=lib.company if lib else "--",
        scale=lib.scale if lib else 0,
        shares=shares or 0,
        cost_nav=cost_nav or 0,
    )

    try:
        data = await fetch_fund_valuation(code)
        if not data.get("no_estimate"):
            fund.name = data.get("name") or fund.name
            fund.nav = data.get("nav", 0)
            fund.est_nav = data.get("est_nav", 0)
            fund.day_chg = data.get("day_chg", 0)
            fund.val_time = data.get("val_time", "")
            fund.nav_date = data.get("nav_date", "")
            fund.type = data.get("type") or fund.type
        else:
            fund.no_estimate = True
    except Exception:
        fund.no_estimate = True
        if fund.is_etf or code[0] in ("5", "1", "4", "9", "2", "0"):
            try:
                etf_data = await fetch_etf_price(code)
                fund.nav = etf_data["nav"]
                fund.est_nav = etf_data["est_nav"]
                fund.day_chg = etf_data["day_chg"]
                fund.val_time = etf_data["val_time"]
                if etf_data.get("name"):
                    fund.name = etf_data["name"]
            except Exception:
                pass

    if not lib and fund.name == f"基金{code}":
        try:
            info = await fetch_fund_basic_info(code)
            if info.get("name"):
                fund.name = info["name"]
            if info.get("manager"):
                fund.manager = info["manager"]
        except Exception:
            pass

    return fund


# ============================================================
# 刷新估值
# ============================================================

async def refresh_all_navs(db: Session) -> dict:
    """核心刷新逻辑（并发请求，最多 5 个并行）"""
    funds = db.query(FundFavorite).all()
    if not funds:
        return {"ok": True, "message": "请先添加自选基金", "results": []}

    sem = asyncio.Semaphore(5)

    async def _fetch_one(fund) -> dict:
        async with sem:
            try:
                if fund.is_etf:
                    data = await fetch_etf_price(fund.code)
                else:
                    data = await fetch_fund_valuation(fund.code)

                if data.get("no_estimate"):
                    if fund.name.startswith("基金"):
                        try:
                            info = await fetch_fund_basic_info(fund.code)
                            data["_info"] = info
                        except Exception:
                            pass
                return {"code": fund.code, "ok": True, "data": data}
            except Exception as e:
                return {"code": fund.code, "ok": False, "error": str(e)}

    raw_results = await asyncio.gather(*[_fetch_one(f) for f in funds])

    fund_map = {f.code: f for f in funds}
    success = 0
    failed = 0
    results = []

    for res in raw_results:
        code = res["code"]
        fund = fund_map.get(code)
        if not fund:
            continue
        if not res["ok"]:
            failed += 1
            results.append({"code": code, "ok": False, "error": res["error"]})
            continue

        data = res["data"]
        if data.get("no_estimate"):
            fund.no_estimate = True
            info = data.get("_info", {})
            if info.get("name"):
                fund.name = info["name"]
            if info.get("manager") and fund.manager == "--":
                fund.manager = info["manager"]
        else:
            if fund.is_etf:
                if fund.nav > 0:
                    fund.prev_nav = fund.nav
                fund.nav = data.get("nav", fund.nav)
                fund.est_nav = data.get("est_nav", fund.est_nav)
                fund.day_chg = data.get("day_chg", fund.day_chg)
                fund.val_time = data.get("val_time", fund.val_time)
                if data.get("name"):
                    fund.name = data["name"]
                fund.no_estimate = False
            else:
                if fund.nav > 0:
                    fund.prev_nav = fund.nav
                fund.nav = data.get("nav", fund.nav)
                fund.est_nav = data.get("est_nav", fund.est_nav)
                fund.day_chg = data.get("day_chg", fund.day_chg)
                fund.val_time = data.get("val_time", fund.val_time)
                fund.nav_date = data.get("nav_date", fund.nav_date)
                if data.get("name") and not fund.name.startswith("基金"):
                    fund.name = data.get("name")
                if data.get("type"):
                    fund.type = data.get("type")
                fund.no_estimate = False
        fund.updated_at = datetime.now()
        success += 1
        results.append({"code": code, "ok": True})

    db.commit()
    msg = "估值已更新" if failed == 0 else f"{failed}/{len(funds)} 只基金获取失败"
    return {"ok": True, "message": msg, "success": success, "failed": failed, "results": results}


# ============================================================
# 持仓分析
# ============================================================

def calc_holding_summary(db: Session) -> dict:
    """计算持仓汇总"""
    funds = db.query(FundFavorite).filter(FundFavorite.shares > 0).all()
    if not funds:
        return {
            "total_market": 0, "total_cost": 0, "total_gain": 0,
            "total_rate": 0, "today_profit": 0, "holdings": []
        }

    total_market = 0
    total_cost = 0
    total_today_profit = 0
    total_yesterday_profit = 0
    holdings = []
    missing_cost_count = 0

    for f in funds:
        cur_nav = f.est_nav or f.nav or f.cost_nav
        market = f.shares * cur_nav
        has_cost = f.cost_nav and f.cost_nav > 0
        cost = f.shares * f.cost_nav if has_cost else 0
        gain = market - cost if has_cost else 0
        rate = (gain / cost * 100) if has_cost and cost > 0 else 0
        today_gain = market * (f.day_chg or 0) / 100
        yesterday_gain = 0
        if f.prev_nav and f.prev_nav > 0 and f.nav and f.nav > 0:
            yesterday_gain = f.shares * (f.nav - f.prev_nav)
        total_market += market
        total_cost += cost
        total_today_profit += today_gain
        total_yesterday_profit += yesterday_gain
        if not has_cost:
            missing_cost_count += 1
        holdings.append({
            **fund_to_dict(f),
            "market_value": round(market, 2),
            "cost_value": round(cost, 2),
            "gain": round(gain, 2),
            "rate": round(rate, 2),
            "today_gain": round(today_gain, 2),
            "cur_nav": round(cur_nav, 4),
            "has_cost": has_cost,
        })

    total_gain = total_market - total_cost
    total_rate = (total_gain / total_cost * 100) if total_cost > 0 else 0

    return {
        "total_market": round(total_market, 2),
        "total_cost": round(total_cost, 2),
        "total_gain": round(total_gain, 2),
        "total_rate": round(total_rate, 2),
        "today_profit": round(total_today_profit, 2),
        "yesterday_profit": round(total_yesterday_profit, 2),
        "holdings": holdings,
        "missing_cost_count": missing_cost_count,
    }


# ============================================================
# 基金详情
# ============================================================

async def fetch_fund_detail_data(code: str, db: Session) -> dict:
    """获取基金详情（持仓Top10 + 近30天净值 + 基本信息）"""
    import html as html_mod

    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            text = resp.text
    except Exception:
        raise HTTPException(502, "获取基金数据失败，请稍后重试")

    # ── 1. 近30天历史净值 ──
    nav_list = []
    trend_match = re.search(r'Data_netWorthTrend\s*=\s*(\[.*?\]);', text, re.DOTALL)
    if trend_match:
        try:
            raw = json.loads(trend_match.group(1))
            for item in raw[-30:]:
                ts = item.get("x", 0) / 1000
                nav = round(float(item.get("y", 0)), 4)
                if ts and nav > 0:
                    date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    nav_list.append({"date": date_str, "nav": nav})
        except (json.JSONDecodeError, IndexError, OSError):
            pass

    # ── 2. 持仓明细（Top 10 重仓股） ──
    holdings = []
    try:
        cc_url = "http://fundf10.eastmoney.com/FundArchivesDatas.aspx"
        cc_params = {"type": "jjcc", "code": code, "topline": "10", "year": "", "month": "", "rt": "0.123"}
        cc_headers = {"Referer": f"http://fundf10.eastmoney.com/ccmx_{code}.html"}
        async with httpx.AsyncClient(timeout=15) as client:
            cc_resp = await client.get(cc_url, params=cc_params, headers=cc_headers)
            cc_text = cc_resp.text

        content_match = re.search(r'content\s*:\s*"(.+?)"', cc_text, re.DOTALL)
        if content_match:
            html_str = content_match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
            rows = re.findall(r'<tr>(.*?)</tr>', html_str, re.DOTALL)
            for row in rows:
                if '<th' in row:
                    continue
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 9:
                    def strip_tags(s):
                        return re.sub(r'<[^>]+>', '', s).strip()
                    stock_code = strip_tags(cells[1])
                    stock_name = strip_tags(cells[2])
                    ratio_str = strip_tags(cells[6]).replace('%', '')
                    amount_str = strip_tags(cells[8]).replace(',', '')
                    try:
                        ratio = float(ratio_str)
                        amount = float(amount_str) if amount_str else 0
                        holdings.append({
                            "stock_code": stock_code,
                            "stock_name": stock_name,
                            "ratio": ratio,
                            "amount": round(amount, 2),
                        })
                    except (ValueError, IndexError):
                        continue
    except Exception:
        pass

    # ── 3. 基金基本信息（从 F10 页面获取） ──
    basic_info = {"manager": "--", "company": "--", "scale": 0, "type": "--"}
    try:
        jbgk_url = f"http://fundf10.eastmoney.com/jbgk_{code}.html"
        jbgk_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"http://fundf10.eastmoney.com/jbgk_{code}.html",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            jbgk_resp = await client.get(jbgk_url, headers=jbgk_headers)
            jbgk_text = jbgk_resp.text

        m_company = re.search(r'基金管理人</th><td><a[^>]*>([^<]+)', jbgk_text)
        if m_company:
            basic_info["company"] = m_company.group(1).strip()

        m_manager = re.search(r'基金经理人</th><td>(.*?)</td>', jbgk_text, re.DOTALL)
        if m_manager:
            names = re.findall(r'<a[^>]*>([^<]+)</a>', m_manager.group(1))
            if names:
                basic_info["manager"] = "、".join(n.strip() for n in names)

        m_scale = re.search(r'(\d+\.?\d*)\s*亿', jbgk_text)
        if m_scale:
            basic_info["scale"] = round(float(m_scale.group(1)), 2)

        m_type = re.search(r'基金类型</th><td[^>]*>([^<]+)', jbgk_text)
        if m_type:
            basic_info["type"] = m_type.group(1).strip()

    except Exception:
        pass

    # ── 4. 历史收益率 ──
    ret_fields = {}
    for var_name, field_name in [("syl_1y", "ret_1m"), ("syl_3y", "ret_3m"), ("syl_6y", "ret_6m"), ("syl_1n", "ret_1y")]:
        m = re.search(rf'{var_name}\s*=\s*"([-\d.]+)"', text)
        if m:
            try:
                ret_fields[field_name] = round(float(m.group(1)), 2)
            except ValueError:
                pass

    # ── 5. 基金经理（补充） ──
    if basic_info["manager"] == "--":
        m_mgr = re.search(r'Data_currentFundManager\s*=\s*(\[.*?\])\s*;', text, re.DOTALL)
        if m_mgr:
            try:
                mgr_list = json.loads(m_mgr.group(1))
                mgr_names = [item.get("name", "") for item in mgr_list if item.get("name")]
                if mgr_names:
                    basic_info["manager"] = "、".join(mgr_names)
            except (json.JSONDecodeError, IndexError):
                pass

    # ── 6. 写回数据库 ──
    fund = db.query(FundFavorite).filter(FundFavorite.code == code).first()
    name = re.search(r'fS_name\s*=\s*"(.+?)"', text).group(1) if re.search(r'fS_name\s*=\s*"(.+?)"', text) else (fund.name if fund else "")

    if fund:
        need_update = False
        if fund.manager in (None, "", "--") and basic_info["manager"] != "--":
            fund.manager = basic_info["manager"]
            need_update = True
        if fund.company in (None, "", "--") and basic_info["company"] != "--":
            fund.company = basic_info["company"]
            need_update = True
        if (fund.scale or 0) == 0 and basic_info["scale"] > 0:
            fund.scale = basic_info["scale"]
            need_update = True
        if fund.type in (None, "", "混合型") and basic_info["type"] != "--":
            fund.type = basic_info["type"]
            need_update = True
        if fund.name and fund.name.startswith("基金") and name and not name.startswith("基金"):
            fund.name = name
            need_update = True
        for field_name, value in ret_fields.items():
            if hasattr(fund, field_name) and (getattr(fund, field_name) or 0) == 0 and value != 0:
                setattr(fund, field_name, value)
                need_update = True
        if need_update:
            db.commit()

    return {
        "code": code,
        "name": name,
        "holdings": holdings,
        "nav_history": nav_list,
        "basic_info": basic_info,
        "ret_fields": ret_fields,
    }


# ============================================================
# 持仓快照
# ============================================================

async def do_take_snapshot(db: Session) -> dict:
    """核心快照逻辑：计算当前持仓状态并写入快照表（UPSERT）"""
    today_str = date_type.today().isoformat()

    funds = db.query(FundFavorite).filter(FundFavorite.shares > 0).all()
    if not funds:
        return {"ok": False, "message": "暂无持仓数据"}

    total_market = 0.0
    total_cost = 0.0
    total_today_profit = 0.0
    items_data = []

    for f in funds:
        cur_nav = f.est_nav or f.nav or f.cost_nav or 0
        market = f.shares * cur_nav
        has_cost = f.cost_nav and f.cost_nav > 0
        cost = f.shares * f.cost_nav if has_cost else 0
        today_gain = market * (f.day_chg or 0) / 100
        total_market += market
        total_cost += cost
        total_today_profit += today_gain
        items_data.append({
            "code": f.code,
            "name": f.name,
            "nav": round(cur_nav, 4),
            "shares": f.shares,
            "market_value": round(market, 2),
            "day_chg": f.day_chg or 0,
            "today_gain": round(today_gain, 2),
        })

    total_gain = total_market - total_cost
    total_rate = (total_gain / total_cost * 100) if total_cost > 0 else 0

    # UPSERT 汇总快照
    existing = db.query(FundSnapshot).filter(FundSnapshot.snapshot_date == today_str).first()
    if existing:
        existing.total_market = round(total_market, 2)
        existing.total_cost = round(total_cost, 2)
        existing.total_gain = round(total_gain, 2)
        existing.total_rate = round(total_rate, 2)
        existing.today_profit = round(total_today_profit, 2)
        existing.created_at = datetime.now()
    else:
        snap = FundSnapshot(
            snapshot_date=today_str,
            total_market=round(total_market, 2),
            total_cost=round(total_cost, 2),
            total_gain=round(total_gain, 2),
            total_rate=round(total_rate, 2),
            today_profit=round(total_today_profit, 2),
        )
        db.add(snap)

    # UPSERT 明细快照
    existing_items = {
        item.code: item
        for item in db.query(FundSnapshotItem).filter(FundSnapshotItem.snapshot_date == today_str).all()
    }
    for item in items_data:
        if item["code"] in existing_items:
            ex = existing_items[item["code"]]
            ex.name = item["name"]
            ex.nav = item["nav"]
            ex.shares = item["shares"]
            ex.market_value = item["market_value"]
            ex.day_chg = item["day_chg"]
            ex.today_gain = item["today_gain"]
        else:
            db.add(FundSnapshotItem(snapshot_date=today_str, **item))

    db.commit()
    return {
        "ok": True,
        "message": f"快照已保存（{today_str}）",
        "date": today_str,
        "total_market": round(total_market, 2),
        "fund_count": len(items_data),
    }


# ============================================================
# 辅助函数
# ============================================================

def fund_to_dict(f: FundFavorite) -> dict:
    """FundFavorite ORM → dict"""
    return {
        "code": f.code,
        "name": f.name,
        "type": f.type,
        "is_etf": f.is_etf,
        "group_id": f.group_id,
        "nav": f.nav or 0,
        "est_nav": f.est_nav or 0,
        "nav_date": f.nav_date or "",
        "day_chg": f.day_chg or 0,
        "val_time": f.val_time or "",
        "no_estimate": f.no_estimate or False,
        "shares": f.shares or 0,
        "cost_nav": f.cost_nav or 0,
        "manager": f.manager or "--",
        "company": f.company or "--",
        "scale": f.scale or 0,
        "ret_1m": f.ret_1m or 0,
        "ret_3m": f.ret_3m or 0,
        "ret_6m": f.ret_6m or 0,
        "ret_1y": f.ret_1y or 0,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "updated_at": f.updated_at.isoformat() if f.updated_at else None,
    }
