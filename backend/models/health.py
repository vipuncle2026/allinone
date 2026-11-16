"""健康管理数据模型：家庭成员 / 健康体检 / 疾病管理"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class FamilyMember(Base):
    """家庭成员"""
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="姓名")
    relationship = Column(String(20), default="本人", comment="关系：本人/配偶/父亲/母亲/儿子/女儿/其他")
    gender = Column(String(10), default="", comment="性别")
    birthday = Column(String(20), default="", comment="出生日期")
    blood_type = Column(String(10), default="", comment="血型")
    height = Column(Float, default=0, comment="身高(cm)")
    weight = Column(Float, default=0, comment="体重(kg)")
    photo_path = Column(String(500), default="", comment="头像路径")
    allergy_history = Column(Text, default="", comment="过敏史")
    medical_history = Column(Text, default="", comment="既往病史")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class HealthCheckup(Base):
    """健康体检记录"""
    __tablename__ = "health_checkups"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False, index=True, comment="成员ID")
    checkup_date = Column(String(20), nullable=False, comment="体检日期")
    hospital = Column(String(200), default="", comment="体检机构")
    checkup_type = Column(String(50), default="年度体检", comment="类型：年度体检/入职体检/专项检查/其他")
    cost = Column(Float, default=0, comment="体检花费(元)")
    summary = Column(Text, default="", comment="体检总评/结论")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, server_default=func.now())


class HealthCheckupItem(Base):
    """体检指标明细"""
    __tablename__ = "health_checkup_items"

    id = Column(Integer, primary_key=True, index=True)
    checkup_id = Column(Integer, nullable=False, index=True, comment="体检记录ID")
    member_id = Column(Integer, nullable=False, index=True, comment="成员ID（冗余，便于统计）")
    checkup_date = Column(String(20), default="", comment="体检日期（冗余，便于趋势统计）")
    item_name = Column(String(100), nullable=False, comment="指标名称：血压/血糖/总胆固醇等")
    item_category = Column(String(50), default="", comment="指标分类：一般检查/血常规/血脂/肝功能/肾功能/血糖/尿常规/其他")
    value = Column(Float, comment="数值（可量化指标）")
    text_value = Column(String(200), default="", comment="文本值（非量化描述）")
    unit = Column(String(50), default="", comment="单位")
    reference_range = Column(String(100), default="", comment="参考范围")
    abnormal_flag = Column(String(20), default="正常", comment="标记：正常/偏高/偏低/异常")


class DiseaseRecord(Base):
    """疾病档案"""
    __tablename__ = "disease_records"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False, index=True, comment="成员ID")
    disease_name = Column(String(200), nullable=False, comment="疾病名称")
    diagnosed_date = Column(String(20), default="", comment="确诊日期")
    status = Column(String(20), default="治疗中", comment="状态：治疗中/慢性病/已治愈/已停访")
    severity = Column(String(20), default="", comment="严重程度：轻微/中度/严重")
    hospital = Column(String(200), default="", comment="确诊医院")
    doctor = Column(String(100), default="", comment="主治医生")
    notes = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class DiseaseVisit(Base):
    """就诊记录（疾病详情页时间线）"""
    __tablename__ = "disease_visits"

    id = Column(Integer, primary_key=True, index=True)
    disease_id = Column(Integer, nullable=False, index=True, comment="疾病档案ID")
    member_id = Column(Integer, nullable=False, index=True, comment="成员ID")
    visit_date = Column(String(20), nullable=False, comment="就诊日期")
    hospital = Column(String(200), default="", comment="医院")
    department = Column(String(100), default="", comment="科室")
    doctor = Column(String(100), default="", comment="医生")
    diagnosis = Column(Text, default="", comment="诊断结论")
    treatment = Column(Text, default="", comment="处理方案/用药")
    notes = Column(Text, default="", comment="医嘱/备注")
    created_at = Column(DateTime, server_default=func.now())


class HealthAttachment(Base):
    """健康模块附件（检查报告等，统一挂 ref_type + ref_id）"""
    __tablename__ = "health_attachments"

    id = Column(Integer, primary_key=True, index=True)
    ref_type = Column(String(30), nullable=False, index=True, comment="挂载类型：checkup=体检报告 / visit=就诊报告 / disease=疾病资料")
    ref_id = Column(Integer, nullable=False, index=True, comment="挂载对象ID")
    member_id = Column(Integer, nullable=False, index=True, comment="成员ID")
    file_name = Column(String(300), default="", comment="原始文件名")
    file_path = Column(String(500), nullable=False, comment="文件路径（uploads/health/xxx）")
    file_type = Column(String(20), default="image", comment="类型：image/pdf")
    created_at = Column(DateTime, server_default=func.now())


class HealthExpense(Base):
    """医疗花费明细（体检 / 疾病 / 就诊 均可挂）"""
    __tablename__ = "health_expenses"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, nullable=False, index=True, comment="成员ID")
    ref_type = Column(String(30), nullable=False, index=True, comment="挂载类型：checkup / disease / visit")
    ref_id = Column(Integer, nullable=False, index=True, comment="挂载对象ID")
    expense_date = Column(String(20), default="", comment="费用日期")
    category = Column(String(50), default="其他", comment="类别：挂号/检查/药品/治疗/住院/其他")
    amount = Column(Float, default=0, comment="金额(元)")
    note = Column(Text, default="", comment="备注")
    created_at = Column(DateTime, server_default=func.now())
