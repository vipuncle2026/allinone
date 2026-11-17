"""健康管理 API 路由：成员 / 体检 / 疾病 / 附件 / 统计"""
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db, get_upload_dir
from models.health import (
    FamilyMember, HealthCheckup, HealthCheckupItem, DiseaseRecord,
    DiseaseVisit, HealthAttachment, HealthExpense,
)
from services.upload_utils import safe_remove_upload

router = APIRouter(prefix="/api/health", tags=["健康管理"])

UPLOAD_DIR = get_upload_dir("health")
os.makedirs(UPLOAD_DIR, exist_ok=True)

RELATIONSHIPS = ["本人", "配偶", "父亲", "母亲", "儿子", "女儿", "其他"]
DISEASE_STATUSES = ["治疗中", "慢性病", "已治愈", "已停访"]
EXPENSE_CATEGORIES = ["挂号", "检查", "药品", "治疗", "住院", "其他"]
EXPENSE_REF_TYPES = ("checkup", "disease", "visit")


# ─── 附件工具 ───────────────────────────────────────────

def _attachment_file_delete(att: HealthAttachment):
    safe_remove_upload(att.file_path)


def _attachment_to_dict(att: HealthAttachment) -> dict:
    return {
        "id": att.id,
        "ref_type": att.ref_type,
        "ref_id": att.ref_id,
        "member_id": att.member_id,
        "file_name": att.file_name,
        "file_path": att.file_path,
        "file_type": att.file_type,
        "created_at": str(att.created_at) if att.created_at else "",
    }


def _member_to_dict(m: FamilyMember) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "relationship": m.relationship,
        "gender": m.gender,
        "birthday": m.birthday,
        "blood_type": m.blood_type,
        "height": m.height,
        "weight": m.weight,
        "photo_path": m.photo_path,
        "allergy_history": m.allergy_history,
        "medical_history": m.medical_history,
        "notes": m.notes,
    }


def _checkup_to_dict(c: HealthCheckup, member_name: str = "") -> dict:
    return {
        "id": c.id,
        "member_id": c.member_id,
        "member_name": member_name,
        "checkup_date": c.checkup_date,
        "hospital": c.hospital,
        "checkup_type": c.checkup_type,
        "cost": c.cost or 0,
        "summary": c.summary,
        "notes": c.notes,
    }


def _expense_to_dict(e: HealthExpense) -> dict:
    return {
        "id": e.id,
        "member_id": e.member_id,
        "ref_type": e.ref_type,
        "ref_id": e.ref_id,
        "expense_date": e.expense_date,
        "category": e.category,
        "amount": e.amount or 0,
        "note": e.note,
        "created_at": str(e.created_at) if e.created_at else "",
    }


def _item_to_dict(i: HealthCheckupItem) -> dict:
    return {
        "id": i.id,
        "checkup_id": i.checkup_id,
        "member_id": i.member_id,
        "item_name": i.item_name,
        "item_category": i.item_category,
        "value": i.value,
        "text_value": i.text_value,
        "unit": i.unit,
        "reference_range": i.reference_range,
        "abnormal_flag": i.abnormal_flag,
    }


def _disease_to_dict(d: DiseaseRecord, member_name: str = "", visit_count: int = 0,
                     expense_total: float = 0, attachment_count: int = 0) -> dict:
    return {
        "id": d.id,
        "member_id": d.member_id,
        "member_name": member_name,
        "disease_name": d.disease_name,
        "diagnosed_date": d.diagnosed_date,
        "status": d.status,
        "severity": d.severity,
        "hospital": d.hospital,
        "doctor": d.doctor,
        "notes": d.notes,
        "visit_count": visit_count,
        "expense_total": round(expense_total or 0, 2),
        "attachment_count": attachment_count,
    }


def _visit_to_dict(v: DiseaseVisit) -> dict:
    return {
        "id": v.id,
        "disease_id": v.disease_id,
        "member_id": v.member_id,
        "visit_date": v.visit_date,
        "hospital": v.hospital,
        "department": v.department,
        "doctor": v.doctor,
        "diagnosis": v.diagnosis,
        "treatment": v.treatment,
        "notes": v.notes,
    }


# ─── Schemas ────────────────────────────────────────────

class MemberCreate(BaseModel):
    name: str
    relationship: str = "本人"
    gender: str = ""
    birthday: str = ""
    blood_type: str = ""
    height: float = 0
    weight: float = 0
    photo_path: str = ""
    allergy_history: str = ""
    medical_history: str = ""
    notes: str = ""


class MemberUpdate(MemberCreate):
    name: Optional[str] = None  # type: ignore


class CheckupItemIn(BaseModel):
    item_name: str
    item_category: str = ""
    value: Optional[float] = None
    text_value: str = ""
    unit: str = ""
    reference_range: str = ""
    abnormal_flag: str = "正常"


class CheckupCreate(BaseModel):
    member_id: int
    checkup_date: str
    hospital: str = ""
    checkup_type: str = "年度体检"
    cost: float = 0
    summary: str = ""
    notes: str = ""
    items: list[CheckupItemIn] = []


class CheckupUpdate(CheckupCreate):
    member_id: Optional[int] = None  # type: ignore
    checkup_date: Optional[str] = None  # type: ignore


class DiseaseCreate(BaseModel):
    member_id: int
    disease_name: str
    diagnosed_date: str = ""
    status: str = "治疗中"
    severity: str = ""
    hospital: str = ""
    doctor: str = ""
    notes: str = ""


class DiseaseUpdate(DiseaseCreate):
    member_id: Optional[int] = None  # type: ignore
    disease_name: Optional[str] = None  # type: ignore


class VisitCreate(BaseModel):
    disease_id: int
    member_id: int
    visit_date: str
    hospital: str = ""
    department: str = ""
    doctor: str = ""
    diagnosis: str = ""
    treatment: str = ""
    notes: str = ""


class VisitUpdate(VisitCreate):
    disease_id: Optional[int] = None  # type: ignore
    member_id: Optional[int] = None  # type: ignore
    visit_date: Optional[str] = None  # type: ignore


class ExpenseCreate(BaseModel):
    ref_type: str
    ref_id: int
    member_id: Optional[int] = None
    expense_date: str = ""
    category: str = "其他"
    amount: float = 0
    note: str = ""


class ExpenseUpdate(BaseModel):
    expense_date: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    note: Optional[str] = None


# ─── 配置 ───────────────────────────────────────────────

@router.get("/config")
def get_config():
    return {
        "relationships": RELATIONSHIPS,
        "disease_statuses": DISEASE_STATUSES,
        "expense_categories": EXPENSE_CATEGORIES,
        "checkup_types": ["年度体检", "入职体检", "专项检查", "其他"],
    }


# ─── 成员管理 ───────────────────────────────────────────

@router.get("/members")
def list_members(keyword: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(FamilyMember)
    if keyword:
        q = q.filter(FamilyMember.name.contains(keyword))
    members = q.order_by(FamilyMember.id).all()
    result = []
    for m in members:
        d = _member_to_dict(m)
        d["checkup_count"] = db.query(func.count(HealthCheckup.id)).filter(HealthCheckup.member_id == m.id).scalar() or 0
        d["disease_count"] = db.query(func.count(DiseaseRecord.id)).filter(DiseaseRecord.member_id == m.id).scalar() or 0
        result.append(d)
    return result


@router.post("/members")
def create_member(data: MemberCreate, db: Session = Depends(get_db)):
    m = FamilyMember(**data.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id, "message": "创建成功"}


@router.put("/members/{member_id}")
def update_member(member_id: int, data: MemberUpdate, db: Session = Depends(get_db)):
    m = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not m:
        raise HTTPException(404, "成员不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(m, k, v)
    m.updated_at = datetime.now()
    db.commit()
    return {"message": "更新成功"}


@router.delete("/members/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """删除成员，级联删除体检/疾病/就诊/附件"""
    m = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not m:
        raise HTTPException(404, "成员不存在")
    # 体检及其明细
    checkups = db.query(HealthCheckup).filter(HealthCheckup.member_id == member_id).all()
    for c in checkups:
        db.query(HealthCheckupItem).filter(HealthCheckupItem.checkup_id == c.id).delete()
    db.query(HealthCheckup).filter(HealthCheckup.member_id == member_id).delete(synchronize_session=False)
    # 就诊及其附件
    visits = db.query(DiseaseVisit).filter(DiseaseVisit.member_id == member_id).all()
    for v in visits:
        for att in db.query(HealthAttachment).filter(HealthAttachment.ref_type == "visit", HealthAttachment.ref_id == v.id).all():
            _attachment_file_delete(att)
            db.delete(att)
    db.query(DiseaseVisit).filter(DiseaseVisit.member_id == member_id).delete(synchronize_session=False)
    # 疾病档案附件
    for att in db.query(HealthAttachment).filter(HealthAttachment.member_id == member_id).all():
        _attachment_file_delete(att)
        db.delete(att)
    db.query(DiseaseRecord).filter(DiseaseRecord.member_id == member_id).delete(synchronize_session=False)
    db.delete(m)
    db.commit()
    return {"message": "删除成功"}


@router.post("/members/upload-photo")
async def upload_member_photo(file: UploadFile = File(...)):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
        raise HTTPException(400, "仅支持图片文件（jpg/png/gif/webp/bmp）")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "图片大小不能超过 5MB")
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(content)
    return {"path": f"uploads/health/{filename}"}


# ─── 健康体检 ───────────────────────────────────────────

@router.get("/checkups")
def list_checkups(
    member_id: Optional[int] = None,
    year: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(HealthCheckup)
    if member_id:
        q = q.filter(HealthCheckup.member_id == member_id)
    if year:
        q = q.filter(HealthCheckup.checkup_date.startswith(str(year)))
    if keyword:
        q = q.filter(
            (HealthCheckup.hospital.contains(keyword)) |
            (HealthCheckup.summary.contains(keyword))
        )
    checkups = q.order_by(desc(HealthCheckup.checkup_date)).all()
    members = {m.id: m.name for m in db.query(FamilyMember).all()}
    result = []
    for c in checkups:
        d = _checkup_to_dict(c, members.get(c.member_id, ""))
        d["item_count"] = db.query(func.count(HealthCheckupItem.id)).filter(HealthCheckupItem.checkup_id == c.id).scalar() or 0
        d["abnormal_count"] = db.query(func.count(HealthCheckupItem.id)).filter(
            HealthCheckupItem.checkup_id == c.id,
            HealthCheckupItem.abnormal_flag != "正常",
        ).scalar() or 0
        d["attachments"] = [
            _attachment_to_dict(a) for a in db.query(HealthAttachment).filter(
                HealthAttachment.ref_type == "checkup", HealthAttachment.ref_id == c.id
            ).all()
        ]
        result.append(d)
    return result


@router.get("/checkups/{checkup_id}")
def get_checkup(checkup_id: int, db: Session = Depends(get_db)):
    c = db.query(HealthCheckup).filter(HealthCheckup.id == checkup_id).first()
    if not c:
        raise HTTPException(404, "体检记录不存在")
    items = db.query(HealthCheckupItem).filter(HealthCheckupItem.checkup_id == checkup_id).all()
    d = _checkup_to_dict(c)
    d["items"] = [_item_to_dict(i) for i in items]
    d["attachments"] = [
        _attachment_to_dict(a) for a in db.query(HealthAttachment).filter(
            HealthAttachment.ref_type == "checkup", HealthAttachment.ref_id == checkup_id
        ).all()
    ]
    return d


@router.post("/checkups")
def create_checkup(data: CheckupCreate, db: Session = Depends(get_db)):
    c = HealthCheckup(
        member_id=data.member_id,
        checkup_date=data.checkup_date,
        hospital=data.hospital,
        checkup_type=data.checkup_type,
        cost=data.cost or 0,
        summary=data.summary,
        notes=data.notes,
    )
    db.add(c)
    db.flush()
    for item in data.items:
        db.add(HealthCheckupItem(
            checkup_id=c.id,
            member_id=data.member_id,
            checkup_date=data.checkup_date,
            **item.model_dump(),
        ))
    db.commit()
    return {"id": c.id, "message": "创建成功"}


@router.put("/checkups/{checkup_id}")
def update_checkup(checkup_id: int, data: CheckupUpdate, db: Session = Depends(get_db)):
    c = db.query(HealthCheckup).filter(HealthCheckup.id == checkup_id).first()
    if not c:
        raise HTTPException(404, "体检记录不存在")
    update = data.model_dump(exclude_none=True)
    items = update.pop("items", None)
    for k, v in update.items():
        setattr(c, k, v)
    if items is not None:
        # 全量替换明细
        db.query(HealthCheckupItem).filter(HealthCheckupItem.checkup_id == checkup_id).delete()
        for item in items:
            db.add(HealthCheckupItem(
                checkup_id=checkup_id,
                member_id=c.member_id,
                checkup_date=c.checkup_date,
                **item,
            ))
    db.commit()
    return {"message": "更新成功"}


@router.delete("/checkups/{checkup_id}")
def delete_checkup(checkup_id: int, db: Session = Depends(get_db)):
    c = db.query(HealthCheckup).filter(HealthCheckup.id == checkup_id).first()
    if not c:
        raise HTTPException(404, "体检记录不存在")
    db.query(HealthCheckupItem).filter(HealthCheckupItem.checkup_id == checkup_id).delete()
    for att in db.query(HealthAttachment).filter(HealthAttachment.ref_type == "checkup", HealthAttachment.ref_id == checkup_id).all():
        _attachment_file_delete(att)
        db.delete(att)
    db.query(HealthExpense).filter(HealthExpense.ref_type == "checkup", HealthExpense.ref_id == checkup_id).delete(synchronize_session=False)
    db.delete(c)
    db.commit()
    return {"message": "删除成功"}


# ─── 疾病管理 ───────────────────────────────────────────

@router.get("/diseases")
def list_diseases(
    member_id: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(DiseaseRecord)
    if member_id:
        q = q.filter(DiseaseRecord.member_id == member_id)
    if status:
        q = q.filter(DiseaseRecord.status == status)
    if keyword:
        q = q.filter(
            (DiseaseRecord.disease_name.contains(keyword)) |
            (DiseaseRecord.hospital.contains(keyword)) |
            (DiseaseRecord.notes.contains(keyword))
        )
    diseases = q.order_by(DiseaseRecord.status, desc(DiseaseRecord.diagnosed_date)).all()
    members = {m.id: m.name for m in db.query(FamilyMember).all()}
    result = []
    for d in diseases:
        visit_count = db.query(func.count(DiseaseVisit.id)).filter(DiseaseVisit.disease_id == d.id).scalar() or 0
        expense_total = db.query(func.coalesce(func.sum(HealthExpense.amount), 0)).filter(
            HealthExpense.ref_type == "disease", HealthExpense.ref_id == d.id
        ).scalar() or 0
        attachment_count = db.query(func.count(HealthAttachment.id)).filter(
            HealthAttachment.ref_type == "disease", HealthAttachment.ref_id == d.id
        ).scalar() or 0
        result.append(_disease_to_dict(
            d, members.get(d.member_id, ""), visit_count,
            float(expense_total), int(attachment_count),
        ))
    return result


@router.post("/diseases")
def create_disease(data: DiseaseCreate, db: Session = Depends(get_db)):
    d = DiseaseRecord(**data.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "message": "创建成功"}


@router.put("/diseases/{disease_id}")
def update_disease(disease_id: int, data: DiseaseUpdate, db: Session = Depends(get_db)):
    d = db.query(DiseaseRecord).filter(DiseaseRecord.id == disease_id).first()
    if not d:
        raise HTTPException(404, "疾病档案不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(d, k, v)
    d.updated_at = datetime.now()
    db.commit()
    return {"message": "更新成功"}


@router.delete("/diseases/{disease_id}")
def delete_disease(disease_id: int, db: Session = Depends(get_db)):
    d = db.query(DiseaseRecord).filter(DiseaseRecord.id == disease_id).first()
    if not d:
        raise HTTPException(404, "疾病档案不存在")
    visits = db.query(DiseaseVisit).filter(DiseaseVisit.disease_id == disease_id).all()
    for v in visits:
        for att in db.query(HealthAttachment).filter(HealthAttachment.ref_type == "visit", HealthAttachment.ref_id == v.id).all():
            _attachment_file_delete(att)
            db.delete(att)
        db.query(HealthExpense).filter(HealthExpense.ref_type == "visit", HealthExpense.ref_id == v.id).delete(synchronize_session=False)
    # 疾病级附件与费用
    for att in db.query(HealthAttachment).filter(HealthAttachment.ref_type == "disease", HealthAttachment.ref_id == disease_id).all():
        _attachment_file_delete(att)
        db.delete(att)
    db.query(HealthExpense).filter(HealthExpense.ref_type == "disease", HealthExpense.ref_id == disease_id).delete(synchronize_session=False)
    db.query(DiseaseVisit).filter(DiseaseVisit.disease_id == disease_id).delete(synchronize_session=False)
    db.delete(d)
    db.commit()
    return {"message": "删除成功"}


# ─── 就诊记录 ───────────────────────────────────────────

@router.get("/visits")
def list_visits(disease_id: int = Query(...), db: Session = Depends(get_db)):
    visits = db.query(DiseaseVisit).filter(DiseaseVisit.disease_id == disease_id) \
        .order_by(desc(DiseaseVisit.visit_date)).all()
    result = []
    for v in visits:
        d = _visit_to_dict(v)
        d["attachments"] = [
            _attachment_to_dict(a) for a in db.query(HealthAttachment).filter(
                HealthAttachment.ref_type == "visit", HealthAttachment.ref_id == v.id
            ).all()
        ]
        result.append(d)
    return result


@router.post("/visits")
def create_visit(data: VisitCreate, db: Session = Depends(get_db)):
    v = DiseaseVisit(**data.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return {"id": v.id, "message": "创建成功"}


@router.put("/visits/{visit_id}")
def update_visit(visit_id: int, data: VisitUpdate, db: Session = Depends(get_db)):
    v = db.query(DiseaseVisit).filter(DiseaseVisit.id == visit_id).first()
    if not v:
        raise HTTPException(404, "就诊记录不存在")
    for k, v_ in data.model_dump(exclude_none=True).items():
        setattr(v, k, v_)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/visits/{visit_id}")
def delete_visit(visit_id: int, db: Session = Depends(get_db)):
    v = db.query(DiseaseVisit).filter(DiseaseVisit.id == visit_id).first()
    if not v:
        raise HTTPException(404, "就诊记录不存在")
    for att in db.query(HealthAttachment).filter(HealthAttachment.ref_type == "visit", HealthAttachment.ref_id == visit_id).all():
        _attachment_file_delete(att)
        db.delete(att)
    db.query(HealthExpense).filter(HealthExpense.ref_type == "visit", HealthExpense.ref_id == visit_id).delete(synchronize_session=False)
    db.delete(v)
    db.commit()
    return {"message": "删除成功"}


# ─── 医疗花费 ───────────────────────────────────────────

def _resolve_ref_member(ref_type: str, ref_id: int, db: Session) -> int:
    """根据挂载对象解析成员 ID，并校验对象存在"""
    if ref_type == "checkup":
        ref = db.query(HealthCheckup).filter(HealthCheckup.id == ref_id).first()
    elif ref_type == "disease":
        ref = db.query(DiseaseRecord).filter(DiseaseRecord.id == ref_id).first()
    elif ref_type == "visit":
        ref = db.query(DiseaseVisit).filter(DiseaseVisit.id == ref_id).first()
    else:
        raise HTTPException(400, "ref_type 必须是 checkup / disease / visit")
    if not ref:
        raise HTTPException(404, "挂载对象不存在")
    return ref.member_id


@router.get("/expenses")
def list_expenses(
    ref_type: str = Query(...),
    ref_id: int = Query(...),
    db: Session = Depends(get_db),
):
    if ref_type not in EXPENSE_REF_TYPES:
        raise HTTPException(400, "ref_type 必须是 checkup / disease / visit")
    rows = db.query(HealthExpense).filter(
        HealthExpense.ref_type == ref_type, HealthExpense.ref_id == ref_id
    ).order_by(desc(HealthExpense.expense_date), desc(HealthExpense.id)).all()
    total = sum((r.amount or 0) for r in rows)
    return {"total": round(total, 2), "items": [_expense_to_dict(r) for r in rows]}


@router.post("/expenses")
def create_expense(data: ExpenseCreate, db: Session = Depends(get_db)):
    member_id = data.member_id or _resolve_ref_member(data.ref_type, data.ref_id, db)
    e = HealthExpense(
        member_id=member_id,
        ref_type=data.ref_type,
        ref_id=data.ref_id,
        expense_date=data.expense_date,
        category=data.category or "其他",
        amount=data.amount or 0,
        note=data.note,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"id": e.id, "message": "创建成功"}


@router.put("/expenses/{expense_id}")
def update_expense(expense_id: int, data: ExpenseUpdate, db: Session = Depends(get_db)):
    e = db.query(HealthExpense).filter(HealthExpense.id == expense_id).first()
    if not e:
        raise HTTPException(404, "费用记录不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(e, k, v)
    db.commit()
    return {"message": "更新成功"}


@router.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    e = db.query(HealthExpense).filter(HealthExpense.id == expense_id).first()
    if not e:
        raise HTTPException(404, "费用记录不存在")
    db.delete(e)
    db.commit()
    return {"message": "删除成功"}


# ─── 附件（检查报告上传）────────────────────────────────

@router.get("/attachments")
def list_attachments(
    ref_type: str = Query(...),
    ref_id: int = Query(...),
    db: Session = Depends(get_db),
):
    if ref_type not in EXPENSE_REF_TYPES:
        raise HTTPException(400, "ref_type 必须是 checkup、disease 或 visit")
    rows = db.query(HealthAttachment).filter(
        HealthAttachment.ref_type == ref_type, HealthAttachment.ref_id == ref_id
    ).order_by(desc(HealthAttachment.id)).all()
    return [_attachment_to_dict(a) for a in rows]


@router.post("/attachments/upload")
async def upload_attachment(
    ref_type: str = Query(..., description="checkup / disease / visit"),
    ref_id: int = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if ref_type not in EXPENSE_REF_TYPES:
        raise HTTPException(400, "ref_type 必须是 checkup、disease 或 visit")
    # 校验挂载对象存在，取 member_id
    if ref_type == "checkup":
        ref = db.query(HealthCheckup).filter(HealthCheckup.id == ref_id).first()
    elif ref_type == "disease":
        ref = db.query(DiseaseRecord).filter(DiseaseRecord.id == ref_id).first()
    else:
        ref = db.query(DiseaseVisit).filter(DiseaseVisit.id == ref_id).first()
    if not ref:
        raise HTTPException(404, "挂载对象不存在")

    filename = file.filename or "report"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        file_type = "pdf"
    elif ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
        file_type = "image"
    else:
        raise HTTPException(400, "仅支持图片（jpg/png/gif/webp/bmp）或 PDF 文件")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "文件大小不能超过 20MB")

    saved_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    with open(os.path.join(UPLOAD_DIR, saved_name), "wb") as f:
        f.write(content)
    att = HealthAttachment(
        ref_type=ref_type,
        ref_id=ref_id,
        member_id=ref.member_id,
        file_name=filename,
        file_path=f"uploads/health/{saved_name}",
        file_type=file_type,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return _attachment_to_dict(att)


@router.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):
    att = db.query(HealthAttachment).filter(HealthAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(404, "附件不存在")
    _attachment_file_delete(att)
    db.delete(att)
    db.commit()
    return {"message": "附件已删除"}


# ─── 统计分析 ───────────────────────────────────────────

@router.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)):
    """成员健康概览卡片"""
    members = db.query(FamilyMember).order_by(FamilyMember.id).all()
    result = []
    for m in members:
        last_checkup = db.query(HealthCheckup).filter(HealthCheckup.member_id == m.id) \
            .order_by(desc(HealthCheckup.checkup_date)).first()
        disease_count = db.query(func.count(DiseaseRecord.id)).filter(
            DiseaseRecord.member_id == m.id, DiseaseRecord.status.in_(["治疗中", "慢性病"])
        ).scalar() or 0
        # 最近一次体检的异常项
        abnormal_items = []
        if last_checkup:
            items = db.query(HealthCheckupItem).filter(
                HealthCheckupItem.checkup_id == last_checkup.id,
                HealthCheckupItem.abnormal_flag != "正常",
            ).all()
            abnormal_items = [i.item_name for i in items]
        result.append({
            **_member_to_dict(m),
            "last_checkup_date": last_checkup.checkup_date if last_checkup else "",
            "last_checkup_hospital": last_checkup.hospital if last_checkup else "",
            "active_disease_count": disease_count,
            "abnormal_items": abnormal_items,
        })
    return result


@router.get("/stats/trends")
def stats_trends(
    member_id: int = Query(...),
    item_name: str = Query(...),
    db: Session = Depends(get_db),
):
    """单项指标跨体检趋势"""
    items = db.query(HealthCheckupItem).filter(
        HealthCheckupItem.member_id == member_id,
        HealthCheckupItem.item_name == item_name,
        HealthCheckupItem.value.isnot(None),
    ).order_by(HealthCheckupItem.checkup_date).all()
    return [
        {
            "date": i.checkup_date,
            "value": i.value,
            "unit": i.unit,
            "reference_range": i.reference_range,
            "abnormal_flag": i.abnormal_flag,
        }
        for i in items
    ]


@router.get("/stats/items")
def stats_items(member_id: int = Query(...), db: Session = Depends(get_db)):
    """该成员所有可统计的量化指标名列表"""
    rows = db.query(
        HealthCheckupItem.item_name,
        func.count(HealthCheckupItem.id).label("cnt"),
    ).filter(
        HealthCheckupItem.member_id == member_id,
        HealthCheckupItem.value.isnot(None),
    ).group_by(HealthCheckupItem.item_name).having(func.count(HealthCheckupItem.id) > 0).all()
    return [{"item_name": r[0], "count": r[1]} for r in sorted(rows, key=lambda x: -x[1])]


@router.get("/stats/abnormal")
def stats_abnormal(member_id: int = Query(...), db: Session = Depends(get_db)):
    """最近一次体检异常项汇总（含明细）"""
    last_checkup = db.query(HealthCheckup).filter(HealthCheckup.member_id == member_id) \
        .order_by(desc(HealthCheckup.checkup_date)).first()
    if not last_checkup:
        return {"checkup": None, "items": []}
    items = db.query(HealthCheckupItem).filter(
        HealthCheckupItem.checkup_id == last_checkup.id,
        HealthCheckupItem.abnormal_flag != "正常",
    ).all()
    return {
        "checkup": _checkup_to_dict(last_checkup),
        "items": [_item_to_dict(i) for i in items],
    }


# ─── 聚合统计：按年 / 按人（疾病、就诊、花费） ──────────────────

def _year_of(date_str: Optional[str]) -> Optional[int]:
    """从 'YYYY-MM-DD' / 'YYYY-MM' / 'YYYY' 中取年份"""
    if not date_str:
        return None
    s = str(date_str).strip()
    if len(s) < 4 or not s[:4].isdigit():
        return None
    return int(s[:4])


@router.get("/stats/aggregate")
def stats_aggregate(
    member_id: Optional[int] = Query(None, description="成员ID，留空=全部成员"),
    year: Optional[int] = Query(None, description="年份，留空=全部年份"),
    db: Session = Depends(get_db),
):
    """健康统计聚合：KPI / 按年 / 按人 / 花费构成 / 疾病排行

    数据口径：
    - 体检：health_checkups.checkup_date + cost
    - 就诊：disease_visits.visit_date
    - 疾病：disease_records.diagnosed_date（新增按确诊年份）
    - 花费：health_expenses.amount（明细账，按 expense_date）
    """
    members = db.query(FamilyMember).order_by(FamilyMember.id).all()
    member_map = {m.id: m for m in members}

    def _m_ok(mid) -> bool:
        return member_id is None or mid == member_id

    def _y_ok(date_str) -> bool:
        if year is None:
            return True
        return _year_of(date_str) == year

    checkups = [c for c in db.query(HealthCheckup).all() if _m_ok(c.member_id)]
    visits = [v for v in db.query(DiseaseVisit).all() if _m_ok(v.member_id)]
    diseases = [d for d in db.query(DiseaseRecord).all() if _m_ok(d.member_id)]
    expenses = [e for e in db.query(HealthExpense).all() if _m_ok(e.member_id)]
    abnormal_rows = [
        i for i in db.query(HealthCheckupItem).all()
        if _m_ok(i.member_id) and i.abnormal_flag and i.abnormal_flag != "正常"
    ]

    # ── 可用年份列表（用于前端下拉）──
    years = set()
    for c in checkups:
        y = _year_of(c.checkup_date)
        if y: years.add(y)
    for v in visits:
        y = _year_of(v.visit_date)
        if y: years.add(y)
    for e in expenses:
        y = _year_of(e.expense_date)
        if y: years.add(y)
    for d in diseases:
        y = _year_of(d.diagnosed_date)
        if y: years.add(y)
    years = sorted(years, reverse=True)

    # ── KPI（受年份过滤）──
    ck_sel = [c for c in checkups if _y_ok(c.checkup_date)]
    vs_sel = [v for v in visits if _y_ok(v.visit_date)]
    ex_sel = [e for e in expenses if _y_ok(e.expense_date)]
    ds_sel = [d for d in diseases if _y_ok(d.diagnosed_date)]
    ab_sel = [i for i in abnormal_rows if _y_ok(i.checkup_date)]

    kpi = {
        "members": len([m for m in members if _m_ok(m.id)]),
        "checkup_count": len(ck_sel),
        "checkup_cost": round(sum(c.cost or 0 for c in ck_sel), 2),
        "visit_count": len(vs_sel),
        "expense_total": round(sum(e.amount or 0 for e in ex_sel), 2),
        "disease_active": len([d for d in diseases if (d.status or "") in ("治疗中", "慢性病")]),
        "disease_new": len(ds_sel),
        "disease_total": len(diseases),
        "abnormal_count": len(ab_sel),
    }

    # ── 按年（忽略年份过滤，始终给全部年份对比）──
    by_year = []
    for y in years:
        ck = [c for c in checkups if _year_of(c.checkup_date) == y]
        vs = [v for v in visits if _year_of(v.visit_date) == y]
        ex = [e for e in expenses if _year_of(e.expense_date) == y]
        ds = [d for d in diseases if _year_of(d.diagnosed_date) == y]
        ab = [i for i in abnormal_rows if _year_of(i.checkup_date) == y]
        by_year.append({
            "year": y,
            "checkup_count": len(ck),
            "checkup_cost": round(sum(c.cost or 0 for c in ck), 2),
            "visit_count": len(vs),
            "expense_total": round(sum(e.amount or 0 for e in ex), 2),
            "disease_new": len(ds),
            "abnormal_count": len(ab),
        })
    by_year.sort(key=lambda x: x["year"])

    # ── 按人（忽略成员过滤，始终给全部成员对比；受年份过滤）──
    by_member = []
    for m in members:
        ck = [c for c in ck_sel if c.member_id == m.id]
        vs = [v for v in vs_sel if v.member_id == m.id]
        ex = [e for e in ex_sel if e.member_id == m.id]
        ds = [d for d in ds_sel if d.member_id == m.id]
        ab = [i for i in ab_sel if i.member_id == m.id]
        active = len([
            d for d in diseases
            if d.member_id == m.id and (d.status or "") in ("治疗中", "慢性病")
        ])
        by_member.append({
            "member_id": m.id,
            "name": m.name,
            "relationship": m.relationship or "",
            "checkup_count": len(ck),
            "checkup_cost": round(sum(c.cost or 0 for c in ck), 2),
            "visit_count": len(vs),
            "expense_total": round(sum(e.amount or 0 for e in ex), 2),
            "disease_new": len(ds),
            "disease_active": active,
            "abnormal_count": len(ab),
        })
    by_member.sort(key=lambda x: (-x["expense_total"], -x["visit_count"]))

    # ── 花费构成（类别 + 挂载类型）──
    cat_map, ref_map = {}, {}
    for e in ex_sel:
        cat = (e.category or "其他").strip() or "其他"
        cat_map[cat] = cat_map.get(cat, 0) + (e.amount or 0)
        ref = {"checkup": "体检", "visit": "就诊", "disease": "疾病"}.get(e.ref_type or "", "其他")
        ref_map[ref] = ref_map.get(ref, 0) + (e.amount or 0)
    expense_by_category = [
        {"category": k, "amount": round(v, 2)}
        for k, v in sorted(cat_map.items(), key=lambda x: -x[1])
    ]
    expense_by_ref = [
        {"ref_type": k, "amount": round(v, 2)}
        for k, v in sorted(ref_map.items(), key=lambda x: -x[1])
    ]

    # ── 月度趋势（受年份过滤；year 为空时用最近有数据的年份）──
    trend_year = year or (years[0] if years else datetime.now().year)
    month_cost = [0.0] * 12
    month_visit = [0] * 12
    for e in expenses:
        if _year_of(e.expense_date) == trend_year and _y_ok(e.expense_date):
            try:
                mi = int(str(e.expense_date)[5:7]) - 1
                if 0 <= mi < 12:
                    month_cost[mi] += e.amount or 0
            except Exception:
                pass
    for v in visits:
        if _year_of(v.visit_date) == trend_year and _y_ok(v.visit_date):
            try:
                mi = int(str(v.visit_date)[5:7]) - 1
                if 0 <= mi < 12:
                    month_visit[mi] += 1
            except Exception:
                pass
    monthly = [
        {"month": i + 1, "amount": round(month_cost[i], 2), "visits": month_visit[i]}
        for i in range(12)
    ]

    # ── 疾病排行：就诊次数 / 花费 / 最近就诊 ──
    visit_by_disease, last_visit = {}, {}
    for v in vs_sel:
        visit_by_disease[v.disease_id] = visit_by_disease.get(v.disease_id, 0) + 1
        if v.visit_date:
            if v.disease_id not in last_visit or v.visit_date > last_visit[v.disease_id]:
                last_visit[v.disease_id] = v.visit_date
    cost_by_disease = {}
    for e in ex_sel:
        if (e.ref_type or "") == "disease":
            cost_by_disease[e.ref_id] = cost_by_disease.get(e.ref_id, 0) + (e.amount or 0)

    disease_rows = []
    for d in ds_sel:
        m = member_map.get(d.member_id)
        disease_rows.append({
            "disease_id": d.id,
            "disease_name": d.disease_name,
            "member_id": d.member_id,
            "member_name": m.name if m else "",
            "status": d.status or "",
            "severity": d.severity or "",
            "diagnosed_date": d.diagnosed_date or "",
            "visit_count": visit_by_disease.get(d.id, 0),
            "expense": round(cost_by_disease.get(d.id, 0), 2),
            "last_visit": last_visit.get(d.id, ""),
        })
    disease_rows.sort(key=lambda x: (-x["visit_count"], -x["expense"], x["disease_name"]))

    # ── 就诊按医院 Top（可选展示）──
    hospital_map = {}
    for v in vs_sel:
        h = (v.hospital or "").strip() or "未填写"
        hospital_map[h] = hospital_map.get(h, 0) + 1
    hospitals = [
        {"hospital": k, "count": v}
        for k, v in sorted(hospital_map.items(), key=lambda x: -x[1])[:10]
    ]

    return {
        "filters": {"member_id": member_id, "year": year},
        "years": years,
        "trend_year": trend_year,
        "kpi": kpi,
        "by_year": by_year,
        "by_member": by_member,
        "expense_by_category": expense_by_category,
        "expense_by_ref": expense_by_ref,
        "monthly": monthly,
        "diseases": disease_rows,
        "hospitals": hospitals,
    }
