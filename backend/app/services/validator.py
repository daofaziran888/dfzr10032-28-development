"""采集结果校验业务规则：状态流转、字段校验与筛选口径都收在这里。

批次校验不重新认字段：直接读取格式解析器按采集字段别名映射数据集写出的
标准字段结果（含实际使用的原字段名与候选来源冲突），在同一映射口径下
判定阈值、开立处置单；处置单的有无及依据都能从原始行还原。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "validator"
RESULT_MODULE = "parse_result"
DISPOSAL_MODULE = "disposal"
REQUIRED_FIELDS = ["规则编号", "校验字段", "校验类型"]
STATUS_ORDER = ["草稿", "待测试", "已启用", "已停用"]
ACTION_RULES = {"提交测试": "待测试", "启用规则": "已启用", "停用规则": "已停用"}
NEGATIVE_ACTIONS = ["停用规则"]


class ValidatorService:
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
            rows = [row for row in rows if keyword in str(row.get("规则编号", ""))]
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
            return None, f"校验规则 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于采集结果校验可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"校验规则已{action}"

    def _enabled_threshold_rules(self) -> list[dict[str, Any]]:
        """已启用的阈值上限规则：期望值即阈值（如超温阈值）。"""
        return [
            row for row in store.rows(MODULE)
            if row.get("status") == "已启用" and str(row.get("校验类型")) == "阈值上限"
        ]

    def _parse_results(self, station: str, batch: str) -> list[dict[str, Any]]:
        rows = [
            row for row in store.rows(RESULT_MODULE)
            if row.get("采样站") == station and row.get("采集批次") == batch
        ]
        return sorted(rows, key=lambda row: int(row.get("行号", 0)))

    def validate_batch(self, station: str, batch: str) -> tuple[dict[str, Any] | None, str]:
        """读取解析结果执行批次校验：超阈值即开处置单，冲突行标记尚欠核对。

        同一批次重复校验会覆盖上一次的处置单，保证处置单的有无及依据
        始终能从当前解析结果（也就是同一映射下的原始行）还原。
        """
        station = station.strip()
        batch = batch.strip()
        if not station or not batch:
            return None, "采样站与采集批次都不能为空"
        results = self._parse_results(station, batch)
        if not results:
            return None, f"{station}/{batch} 尚无解析结果，请先在格式解析器运行批次解析"
        rules = self._enabled_threshold_rules()
        table = store.rows(DISPOSAL_MODULE)
        table[:] = [
            row for row in table
            if not (row.get("采样站") == station and row.get("采集批次") == batch)
        ]
        next_id = max((int(row.get("id", 0)) for row in table), default=0) + 1
        issued: list[dict[str, Any]] = []
        for row in results:
            line_no = int(row.get("行号", 0))
            for std, value in row.get("标准字段值", {}).items():
                for rule in rules:
                    if str(rule.get("校验字段")) != std:
                        continue
                    try:
                        threshold = float(rule.get("期望值"))
                        reading = float(value)
                    except (TypeError, ValueError):
                        continue
                    if reading <= threshold:
                        continue
                    source = row.get("字段来源", {}).get(std, "")
                    evidence = row.get("来源证据", {}).get(std, "")
                    conflicts = [c for c in row.get("冲突", []) if c.get("标准字段") == std]
                    order = {
                        "id": next_id,
                        "处置单号": f"DISP-{next_id:04d}",
                        "采样站": station,
                        "采集批次": batch,
                        "行号": line_no,
                        "标准字段": std,
                        "来源字段": source,
                        "字段值": value,
                        "阈值": threshold,
                        "规则编号": rule.get("规则编号"),
                        "判定依据": (
                            f"第{line_no}行标准字段「{std}」取自已确认来源「{source}」"
                            f"（{evidence}），读数{reading}超过阈值{threshold}"
                        ),
                        "冲突证据": conflicts,
                        "状态": "已开立",
                        "status": "已开立",
                        "pending": True,
                        "abnormal": True,
                    }
                    table.append(order)
                    issued.append(order)
                    next_id += 1
        pending_rows = [int(row.get("行号", 0)) for row in results if row.get("核对状态") == "待核对"]
        summary = {
            "采样站": station,
            "采集批次": batch,
            "校验行数": len(results),
            "处置单": [order["处置单号"] for order in issued],
            "处置行号": [int(order["行号"]) for order in issued],
            "尚欠核对行号": pending_rows,
        }
        return summary, f"批次校验完成：开立处置单 {len(issued)} 张，尚欠核对 {len(pending_rows)} 行"

    def validation_detail(self, station: str, batch: str) -> tuple[dict[str, Any] | None, str]:
        """校验明细：逐行给出标准字段值、实际使用的原字段名、冲突与处置单。

        尚欠核对的原始行（候选来源冲突或表头未登记）单独列出，方便核对员追查。
        """
        station = station.strip()
        batch = batch.strip()
        results = self._parse_results(station, batch)
        if not results:
            return None, f"{station}/{batch} 尚无解析结果，请先在格式解析器运行批次解析"
        disposals = self.list_disposals(station, batch)
        by_line: dict[int, list[dict[str, Any]]] = {}
        for order in disposals:
            by_line.setdefault(int(order.get("行号", 0)), []).append(order)
        lines = []
        for row in results:
            line_no = int(row.get("行号", 0))
            lines.append({
                "行号": line_no,
                "标准字段值": row.get("标准字段值", {}),
                "字段来源": row.get("字段来源", {}),
                "来源证据": row.get("来源证据", {}),
                "冲突": row.get("冲突", []),
                "未登记来源": row.get("未登记来源", []),
                "核对状态": row.get("核对状态"),
                "处置单": by_line.get(line_no, []),
            })
        detail = {
            "采样站": station,
            "采集批次": batch,
            "行明细": lines,
            "尚欠核对行号": [line["行号"] for line in lines if line["核对状态"] == "待核对"],
            "处置单": disposals,
        }
        return detail, "ok"

    def list_disposals(self, station: str | None = None, batch: str | None = None) -> list[dict[str, Any]]:
        """查询处置单：可按站点与批次过滤。"""
        rows = store.rows(DISPOSAL_MODULE)
        if station:
            rows = [row for row in rows if row.get("采样站") == station]
        if batch:
            rows = [row for row in rows if row.get("采集批次") == batch]
        return sorted(rows, key=lambda row: int(row.get("id", 0)))
