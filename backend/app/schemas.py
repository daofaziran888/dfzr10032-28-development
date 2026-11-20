"""接口出入参模型：列表分页、动作结果与各模块的明细结构。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    size: int = 20


class ActionResult(BaseModel):
    ok: bool
    message: str
    entry: dict[str, Any] | None = None


class EntryPayload(BaseModel):
    """登记或修改一条业务记录时提交的字段集合。"""

    values: dict[str, Any] = Field(default_factory=dict)
    remark: str | None = None



class DatasourceEntry(BaseModel):
    """数据源明细结构。"""

    field_0: str | None = None  # 源端编号
    field_1: str | None = None  # 连接类型
    field_2: str | None = None  # 接入地址
    field_3: str | None = None  # 认证方式
    field_4: str | None = None  # 采样周期
    field_5: str | None = None  # 超时秒数
    field_6: str | None = None  # 重试上限
    field_7: str | None = None  # 负责人

class CrawlerEntry(BaseModel):
    """采集规则明细结构。"""

    field_0: str | None = None  # 规则编号
    field_1: str | None = None  # 目标网址
    field_2: str | None = None  # 页面选择器
    field_3: str | None = None  # 正文选择器
    field_4: str | None = None  # 翻页参数
    field_5: str | None = None  # 抓取频率
    field_6: str | None = None  # 字符编码
    field_7: str | None = None  # 去重策略

class ApiclientEntry(BaseModel):
    """API客户端明细结构。"""

    field_0: str | None = None  # 客户端编号
    field_1: str | None = None  # 接口名称
    field_2: str | None = None  # 请求方法
    field_3: str | None = None  # 认证凭证
    field_4: str | None = None  # 限流令牌
    field_5: str | None = None  # 重试策略
    field_6: str | None = None  # 超时配置
    field_7: str | None = None  # 启用状态

class IncrementalEntry(BaseModel):
    """增量游标明细结构。"""

    field_0: str | None = None  # 游标编号
    field_1: str | None = None  # 来源标识
    field_2: str | None = None  # 增量字段
    field_3: str | None = None  # 当前水位
    field_4: str | None = None  # 批次大小
    field_5: str | None = None  # 采集间隔
    field_6: str | None = None  # 上次采集
    field_7: str | None = None  # 下次采集

class RobotTaskEntry(BaseModel):
    """RPA任务明细结构。"""

    field_0: str | None = None  # 任务编号
    field_1: str | None = None  # 任务名称
    field_2: str | None = None  # 页面定位器
    field_3: str | None = None  # 动作序列
    field_4: str | None = None  # 等待条件
    field_5: str | None = None  # 结果字段
    field_6: str | None = None  # 超时秒数
    field_7: str | None = None  # 执行批次

class IngestionEntry(BaseModel):
    """接入通道明细结构。"""

    field_0: str | None = None  # 通道编号
    field_1: str | None = None  # 通道名称
    field_2: str | None = None  # 输入格式
    field_3: str | None = None  # 解析引擎
    field_4: str | None = None  # 并发数量
    field_5: str | None = None  # 背压阈值
    field_6: str | None = None  # 缓冲队列
    field_7: str | None = None  # 通道状态

class ParserEntry(BaseModel):
    """解析配置明细结构。"""

    field_0: str | None = None  # 解析编号
    field_1: str | None = None  # 输入格式
    field_2: str | None = None  # 输出格式
    field_3: str | None = None  # 字段映射
    field_4: str | None = None  # 类型转换
    field_5: str | None = None  # 空值处理
    field_6: str | None = None  # 异常策略
    field_7: str | None = None  # 解析状态

class ValidatorEntry(BaseModel):
    """校验规则明细结构。"""

    field_0: str | None = None  # 规则编号
    field_1: str | None = None  # 校验字段
    field_2: str | None = None  # 校验类型
    field_3: str | None = None  # 期望值
    field_4: str | None = None  # 容错范围
    field_5: str | None = None  # 采样比例
    field_6: str | None = None  # 阻断级别
    field_7: str | None = None  # 规则状态

class FieldAliasEntry(BaseModel):
    """别名映射明细结构。"""

    field_0: str | None = None  # 映射编号
    field_1: str | None = None  # 标准字段
    field_2: str | None = None  # 来源名称
    field_3: str | None = None  # 采样站
    field_4: str | None = None  # 有效批次
    field_5: str | None = None  # 核对证据
    field_6: str | None = None  # 核对状态

class DedupEntry(BaseModel):
    """去重策略明细结构。"""

    field_0: str | None = None  # 策略编号
    field_1: str | None = None  # 输入来源
    field_2: str | None = None  # 去重键
    field_3: str | None = None  # 排序字段
    field_4: str | None = None  # 保留策略
    field_5: str | None = None  # 时间窗口
    field_6: str | None = None  # 重复阈值
    field_7: str | None = None  # 策略状态

class ScheduleEntry(BaseModel):
    """调度计划明细结构。"""

    field_0: str | None = None  # 计划编号
    field_1: str | None = None  # 关联任务
    field_2: str | None = None  # 调度周期
    field_3: str | None = None  # 开始时间
    field_4: str | None = None  # 结束时间
    field_5: str | None = None  # 依赖任务
    field_6: str | None = None  # 失败策略
    field_7: str | None = None  # 计划状态

class MonitorEntry(BaseModel):
    """监控面板明细结构。"""

    field_0: str | None = None  # 面板编号
    field_1: str | None = None  # 采集源总数
    field_2: str | None = None  # 今日采集量
    field_3: str | None = None  # 成功率
    field_4: str | None = None  # 平均延迟
    field_5: str | None = None  # 失败重试
    field_6: str | None = None  # 异常告警
    field_7: str | None = None  # 更新时间

class LogViewerEntry(BaseModel):
    """日志条目明细结构。"""

    field_0: str | None = None  # 日志编号
    field_1: str | None = None  # 关联任务
    field_2: str | None = None  # 日志级别
    field_3: str | None = None  # 记录时间
    field_4: str | None = None  # 日志内容
    field_5: str | None = None  # 错误堆栈
    field_6: str | None = None  # 处理状态
    field_7: str | None = None  # 处理人

class AuthEntry(BaseModel):
    """认证凭证明细结构。"""

    field_0: str | None = None  # 凭证编号
    field_1: str | None = None  # 凭证类型
    field_2: str | None = None  # 关联数据源
    field_3: str | None = None  # 凭证内容
    field_4: str | None = None  # 有效期至
    field_5: str | None = None  # 创建时间
    field_6: str | None = None  # 最后使用
    field_7: str | None = None  # 凭证状态

class TransformEntry(BaseModel):
    """转换节点明细结构。"""

    field_0: str | None = None  # 节点编号
    field_1: str | None = None  # 输入来源
    field_2: str | None = None  # 输出目标
    field_3: str | None = None  # 转换表达式
    field_4: str | None = None  # 执行顺序
    field_5: str | None = None  # 依赖节点
    field_6: str | None = None  # 失败策略
    field_7: str | None = None  # 节点状态

class FlowEntry(BaseModel):
    """流转管道明细结构。"""

    field_0: str | None = None  # 管道编号
    field_1: str | None = None  # 管道名称
    field_2: str | None = None  # 起始节点
    field_3: str | None = None  # 终止节点
    field_4: str | None = None  # 中间节点
    field_5: str | None = None  # 流转条件
    field_6: str | None = None  # 并行数量
    field_7: str | None = None  # 管道状态

class LineageEntry(BaseModel):
    """血缘关系明细结构。"""

    field_0: str | None = None  # 关系编号
    field_1: str | None = None  # 上游节点
    field_2: str | None = None  # 下游节点
    field_3: str | None = None  # 来源字段
    field_4: str | None = None  # 目标字段
    field_5: str | None = None  # 转换说明
    field_6: str | None = None  # 采集批次
    field_7: str | None = None  # 关系版本

class ReportEntry(BaseModel):
    """采集报告明细结构。"""

    field_0: str | None = None  # 报告编号
    field_1: str | None = None  # 采集源
    field_2: str | None = None  # 统计周期
    field_3: str | None = None  # 总采集量
    field_4: str | None = None  # 成功量
    field_5: str | None = None  # 失败量
    field_6: str | None = None  # 平均耗秒
    field_7: str | None = None  # 生成时间
