"""采集结果校验接口：维护校验规则，覆盖提交测试、启用规则、停用规则等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.validator import ValidatorService

router = APIRouter(prefix="/api/validator", tags=["采集结果校验"])

service = ValidatorService()

LIST_FIELDS = ["规则编号", "校验字段", "校验类型", "期望值", "容错范围", "采样比例", "阻断级别", "规则状态"]
STATUSES = ["草稿", "待测试", "已启用", "已停用"]


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出采集结果校验清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "validator", "total": total, "items": items}


@router.get("/detail")
def validation_detail(
    采样站: str = Query(..., description="采样站"),
    采集批次: str = Query(..., description="采集批次"),
) -> dict[str, Any]:
    """校验明细：逐行给出标准字段值、实际使用的原字段名、冲突与处置单。"""
    detail, message = service.validation_detail(采样站, 采集批次)
    if detail is None:
        raise HTTPException(status_code=404, detail=message)
    return detail


@router.get("/disposals")
def list_disposals(
    采样站: str | None = Query(default=None, description="按采样站过滤"),
    采集批次: str | None = Query(default=None, description="按采集批次过滤"),
) -> dict[str, Any]:
    """查询处置单：处置单的有无及依据都能从对应原始行还原。"""
    items = service.list_disposals(采样站, 采集批次)
    return {"total": len(items), "items": items}


@router.post("/validate", response_model=ActionResult)
def validate_batch(payload: EntryPayload) -> ActionResult:
    """读取解析结果执行批次校验：超阈值开处置单，冲突行标记尚欠核对。"""
    station = str(payload.values.get("采样站") or "")
    batch = str(payload.values.get("采集批次") or "")
    summary, message = service.validate_batch(station, batch)
    if summary is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=summary)


@router.get("", response_model=PageResult[dict])
def list_entries(
    request: Request,
    keyword: str | None = Query(default=None, description="按规则编号检索"),
    status: str | None = Query(default=None, description="草稿、待测试、已启用、已停用"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按规则编号与状态过滤采集结果校验列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    extra = {k: v for k, v in request.query_params.items() if k not in ("keyword", "status", "page", "size") and v.strip()}
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size, extra=extra)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条校验规则明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"校验规则 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条校验规则，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="校验规则已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条校验规则执行提交测试、启用规则、停用规则；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
