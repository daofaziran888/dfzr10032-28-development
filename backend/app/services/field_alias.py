"""采集字段别名映射业务规则：数据集登记、表头归并与状态流转都收在这里。"""
from __future__ import annotations

from typing import Any

from app.services import field_mapping
from app.store import store

MODULE = "field_alias"
REQUIRED_FIELDS = ["标准字段", "来源名称", "采样站", "有效批次", "核对证据"]
STATUS_ORDER = ["待核对", "已确认", "已停用"]
ACTION_RULES = {"确认映射": "已确认", "停用映射": "已停用"}
NEGATIVE_ACTIONS = ["停用映射"]


class FieldAliasService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
        extra: dict[str, str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("映射编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if extra:
            for field, val in extra.items():
                rows = [row for row in rows if val in str(row.get(field, ""))]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["映射编号"] = str(values.get("映射编号") or "").strip() or f"ALIAS-{entry['id']:04d}"
        entry["status"] = STATUS_ORDER[0]
        entry["核对状态"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"别名映射 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于采集字段别名映射可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        if target == "已确认" and not str(entry.get("标准字段") or "").strip():
            return None, "尚未指派标准字段的来源不能确认，请先补全标准字段"
        entry["status"] = target
        entry["核对状态"] = target
        entry["pending"] = target == STATUS_ORDER[0]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"别名映射已{action}"

    def ingest_headers(
        self,
        station: str,
        batch: str,
        headers: list[str] | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        """读取传感器表头与来源字段名，归并进采集字段别名映射数据集。

        未显式给出表头时，从该站点该批次的传感器样本里读取实际表头。
        """
        station = station.strip()
        batch = batch.strip()
        if not station or not batch:
            return None, "采样站与有效批次都不能为空"
        names = [str(name).strip() for name in (headers or []) if str(name).strip()]
        if not names:
            names = field_mapping.headers_of_samples(station, batch)
        if not names:
            return None, f"{station}/{batch} 没有可读入的传感器表头"
        result = field_mapping.ingest_headers(station, batch, names)
        created = len(result["新登记"])
        kept = len(result["已保留"])
        message = f"已归并 {created} 个新来源（待核对），保留既有映射 {kept} 个"
        result["采样站"] = station
        result["有效批次"] = batch
        return result, message

    def resolve(self, station: str, batch: str) -> dict[str, Any]:
        """查看某站点某批次的有效映射：与解析器、校验共用同一份解析结果。"""
        return field_mapping.resolve_mapping(station.strip(), batch.strip())
