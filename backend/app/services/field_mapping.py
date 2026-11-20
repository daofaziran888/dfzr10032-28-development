"""采集字段别名映射的共用解析：格式解析器与采集结果校验都从这一份映射取字段。

映射按（采样站， 有效批次）限定作用域：同一个来源字段名在不同站点、不同批次可以
指向不同标准字段，绝不按文本相等折叠。新读入的表头只登记为待核对映射，不覆盖旧映射；
旧批次的映射原样保留，可按批次查询。
"""
from __future__ import annotations

from typing import Any

from app.store import store

ALIAS_MODULE = "field_alias"
SAMPLE_MODULE = "sensor_sample"

CONFIRMED = "已确认"
PENDING = "待核对"
RETIRED = "已停用"


def _next_id(module: str) -> int:
    return max((int(row.get("id", 0)) for row in store.rows(module)), default=0) + 1


def _next_code(module: str, prefix: str) -> str:
    return f"{prefix}-{_next_id(module):04d}"


def scoped_aliases(station: str, batch: str, *, include_retired: bool = False) -> list[dict[str, Any]]:
    """取（采样站， 有效批次）限定下的映射条目；已停用的默认不参与解析。"""
    rows = [
        row for row in store.rows(ALIAS_MODULE)
        if row.get("采样站") == station and row.get("有效批次") == batch
    ]
    if not include_retired:
        rows = [row for row in rows if row.get("status") != RETIRED]
    return rows


def resolve_mapping(station: str, batch: str) -> dict[str, Any]:
    """共用映射解析：返回该站点该批次下每个标准字段的已确认来源与全部候选来源。

    解析器写标准字段、校验读字段冲突都只用这一份结果，保证两处字段识别一致。
    """
    standards: dict[str, dict[str, Any]] = {}
    sources: dict[str, dict[str, Any]] = {}
    for row in scoped_aliases(station, batch):
        name = str(row.get("来源名称") or "").strip()
        if not name:
            continue
        sources[name] = {
            "标准字段": row.get("标准字段") or "",
            "核对状态": row.get("status"),
            "核对证据": row.get("核对证据") or "",
            "映射编号": row.get("映射编号"),
        }
        std = str(row.get("标准字段") or "").strip()
        if not std:
            continue  # 新表头尚未指派标准字段，仅登记待核对
        bucket = standards.setdefault(std, {"已确认来源": None, "核对证据": None, "候选来源": []})
        bucket["候选来源"].append({
            "来源名称": name,
            "核对证据": row.get("核对证据") or "",
            "核对状态": row.get("status"),
            "映射编号": row.get("映射编号"),
        })
        if row.get("status") == CONFIRMED and bucket["已确认来源"] is None:
            bucket["已确认来源"] = name
            bucket["核对证据"] = row.get("核对证据") or ""
    return {"采样站": station, "有效批次": batch, "标准字段": standards, "来源登记": sources}


def ingest_headers(station: str, batch: str, headers: list[str]) -> dict[str, Any]:
    """把传感器表头/来源字段名归并进采集字段别名映射数据集。

    只按（采样站， 有效批次， 来源名称）判重：新来源登记为待核对映射，
    已存在的映射（含旧批次、已停用）原样保留，不按文本相等跨站点折叠。
    """
    existing = {
        str(row.get("来源名称") or "").strip()
        for row in scoped_aliases(station, batch, include_retired=True)
    }
    created: list[dict[str, Any]] = []
    kept: list[str] = []
    rows = store.rows(ALIAS_MODULE)
    for header in headers:
        name = str(header).strip()
        if not name:
            continue
        if name in existing:
            kept.append(name)
            continue
        entry = {
            "id": _next_id(ALIAS_MODULE),
            "映射编号": _next_code(ALIAS_MODULE, "ALIAS"),
            "标准字段": "",
            "来源名称": name,
            "采样站": station,
            "有效批次": batch,
            "核对证据": "",
            "核对状态": PENDING,
            "status": PENDING,
            "pending": True,
            "abnormal": False,
        }
        rows.append(entry)
        created.append(entry)
        existing.add(name)
    return {"新登记": created, "已保留": kept}


def headers_of_samples(station: str, batch: str) -> list[str]:
    """读取传感器样本里实际出现的表头（来源字段名），按行号顺序去重。"""
    headers: list[str] = []
    for sample in sample_rows(station, batch):
        for name in sample.get("表头", []):
            name = str(name).strip()
            if name and name not in headers:
                headers.append(name)
    return headers


def sample_rows(station: str, batch: str) -> list[dict[str, Any]]:
    """取某站点某批次的原始样本行，按行号排序；原值只读，不在此处改动。"""
    rows = [
        row for row in store.rows(SAMPLE_MODULE)
        if row.get("采样站") == station and row.get("采集批次") == batch
    ]
    return sorted(rows, key=lambda row: int(row.get("行号", 0)))


def _same_value(left: Any, right: Any) -> bool:
    """数值按数值比，其余按文本比；用于判断两个来源列的读数是否一致。"""
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return str(left) == str(right)


def apply_mapping(station: str, batch: str, readings: dict[str, Any]) -> dict[str, Any]:
    """按共用映射把一行原始读数写成标准字段。

    返回：标准字段值、每个标准字段实际使用的原字段名与核对证据、候选来源冲突、
    未登记来源。只要存在冲突或未登记来源，该行即为尚欠核对。
    """
    resolution = resolve_mapping(station, batch)
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}
    evidence: dict[str, str] = {}
    conflicts: list[dict[str, Any]] = []
    for std, bucket in resolution["标准字段"].items():
        confirmed = bucket["已确认来源"]
        if confirmed is None or confirmed not in readings:
            continue
        values[std] = readings[confirmed]
        sources[std] = confirmed
        evidence[std] = bucket["核对证据"]
        for cand in bucket["候选来源"]:
            name = cand["来源名称"]
            if name == confirmed or name not in readings:
                continue
            if not _same_value(readings[name], readings[confirmed]):
                conflicts.append({
                    "标准字段": std,
                    "已确认来源": confirmed,
                    "已确认值": readings[confirmed],
                    "冲突来源": name,
                    "冲突值": readings[name],
                    "冲突来源证据": cand["核对证据"],
                    "冲突来源状态": cand["核对状态"],
                })
    unregistered = [
        name for name in readings
        if str(name).strip() and name not in resolution["来源登记"]
    ]
    return {
        "标准字段值": values,
        "字段来源": sources,
        "来源证据": evidence,
        "冲突": conflicts,
        "未登记来源": unregistered,
    }
