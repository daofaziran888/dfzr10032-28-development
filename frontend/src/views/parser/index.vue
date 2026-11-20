<template>
  <section class="page" data-module="parser">
    <header class="page-head">
      <div>
        <h2>格式解析器管理</h2>
        <p class="page-desc">维护解析配置，围绕解析编号、输入格式、输出格式、字段映射做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记解析配置</button>
        <button class="btn" type="button" @click="openParse">运行批次解析</button>
        <button class="btn" type="button" @click="exportRows">导出格式解析器清单</button>
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
          <td :colspan="columns.length + 1" class="empty-state">暂无格式解析器数据，可先登记解析配置</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条格式解析器记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <section class="panel">
      <header class="panel-head">
        <h3>批次解析结果（按采集字段别名映射写出标准字段）</h3>
      </header>
      <form class="filter-bar" @submit.prevent="loadResults">
        <label class="filter-item">
          <span>采样站</span>
          <input v-model="resultFilter.采样站" placeholder="如：河口站" />
        </label>
        <label class="filter-item">
          <span>采集批次</span>
          <input v-model="resultFilter.采集批次" placeholder="如：BATCH-2026-1101" />
        </label>
        <button class="btn" type="submit">查询解析结果</button>
        <button class="btn ghost" type="button" @click="loadSamples">查看原始样本</button>
      </form>
      <p v-if="parseMessage" class="panel-note">{{ parseMessage }}</p>
      <table v-if="resultRows.length" class="data-table">
        <thead>
          <tr>
            <th>行号</th>
            <th>标准字段值</th>
            <th>实际使用原字段名</th>
            <th>候选来源冲突</th>
            <th>核对状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in resultRows" :key="String(row.id)" :class="{ 'row-warn': row['核对状态'] === '待核对' }">
            <td>{{ row['行号'] }}</td>
            <td>{{ formatValues(row['标准字段值']) }}</td>
            <td>{{ formatSources(row['字段来源']) }}</td>
            <td>{{ formatConflicts(row['冲突']) || '—' }}</td>
            <td>{{ row['核对状态'] }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-state">暂无解析结果，可先运行批次解析</p>
      <table v-if="sampleRows.length" class="data-table">
        <thead>
          <tr>
            <th>行号</th>
            <th>表头</th>
            <th>原始读数</th>
            <th>采样时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sampleRows" :key="String(row.id)">
            <td>{{ row['行号'] }}</td>
            <td>{{ (row['表头'] ?? []).join('、') }}</td>
            <td>{{ formatValues(row['读数']) }}</td>
            <td>{{ row['采样时间'] }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <Teleport to="body">
      <div v-if="showParseModal" class="modal-overlay" @click.self="showParseModal = false">
        <div class="modal-card">
          <header class="modal-head">
            <h3>运行批次解析</h3>
            <button class="btn ghost" type="button" @click="showParseModal = false">&times;</button>
          </header>
          <form class="modal-body" @submit.prevent="submitParse">
            <label class="modal-field">
              <span>采样站</span>
              <input v-model="parseForm.采样站" placeholder="如：河口站" required />
            </label>
            <label class="modal-field">
              <span>采集批次</span>
              <input v-model="parseForm.采集批次" placeholder="如：BATCH-2026-1101" required />
            </label>
            <footer class="modal-foot">
              <button class="btn" type="button" @click="showParseModal = false">取消</button>
              <button class="btn primary" type="submit">开始解析</button>
            </footer>
          </form>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
        <div class="modal-card">
          <header class="modal-head">
            <h3>登记解析配置</h3>
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

const ENDPOINT = '/api/parser'
const columns = ["解析编号", "输入格式", "输出格式", "字段映射", "类型转换", "空值处理", "异常策略", "解析状态"]
const actions = ["提交配置", "启用解析", "废弃解析"]
const statuses = ["草稿", "已配置", "生效中", "已废弃"]
const stats = [{"label": "解析器总数", "value": 0}, {"label": "生效中解析器", "value": 0}, {"label": "已废弃解析器", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const showCreateModal = ref(false)
const createFields = ref<Record<string, string>>({})
const showParseModal = ref(false)
const parseForm = ref<Record<string, string>>({ 采样站: '', 采集批次: '' })
const resultFilter = ref<Record<string, string>>({ 采样站: '', 采集批次: '' })
const resultRows = ref<Row[]>([])
const sampleRows = ref<Row[]>([])
const parseMessage = ref('')

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

function openParse() {
  errorMessage.value = ''
  parseForm.value = { 采样站: '', 采集批次: '' }
  showParseModal.value = true
}

async function submitParse() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/parse`, {
      method: 'POST',
      body: JSON.stringify({ values: parseForm.value }),
    })
    const data = await response.json()
    if (!response.ok || !data.ok) {
      throw new Error(data.message || '批次解析失败')
    }
    parseMessage.value = data.message
    resultFilter.value = { ...parseForm.value }
    showParseModal.value = false
    await loadResults()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '批次解析失败'
  }
}

async function loadResults() {
  errorMessage.value = ''
  sampleRows.value = []
  const query = new URLSearchParams({
    采样站: resultFilter.value.采样站 || '',
    采集批次: resultFilter.value.采集批次 || '',
  }).toString()
  try {
    const response = await request(`${ENDPOINT}/results?${query}`)
    if (!response.ok) {
      throw new Error('解析结果读取失败')
    }
    const payload = await response.json()
    resultRows.value = payload.items ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '解析结果读取失败'
  }
}

async function loadSamples() {
  errorMessage.value = ''
  const query = new URLSearchParams({
    采样站: resultFilter.value.采样站 || '',
    采集批次: resultFilter.value.采集批次 || '',
  }).toString()
  try {
    const response = await request(`${ENDPOINT}/samples?${query}`)
    if (!response.ok) {
      throw new Error('原始样本读取失败')
    }
    const payload = await response.json()
    sampleRows.value = payload.items ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '原始样本读取失败'
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
      throw new Error('格式解析器动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '格式解析器操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('解析配置列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    updateStats()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '格式解析器列表读取失败'
  }
}

onMounted(reload)
</script>
