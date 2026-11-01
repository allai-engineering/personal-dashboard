import {combinedAccounts} from './sources.mjs';
export const numeric = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
export const number = value => numeric(value) ? new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 1}).format(value) : '—';
export const tokens = value => numeric(value) ? new Intl.NumberFormat('ru-RU', {notation: 'compact', maximumFractionDigits: 1}).format(value) : '—';
export const percent = value => numeric(value) ? new Intl.NumberFormat('ru-RU', {style: 'percent', maximumFractionDigits: 2}).format(value) : '—';
export const latency = value => numeric(value) ? (value >= 1000 ? number(value / 1000) + ' с' : number(value) + ' мс') : '—';
export const clock = value => Number.isFinite(Date.parse(value)) ? new Intl.DateTimeFormat('ru-RU', {timeZone: 'UTC', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'}).format(new Date(value)) + ' UTC' : 'Время неизвестно';

export const stateLabels = {enabled: 'Включён', disabled: 'Отключён', cooldown: 'Cooldown', limited: 'Ограничен', unknown: 'Неизвестно', orphan: 'Нет привязки'};
export function accountState(account, observedAt) {
  if (account.inventory_present === false) return 'orphan';
  if (account.disabled === true || account.status === 'disabled') return 'disabled';
  const cutoff = Date.parse(observedAt);
  if (Number.isFinite(cutoff) && Number.isFinite(Date.parse(account.next_retry_at)) && Date.parse(account.next_retry_at) > cutoff) return 'cooldown';
  if (account.unavailable === true || account.status === 'error') return 'limited';
  if (account.disabled === false && account.unavailable === false && account.status === 'active') return 'enabled';
  return 'unknown';
}

export function accountRows(snapshot) {
  return combinedAccounts(snapshot);
}

export function windowData(account, window) {
  return account?.windows?.[window] ?? null;
}

export function emptyMessage(snapshot, filtered) {
  if (snapshot?.inventory?.status !== 'ok' || snapshot.inventory.complete !== true) return 'Реестр недоступен или получен не полностью. Наличие аккаунтов неизвестно.';
  return filtered ? 'Нет аккаунтов с выбранными условиями. Измените поиск или состояние.' : 'Нет аккаунтов для отображения.';
}

export function viewRows(snapshot, {window = '60', query = '', state = 'all', sort = 'attempts', direction = -1, cohort = 'all_attempt_latency_ms'} = {}) {
  const needle = query.trim().toLocaleLowerCase('ru');
  const value = row => {
    const data = windowData(row, window);
    return {label: row.label, attempts: data?.attempt_records, errors: data?.failed_fraction_of_all_records,
      p50: data?.[cohort]?.p50, p95: data?.[cohort]?.p95, input: data?.tokens?.input_tokens?.sum,
      output: data?.tokens?.output_tokens?.sum}[sort];
  };
  return accountRows(snapshot).filter(row =>
    (!needle || `${row.label} ${row.id} ${row.provider}`.toLocaleLowerCase('ru').includes(needle)) &&
    (state === 'all' || accountState(row, snapshot.observed_at_utc) === state)
  ).sort((a, b) => {
    const x = value(a), y = value(b);
    if (sort === 'label') return direction * String(x ?? '').localeCompare(String(y ?? ''), 'ru');
    if (!numeric(x) || !numeric(y)) return numeric(x) ? -1 : numeric(y) ? 1 : String(a.id).localeCompare(String(b.id));
    return direction * (x - y) || String(a.id).localeCompare(String(b.id));
  });
}
