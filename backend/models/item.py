"""重要物品管理数据模型"""
from sqlalchemy import Column, Integer, String, Float, Text, Boolean
from sqlalchemy.sql import func
from database import Base


# 物品分类配置
ITEM_CATEGORIES = {
    '电子数码': {'icon': '💻', 'color': '#3B82F6'},
    '证件卡证': {'icon': '🪪', 'color': '#8B5CF6'},
    '钥匙门禁': {'icon': '🔑', 'color': '#F59E0B'},
    '珠宝首饰': {'icon': '💍', 'color': '#EC4899'},
    '收藏品': {'icon': '🎨', 'color': '#6366F1'},
    '家电家具': {'icon': '🏠', 'color': '#10B981'},
    '工具仪器': {'icon': '🔧', 'color': '#F97316'},
    '文件资料': {'icon': '📁', 'color': '#64748B'},
    '其他': {'icon': '📦', 'color': '#94A3B8'},
}


class Item(Base):
    """重要物品"""
    __tablename__ = "important_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="物品名称")
    category = Column(String(50), nullable=False, default="其他", comment="分类")
    brand = Column(String(100), default="", comment="品牌/型号")
    purchase_date = Column(String(20), default="", comment="购入日期")
    purchase_price = Column(Float, default=0, comment="购入价格")
    estimated_value = Column(Float, default=0, comment="当前估值")
    serial_number = Column(String(200), default="", comment="序列号/编号")
    location = Column(String(500), default="", comment="存放位置")
    status = Column(String(20), default="在用", comment="状态：在用/闲置/出借/已出售")
    photo_path = Column(String(500), default="", comment="照片路径")
    notes = Column(Text, default="", comment="备注")
    is_important = Column(Boolean, default=False, comment="是否标记为重要")
    created_at = Column(String(20), server_default=func.now())
    updated_at = Column(String(20), server_default=func.now())
