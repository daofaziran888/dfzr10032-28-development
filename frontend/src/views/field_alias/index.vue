<template>
  <section class="page" data-module="field_alias">
    <header class="page-head">
      <div>
        <h2>采集字段别名映射</h2>
        <p class="page-desc">按采样站与有效批次登记标准字段的来源名称与核对证据；新表头只归并为待核对，旧映射不按文本相等折叠。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记别名映射</button>
        <button class="btn" type="button" @click="openIngest">读入传感器表头</button>
        <button class="btn" type="button" @click="exportRows">导出别名映射清单</button>
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
          <td v-for="column in columns" :key="column">{{ row[column] || '—' }}</td>
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
          <td :colspan="columns.length + 1" class="empty-state">暂无别名映射数据，可先登记映射或读入传感器表头</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条别名映射记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <section class="panel">
      <header class="panel-head">
        <h3>有效映射查看（与解析器、校验同一份解析）</h3>
      </header>
      <form class="filter-bar" @submit.prevent="loadResolve">
        <label class="filter-item">
          <span>采样站</span>
          <input v-model="resolveForm.采样站" placeholder="如：河口站" />
        </label>
        <label class="filter-item">
          <span>有效批次</span>
          <input v-model="resolveForm.有效批次" placeholder="如：BATCH-2026-1101" />
        </label>
        <button class="btn" type="submit">查看有效映射</button>
      </form>
      <table v-if="resolveRows.length" class="data-table">
        <thead>
          <tr>
            <th>标准字段</th>
            <th>已确认来源</th>
            <th>核对证据</th>
            <th>候选来源（含待核对）</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in resolveRows" :key="row.标准字段">
            <td>{{ row.标准字段 }}</td>
            <td>{{ row.已确认来源 || '—' }}</td>
            <td>{{ row.核对证据 || '—' }}</td>
            <td>{{ row.候选来源 }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty-state">输入采样站与有效批次后查看该作用域下的有效映射</p>
      <table v-if="sourceRows.length" class="data-table">
        <thead>
          <tr>
            <th>来源名称</th>
            <th>标准字段</th>
            <th>核对状态</th>
            <th>核对证据</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sourceRows" :key="row.来源名称">
            <td>{{ row.来源名称 }}</td>
            <td>{{ row.标准字段 || '—（未指派）' }}</td>
            <td>{{ row.核对状态 }}</td>
            <td>{{ row.核对证据 || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <Teleport to="body">
      <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
        <div class="modal-card">
          <header class="modal-head">
            <h3>登记别名映射</h3>
            <button class="btn ghost" type="button" @click="showCreateModal = false">&times;</button>
          </header>
          <form class="modal-body" @submit.prevent="submitCreate">
            <label v-for="field in createFieldList" :key="field" class="modal-field">
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

    <Teleport to="body">
      <div v-if="showIngestModal" class="modal-overlay" @click.self="showIngestModal = false">
        <div class="modal-card">
          <header class="modal-head">
            <h3>读入传感器表头</h3>
            <button class="btn ghost" type="button" @click="showIngestModal = false">&times;</button>
          </header>
          <form class="modal-body" @submit.prevent="submitIngest">
            <label class="modal-field">
              <span>采样站</span>
              <input v-model="ingestForm.采样站" placeholder="如：河口站" required />
            </label>
            <label class="modal-field">
              <span>有效批次</span>
              <input v-model="ingestForm.有效批次" placeholder="如：BATCH-2026-1102" required />
            </label>
            <label class="modal-field">
              <span>表头（逗号分隔，留空则从该批次样本读取）</span>
              <input v-model="ingestForm.表头" placeholder="如：水温,河水温度,浊度" />
            </label>
            <p v-if="ingestMessage" class="panel-note">{{ ingestMessage }}</p>
            <footer class="modal-foot">
              <button class="btn" type="button" @click="showIngestModal = false">取消</button>
              <button class="btn primary" type="submit">归并表头</button>
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

const ENDPOINT = '/api/field_alias'
const columns = ["映射编号", "标准字段", "来源名称", "采样站", "有效批次", "核对证据", "核对状态"]
const actions = ["确认映射", "停用映射"]
const statuses = ["待核对", "已确认", "已停用"]
const stats = [{"label": "映射总数", "value": 0}, {"label": "已确认映射", "value": 0}, {"label": "待核对来源", "value": 0}]
const createFieldList = ["标准字段", "来源名称", "采样站", "有效批次", "核对证据"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = ["来源名称", "采样站", "有效批次"]
const showCreateModal = ref(false)
const createFields = ref<Record<string, string>>({})
const showIngestModal = ref(false)
const ingestForm = ref<Record<string, string>>({ 采样站: '', 有效批次: '', 表头: '' })
const ingestMessage = ref('')
const resolveForm = ref<Record<string, string>>({ 采样站: '', 有效批次: '' })
const resolveRows = ref<Row[]>([])
const sourceRows = ref<Row[]>([])

function updateStats() {
  const data = rows.value
  stats.length > 0 && (stats[0].value = data.length)
  stats.length > 1 && (stats[1].value = data.filter((r: Row) => r.status === statuses[1]).length)
  stats.length > 2 && (stats[2].value = data.filter((r: Row) => r.status === statuses[0]).length)
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

function openIngest() {
  errorMessage.value = ''
  ingestMessage.value = ''
  ingestForm.value = { 采样站: '', 有效批次: '', 表头: '' }
  showIngestModal.value = true
}

async function submitCreate() {
  errorMessage.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: createFields.value }),
    })
    const data = await response.json()
    if (!response.ok || !data.ok) {
      throw new Error(data.message || '登记失败')
    }
    showCreateModal.value = false
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登记失败'
  }
}

async function submitIngest() {
  errorMessage.value = ''
  ingestMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/ingest`, {
      method: 'POST',
      body: JSON.stringify({ values: ingestForm.value }),
    })
    const data = await response.json()
    if (!response.ok || !data.ok) {
      throw new Error(data.message || '表头归并失败')
    }
    ingestMessage.value = data.message
    await reload()
  } catch (error) {
    ingestMessage.value = error instanceof Error ? error.message : '表头归并失败'
  }
}

async function loadResolve() {
  errorMessage.value = ''
  resolveRows.value = []
  sourceRows.value = []
  const query = new URLSearchParams({
    采样站: resolveForm.value.采样站 || '',
    有效批次: resolveForm.value.有效批次 || '',
  }).toString()
  try {
    const response = await request(`${ENDPOINT}/resolve?${query}`)
    if (!response.ok) {
      throw new Error('有效映射读取失败')
    }
    const payload = await response.json()
    resolveRows.value = Object.entries(payload['标准字段'] ?? {}).map(([std, bucket]: [string, any]) => ({
      标准字段: std,
      已确认来源: bucket['已确认来源'],
      核对证据: bucket['核对证据'],
      候选来源: (bucket['候选来源'] ?? [])
        .map((cand: any) => `${cand['来源名称']}（${cand['核对状态']}）`)
        .join('、'),
    }))
    sourceRows.value = Object.entries(payload['来源登记'] ?? {}).map(([name, info]: [string, any]) => ({
      来源名称: name,
      标准字段: info['标准字段'],
      核对状态: info['核对状态'],
      核对证据: info['核对证据'],
    }))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '有效映射读取失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const data = await response.json()
    if (!response.ok || !data.ok) {
      throw new Error(data.message || '别名映射动作未生效')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '别名映射操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('别名映射列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    updateStats()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '别名映射列表读取失败'
  }
}

onMounted(reload)
</script>
