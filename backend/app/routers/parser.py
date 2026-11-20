"""格式解析器接口：维护解析配置，覆盖提交配置、启用解析、废弃解析等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.parser import ParserService

router = APIRouter(prefix="/api/parser", tags=["格式解析器"])

service = ParserService()

LIST_FIELDS = ["解析编号", "输入格式", "输出格式", "字段映射", "类型转换", "空值处理", "异常策略", "解析状态"]
STATUSES = ["草稿", "已配置", "生效中", "已废弃"]


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出格式解析器清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "parser", "total": total, "items": items}


@router.get("/results")
def list_results(
    采样站: str | None = Query(default=None, description="按采样站过滤"),
    采集批次: str | None = Query(default=None, description="按采集批次过滤"),
) -> dict[str, Any]:
    """查询批次解析结果：标准字段值与实际使用的原字段名一并返回。"""
    items = service.list_results(采样站, 采集批次)
    return {"total": len(items), "items": items}


@router.get("/samples")
def list_samples(
    采样站: str | None = Query(default=None, description="按采样站过滤"),
    采集批次: str | None = Query(default=None, description="按采集批次过滤"),
) -> dict[str, Any]:
    """查询传感器原始样本：新表头的原值在这里始终可查。"""
    items = service.list_samples(采样站, 采集批次)
    return {"total": len(items), "items": items}


@router.post("/parse", response_model=ActionResult)
def parse_batch(payload: EntryPayload) -> ActionResult:
    """按采集字段别名映射数据集解析一个采集批次，写出标准字段。"""
    station = str(payload.values.get("采样站") or "")
    batch = str(payload.values.get("采集批次") or "")
    summary, message = service.parse_batch(station, batch)
    if summary is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=summary)


@router.get("", response_model=PageResult[dict])
def list_entries(
    request: Request,
    keyword: str | None = Query(default=None, description="按解析编号检索"),
    status: str | None = Query(default=None, description="草稿、已配置、生效中、已废弃"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按解析编号与状态过滤格式解析器列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    extra = {k: v for k, v in request.query_params.items() if k not in ("keyword", "status", "page", "size") and v.strip()}
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size, extra=extra)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条解析配置明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"解析配置 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条解析配置，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="解析配置已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条解析配置执行提交配置、启用解析、废弃解析；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
