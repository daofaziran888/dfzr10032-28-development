"""采集字段别名映射接口：维护别名映射数据集，读入传感器表头，查看有效映射。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.field_alias import FieldAliasService

router = APIRouter(prefix="/api/field_alias", tags=["采集字段别名映射"])

service = FieldAliasService()

LIST_FIELDS = ["映射编号", "标准字段", "来源名称", "采样站", "有效批次", "核对证据", "核对状态"]
STATUSES = ["待核对", "已确认", "已停用"]


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出采集字段别名映射清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "field_alias", "total": total, "items": items}


@router.get("/resolve")
def resolve_mapping(
    采样站: str = Query(..., description="采样站"),
    有效批次: str = Query(..., description="有效批次"),
) -> dict[str, Any]:
    """查看某站点某批次的有效映射：与格式解析器、采集结果校验共用同一份解析。"""
    return service.resolve(采样站, 有效批次)


@router.post("/ingest", response_model=ActionResult)
def ingest_headers(payload: EntryPayload) -> ActionResult:
    """读取传感器表头与来源字段名，归并进采集字段别名映射数据集。

    表头可显式给出（values.表头 为列表或逗号分隔文本）；缺省时从该站点
    该批次的传感器样本里读取实际表头。新来源登记为待核对，旧映射原样保留。
    """
    station = str(payload.values.get("采样站") or "")
    batch = str(payload.values.get("有效批次") or payload.values.get("采集批次") or "")
    raw_headers = payload.values.get("表头")
    headers: list[str] = []
    if isinstance(raw_headers, str):
        headers = [name.strip() for name in raw_headers.replace("，", ",").split(",")]
    elif isinstance(raw_headers, list):
        headers = [str(name) for name in raw_headers]
    result, message = service.ingest_headers(station, batch, headers or None)
    if result is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=result)


@router.get("", response_model=PageResult[dict])
def list_entries(
    request: Request,
    keyword: str | None = Query(default=None, description="按映射编号检索"),
    status: str | None = Query(default=None, description="待核对、已确认、已停用"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按映射编号、状态与字段过滤别名映射列表；旧批次映射同样可查。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    extra = {k: v for k, v in request.query_params.items() if k not in ("keyword", "status", "page", "size") and v.strip()}
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size, extra=extra)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条别名映射明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"别名映射 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条别名映射，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="别名映射已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条别名映射执行确认映射、停用映射；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
