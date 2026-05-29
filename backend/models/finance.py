"""财务管理数据模型"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from datetime import datetime

from database import Base


# 资产类型定义（与 money 项目保持一致）
ASSET_TYPES = {
    "cash": {"label": "现金/活期", "icon": "💵", "color": "#22c55e"},
    "deposit": {"label": "定期存款", "icon": "🏦", "color": "#3b82f6"},
    "stock": {"label": "股票", "icon": "📈", "color": "#ef4444"},
    "fund": {"label": "基金", "icon": "📊", "color": "#f59e0b"},
    "realestate": {"label": "房产", "icon": "🏠", "color": "#8b5cf6"},
    "debt": {"label": "负债", "icon": "📉", "color": "#64748b"},
    "other": {"label": "其他", "icon": "📦", "color": "#ec4899"},
}

# 收支分类
INCOME_CATEGORIES = [
    "工资收入", "投资收益", "兼职收入", "红包收入", "退款", "利息收入", "其他收入"
]
EXPENSE_CATEGORIES = [
    "餐饮美食", "交通出行", "购物消费", "居家生活", "娱乐休闲",
    "医疗健康", "教育学习", "通讯网络", "人情往来", "投资支出",
    "旅行出游", "宠物", "其他支出"
]

ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES


class FinanceAccount(Base):
    """财务账户（资产）"""
    __tablename__ = "finance_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="账户名称")
    type = Column(String(20), nullable=False, default="cash",
                  comment="类型: cash/deposit/stock/fund/realestate/debt/other")
    amount = Column(Float, default=0, comment="当前金额")
    institution = Column(String(200), default="", comment="机构/平台")
    notes = Column(Text, default="", comment="备注")
    sort_order = Column(Integer, default=0, comment="排序序号")
    is_hidden = Column(Integer, default=0, comment="是否隐藏: 0/1")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FinanceTransaction(Base):
    """收支记录"""
    __tablename__ = "finance_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(10), nullable=False, comment="类型: income/expense")
    category = Column(String(50), nullable=False, comment="分类")
    amount = Column(Float, nullable=False, default=0, comment="金额")
    date = Column(String(20), nullable=False, index=True, comment="日期 YYYY-MM-DD")
    description = Column(String(500), default="", comment="描述")
    account_id = Column(Integer, default=None, index=True, comment="关联账户ID")
    # 新增字段：账单导入
    source = Column(String(20), default="manual", comment="来源: manual/alipay/wechat")
    counterparty = Column(String(200), default="", comment="交易对方")
    pay_method = Column(String(50), default="", comment="支付方式")
    trade_no = Column(String(100), default="", index=True, comment="平台订单号（去重用）")
    import_id = Column(Integer, default=None, index=True, comment="关联导入批次ID")
    is_transfer = Column(Integer, default=0, comment="是否转账类: 0/1（不计入收支统计）")
    notes = Column(Text, default="", comment="备注")
    raw_data = Column(Text, default="", comment="原始行JSON（追溯用）")
    created_at = Column(DateTime, default=datetime.now)


class FinanceBillImport(Base):
    """账单导入批次"""
    __tablename__ = "finance_bill_imports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(20), nullable=False, comment="来源: alipay/wechat")
    file_name = Column(String(200), default="", comment="原始文件名")
    total_count = Column(Integer, default=0, comment="解析总行数")
    imported_count = Column(Integer, default=0, comment="成功导入数")
    skipped_count = Column(Integer, default=0, comment="跳过（重复）数")
    failed_count = Column(Integer, default=0, comment="失败数")
    status = Column(String(20), default="pending", comment="状态: pending/completed/failed")
    created_at = Column(DateTime, default=datetime.now)


class FinanceCategoryRule(Base):
    """自动分类规则"""
    __tablename__ = "finance_category_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="规则名称")
    match_field = Column(String(20), nullable=False, default="description",
                         comment="匹配字段: description/counterparty")
    match_type = Column(String(20), nullable=False, default="contains",
                        comment="匹配方式: contains/equals/regex")
    match_value = Column(String(500), nullable=False, comment="匹配值")
    category = Column(String(50), nullable=False, comment="目标分类")
    txn_type = Column(String(10), default="all", comment="适用收支类型: income/expense/all")
    platform = Column(String(20), default="all", comment="适用平台: alipay/wechat/all")
    priority = Column(Integer, default=100, comment="优先级（数字越小越优先）")
    is_enabled = Column(Integer, default=1, comment="是否启用: 0/1")
    created_at = Column(DateTime, default=datetime.now)


class AssetSnapshot(Base):
    """资产快照（用于趋势图）"""
    __tablename__ = "asset_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(20), nullable=False, unique=True, comment="快照日期 YYYY-MM-DD")
    total_assets = Column(Float, default=0, comment="总资产")
    total_debt = Column(Float, default=0, comment="总负债")
    net_assets = Column(Float, default=0, comment="净资产")
    breakdown = Column(JSON, default=dict, comment="各类型资产分布 JSON")
    created_at = Column(DateTime, default=datetime.now)
