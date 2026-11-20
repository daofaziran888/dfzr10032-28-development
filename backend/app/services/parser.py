"""格式解析器业务规则：状态流转、字段校验与筛选口径都收在这里。

批次解析不再各自认字段，统一走 app.services.field_mapping 的共用映射解析：
按采集字段别名映射数据集把传感器原值写成标准字段，并记录每个标准字段
实际使用的原字段名与核对证据，供采集结果校验读取同一份结果。
"""
from __future__ import annotations

from typing import Any

from app.services import field_mapping
from app.store import store

MODULE = "parser"
RESULT_MODULE = "parse_result"
REQUIRED_FIELDS = ["解析编号", "输入格式", "输出格式"]
STATUS_ORDER = ["草稿", "已配置", "生效中", "已废弃"]
ACTION_RULES = {"提交配置": "已配置", "启用解析": "生效中", "废弃解析": "已废弃"}
NEGATIVE_ACTIONS = []


class ParserService:
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
            rows = [row for row in rows if keyword in str(row.get("解析编号", ""))]
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
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"解析配置 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于格式解析器可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"解析配置已{action}"

    def parse_batch(self, station: str, batch: str) -> tuple[dict[str, Any] | None, str]:
        """按采集字段别名映射数据集解析一个采集批次，写出标准字段。

        同一批次重复解析会覆盖上一次的解析结果，保证结果可重放；
        原始样本只读，新表头的原值始终可查。
        """
        station = station.strip()
        batch = batch.strip()
        if not station or not batch:
            return None, "采样站与采集批次都不能为空"
        samples = field_mapping.sample_rows(station, batch)
        if not samples:
            return None, f"{station}/{batch} 没有可解析的传感器样本"
        table = store.rows(RESULT_MODULE)
        table[:] = [
            row for row in table
            if not (row.get("采样站") == station and row.get("采集批次") == batch)
        ]
        next_id = max((int(row.get("id", 0)) for row in table), default=0) + 1
        pending_rows: list[int] = []
        conflict_rows: list[int] = []
        unregistered: list[str] = []
        for sample in samples:
            mapped = field_mapping.apply_mapping(station, batch, sample.get("读数", {}))
            line_no = int(sample.get("行号", 0))
            needs_check = bool(mapped["冲突"] or mapped["未登记来源"])
            if needs_check:
                pending_rows.append(line_no)
            if mapped["冲突"]:
                conflict_rows.append(line_no)
            for name in mapped["未登记来源"]:
                if name not in unregistered:
                    unregistered.append(name)
            table.append({
                "id": next_id,
                "采样站": station,
                "采集批次": batch,
                "行号": line_no,
                "标准字段值": mapped["标准字段值"],
                "字段来源": mapped["字段来源"],
                "来源证据": mapped["来源证据"],
                "冲突": mapped["冲突"],
                "未登记来源": mapped["未登记来源"],
                "核对状态": "待核对" if needs_check else "已核对",
                "status": "已解析",
                "pending": needs_check,
                "abnormal": bool(mapped["冲突"]),
            })
            next_id += 1
        summary = {
            "采样站": station,
            "采集批次": batch,
            "解析行数": len(samples),
            "待核对行号": pending_rows,
            "冲突行号": conflict_rows,
            "未登记来源": unregistered,
        }
        return summary, f"批次解析完成：{len(samples)} 行，尚欠核对 {len(pending_rows)} 行"

    def list_results(self, station: str | None = None, batch: str | None = None) -> list[dict[str, Any]]:
        """查询解析结果：标准字段值与实际使用的原字段名一并返回。"""
        rows = store.rows(RESULT_MODULE)
        if station:
            rows = [row for row in rows if row.get("采样站") == station]
        if batch:
            rows = [row for row in rows if row.get("采集批次") == batch]
        return sorted(rows, key=lambda row: (str(row.get("采集批次")), int(row.get("行号", 0))))

    def list_samples(self, station: str | None = None, batch: str | None = None) -> list[dict[str, Any]]:
        """查询传感器原始样本：新表头的原值在这里始终可查。"""
        rows = store.rows(field_mapping.SAMPLE_MODULE)
        if station:
            rows = [row for row in rows if row.get("采样站") == station]
        if batch:
            rows = [row for row in rows if row.get("采集批次") == batch]
        return sorted(rows, key=lambda row: (str(row.get("采集批次")), int(row.get("行号", 0))))
