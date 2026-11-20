<template>
  <section class="page" data-module="validator">
    <header class="page-head">
      <div>
        <h2>采集结果校验管理</h2>
        <p class="page-desc">维护校验规则，围绕规则编号、校验字段、校验类型、期望值做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记校验规则</button>
        <button class="btn" type="button" @click="openValidate">执行批次校验</button>
        <button class="btn" type="button" @click="exportRows">导出采集结果校验清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无采集结果校验数据，可先登记校验规则</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条采集结果校验记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <section class="panel">
      <header class="panel-head">
        <h3>批次校验明细（与解析器同一份映射，可见实际使用的原字段名）</h3>
      </header>
      <form class="filter-bar" @submit.prevent="loadDetail">
        <label class="filter-item">
          <span>采样站</span>
          <input v-model="detailFilter.采样站" placeholder="如：河口站" />
        </label>
        <label class="filter-item">
          <span>采集批次</span>
          <input v-model="detailFilter.采集批次" placeholder="如：BATCH-2026-1101" />
        </label>
        <button class="btn" type="submit">查询校验明细</button>
      </form>
      <p v-if="validateMessage" class="panel-note">{{ validateMessage }}</p>
      <p v-if="pendingLines.length" class="panel-note">尚欠核对的原始行：第 {{ pendingLines.join('、') }} 行</p>
      <table v-if="detailRows.length" class="data-table">
        <thead>
          <tr>
            <th>行号</th>
            <th>标准字段值</th>
            <th>实际使用原字段名</th>
            <th>候选来源冲突</th>
            <th>核对状态</th>
            <th>处置单</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in detailRows" :key="String(row['行号'])" :class="{ 'row-warn': row['核对状态'] === '待核对' }">
            <td>{{ row['行号'] }}</td>
            <td>{{ formatValues(row['标准字段值']) }}</td>
            <td>{{ formatSources(row['字段来源']) }}</td>
            <td>{{ formatConflicts(row['冲突']) || '—' }}</td>
            <td>{{ row['核对状态'] }}</td>
            <td>{{ formatOrders(row['处置单']) || '—' }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-state">暂无校验明细，请先在格式解析器运行批次解析再执行批次校验</p>
      <table v-if="disposalRows.length" class="data-table">
        <thead>
          <tr>
            <th>处置单号</th>
            <th>行号</th>
            <th>标准字段</th>
            <th>来源字段</th>
            <th>字段值</th>
            <th>阈值</th>
            <th>判定依据</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in disposalRows" :key="String(order.id)">
            <td>{{ order['处置单号'] }}</td>
            <td>{{ order['行号'] }}</td>
            <td>{{ order['标准字段'] }}</td>
            <td>{{ order['来源字段'] }}</td>
            <td>{{ order['字段值'] }}</td>
            <td>{{ order['阈值'] }}</td>
            <td>{{ order['判定依据'] }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <Teleport to="body">
      <div v-if="showValidateModal" class="modal-overlay" @click.self="showValidateModal = false">
        <div class="modal-card">
          <header class="modal-head">
            <h3>执行批次校验</h3>
            <button class="btn ghost" type="button" @click="showValidateModal = false">&times;</button>
          </header>
          <form class="modal-body" @submit.prevent="submitValidate">
            <label class="modal-field">
              <span>采样站</span>
              <input v-model="validateForm.采样站" placeholder="如：河口站" required />
            </label>
            <label class="modal-field">
              <span>采集批次</span>
              <input v-model="validateForm.采集批次" placeholder="如：BATCH-2026-1101" required />
            </label>
            <footer class="modal-foot">
              <button class="btn" type="button" @click="showValidateModal = false">取消</button>
              <button class="btn primary" type="submit">开始校验</button>
            </footer>
          </form>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
        <div class="modal-card">
          <header class="modal-head">
            <h3>登记校验规则</h3>
            <button class="btn ghost" type="button" @click="showCreateModal = false">&times;</button>
          </header>
          <form class="modal-body" @submit.prevent="submitCreate">
            <label v-for="field in columns.slice(0, 3)" :key="field" class="modal-field">
              <span>{{ field }}</span>
              <input v-model="createFields[field]" :placeholder="`请输入${field}`" required />
            </label>
            <footer class="modal-foot">
              <button class="btn" type="button" @click="showCreateModal = false">取消</button>
              <button class="btn primary" type="submit">提交登记</button>
            </footer>
          </form>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, any>

const ENDPOINT = '/api/validator'
const columns = ["规则编号", "校验字段", "校验类型", "期望值", "容错范围", "采样比例", "阻断级别", "规则状态"]
const actions = ["提交测试", "启用规则", "停用规则"]
const statuses = ["草稿", "待测试", "已启用", "已停用"]
const stats = [{"label": "规则总数", "value": 0}, {"label": "已启用规则", "value": 0}, {"label": "待测试规则", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const showCreateModal = ref(false)
const createFields = ref<Record<string, string>>({})
const showValidateModal = ref(false)
const validateForm = ref<Record<string, string>>({ 采样站: '', 采集批次: '' })
const detailFilter = ref<Record<string, string>>({ 采样站: '', 采集批次: '' })
const detailRows = ref<Row[]>([])
const disposalRows = ref<Row[]>([])
const pendingLines = ref<number[]>([])
const validateMessage = ref('')

function formatValues(values: Record<string, unknown> | undefined): string {
  return Object.entries(values ?? {}).map(([key, val]) => `${key}=${String(val)}`).join('，')
}

function formatSources(sources: Record<string, unknown> | undefined): string {
  return Object.entries(sources ?? {}).map(([key, val]) => `${key}←${String(val)}`).join('，')
}

function formatConflicts(conflicts: Array<Record<string, unknown>> | undefined): string {
  return (conflicts ?? [])
    .map((item) => `${String(item['标准字段'])}：${String(item['冲突来源'])}=${String(item['冲突值'])} ≠ ${String(item['已确认来源'])}=${String(item['已确认值'])}`)
    .join('；')
}

function formatOrders(orders: Array<Record<string, unknown>> | undefined): string {
  return (orders ?? []).map((order) => String(order['处置单号'])).join('、')
}

function openValidate() {
  errorMessage.value = ''
  validateForm.value = { 采样站: '', 采集批次: '' }
  showValidateModal.value = true
}

async function submitValidate() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/validate`, {
      method: 'POST',
      body: JSON.stringify({ values: validateForm.value }),
    })
    const data = await response.json()
    if (!response.ok || !data.ok) {
      throw new Error(data.message || '批次校验失败')
    }
    validateMessage.value = data.message
    detailFilter.value = { ...validateForm.value }
    showValidateModal.value = false
    await loadDetail()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '批次校验失败'
  }
}

async function loadDetail() {
  errorMessage.value = ''
  detailRows.value = []
  disposalRows.value = []
  pendingLines.value = []
  const query = new URLSearchParams({
    采样站: detailFilter.value.采样站 || '',
    采集批次: detailFilter.value.采集批次 || '',
  }).toString()
  try {
    const response = await request(`${ENDPOINT}/detail?${query}`)
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || '校验明细读取失败')
    }
    const payload = await response.json()
    detailRows.value = payload['行明细'] ?? []
    disposalRows.value = payload['处置单'] ?? []
    pendingLines.value = payload['尚欠核对行号'] ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '校验明细读取失败'
  }
}

function updateStats() {
  const data = rows.value
  stats.length > 0 && (stats[0].value = data.filter((r: Row) => r.status === statuses[1] || r.pending).length)
  stats.length > 1 && (stats[1].value = data.filter((r: Row) => r.status && !r.pending && !r.abnormal).length)
  stats.length > 2 && (stats[2].value = data.filter((r: Row) => r.abnormal).length)
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = ''
  createFields.value = {}
  showCreateModal.value = true
}

async function submitCreate() {
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: createFields.value }),
    })
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.message || '登记失败')
    }
    showCreateModal.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登记失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      throw new Error('采集结果校验动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '采集结果校验操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('校验规则列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    updateStats()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '采集结果校验列表读取失败'
  }
}

onMounted(reload)
</script>
