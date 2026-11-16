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
