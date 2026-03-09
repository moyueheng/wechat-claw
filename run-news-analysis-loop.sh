#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${PROJECT_ROOT}/input/data/state"
LOG_FILE="${LOG_DIR}/news-analysis-loop.log"
PID_FILE="${LOG_DIR}/news-analysis-loop.pid"
SLEEP_SECONDS="${SLEEP_SECONDS:-1800}"
INITIAL_DELAY_SECONDS="${INITIAL_DELAY_SECONDS:-0}"
LOG_MAX_BYTES="${LOG_MAX_BYTES:-10485760}"
LOG_ROTATE_COUNT="${LOG_ROTATE_COUNT:-5}"
COMMAND="${1:-start}"

mkdir -p "${LOG_DIR}"

PROMPT="$(cat <<'EOF'
使用这个 skill `.agents/skills/news-analysis/SKILL.md`。
最终分析报告只发送到飞书
如果 `.env` 中存在可用的飞书别名映射，则优先使用该映射解析发送目标。
如果没有可用的飞书目标配置，直接报错并结束
如果没有新增新闻就不要发送任何消息，直接结束任务。
按时间顺序处理全部待分析新闻，并在每条发送完成后按 skill 要求归档。
EOF
)"

log() {
  local level="$1"
  shift
  local message
  message="$(printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${level}" "$*")"
  rotate_log_if_needed
  printf '%s\n' "${message}" | tee -a "${LOG_FILE}" >&2
}

validate_log_rotation_config() {
  if ! [[ "${LOG_MAX_BYTES}" =~ ^[0-9]+$ ]] || [[ "${LOG_MAX_BYTES}" -le 0 ]]; then
    echo "LOG_MAX_BYTES must be a positive integer, got: ${LOG_MAX_BYTES}" >&2
    exit 1
  fi

  if ! [[ "${LOG_ROTATE_COUNT}" =~ ^[0-9]+$ ]] || [[ "${LOG_ROTATE_COUNT}" -lt 1 ]]; then
    echo "LOG_ROTATE_COUNT must be an integer >= 1, got: ${LOG_ROTATE_COUNT}" >&2
    exit 1
  fi
}

rotate_log_if_needed() {
  local current_size
  local index

  if [[ ! -f "${LOG_FILE}" ]]; then
    return 0
  fi

  current_size="$(wc -c <"${LOG_FILE}")"
  if [[ "${current_size}" -lt "${LOG_MAX_BYTES}" ]]; then
    return 0
  fi

  rm -f "${LOG_FILE}.${LOG_ROTATE_COUNT}"
  for ((index = LOG_ROTATE_COUNT - 1; index >= 1; index--)); do
    if [[ -f "${LOG_FILE}.${index}" ]]; then
      mv "${LOG_FILE}.${index}" "${LOG_FILE}.$((index + 1))"
    fi
  done

  mv "${LOG_FILE}" "${LOG_FILE}.1"
  : >"${LOG_FILE}"
}

require_kimi() {
  if ! command -v kimi >/dev/null 2>&1; then
    echo "kimi command not found" >&2
    exit 1
  fi
}

is_pid_running() {
  local pid="$1"
  ps -p "${pid}" -o pid= >/dev/null 2>&1
}

read_pid() {
  if [[ -f "${PID_FILE}" ]]; then
    tr -d '[:space:]' <"${PID_FILE}"
  fi
}

clear_pid_file() {
  rm -f "${PID_FILE}"
}

write_pid_file() {
  printf '%s\n' "$$" >"${PID_FILE}"
}

ensure_single_instance() {
  local existing_pid
  existing_pid="$(read_pid)"

  if [[ -n "${existing_pid}" ]]; then
    if is_pid_running "${existing_pid}"; then
      echo "already running: pid=${existing_pid}"
      exit 1
    fi
    log WARN "stale pid file detected: pid=${existing_pid}"
    clear_pid_file
  fi
}

shutdown_loop() {
  local signal_name="$1"
  log INFO "received ${signal_name}, exiting loop"
  clear_pid_file
  exit 0
}

run_once() {
  local start_ts end_ts duration exit_code
  start_ts="$(date +%s)"

  log INFO "run start"
  log INFO "project_root=${PROJECT_ROOT}"
  log INFO "log_file=${LOG_FILE}"
  log INFO "pid_file=${PID_FILE}"
  log INFO "initial_delay_seconds=${INITIAL_DELAY_SECONDS} sleep_seconds=${SLEEP_SECONDS}"
  log INFO "log_max_bytes=${LOG_MAX_BYTES} log_rotate_count=${LOG_ROTATE_COUNT}"
  log INFO "kimi command: kimi --print -p <prompt> --work-dir ${PROJECT_ROOT} --add-dir ${PROJECT_ROOT} --output-format text"
  log INFO "prompt<<EOF"
  while IFS= read -r line; do
    log INFO "prompt| ${line}"
  done <<<"${PROMPT}"
  log INFO "EOF"

  cd "${PROJECT_ROOT}"
  rotate_log_if_needed
  if kimi --print \
    -p "${PROMPT}" \
    --work-dir "${PROJECT_ROOT}" \
    --add-dir "${PROJECT_ROOT}" \
    --output-format text >>"${LOG_FILE}" 2>&1; then
    exit_code=0
  else
    exit_code=$?
  fi

  end_ts="$(date +%s)"
  duration="$((end_ts - start_ts))"
  log INFO "run done exit_code=${exit_code} duration_seconds=${duration}"

  return "${exit_code}"
}

start_loop() {
  require_kimi
  validate_log_rotation_config
  ensure_single_instance
  write_pid_file

  trap 'shutdown_loop SIGINT' INT
  trap 'shutdown_loop SIGTERM' TERM
  trap 'clear_pid_file' EXIT

  echo "started pid=$$ log=${LOG_FILE}"
  log INFO "loop boot pid=$$"
  log INFO "sleep before first run: ${INITIAL_DELAY_SECONDS}s"
  sleep "${INITIAL_DELAY_SECONDS}"

  while true; do
    if ! run_once; then
      log ERROR "run failed; continue loop"
    fi
    log INFO "sleep before next run: ${SLEEP_SECONDS}s"
    sleep "${SLEEP_SECONDS}"
  done
}

stop_loop() {
  local existing_pid
  local waited_seconds
  existing_pid="$(read_pid)"

  if [[ -z "${existing_pid}" ]]; then
    echo "not running"
    return 0
  fi

  if ! is_pid_running "${existing_pid}"; then
    echo "stale pid file removed: pid=${existing_pid}"
    clear_pid_file
    return 0
  fi

  kill "${existing_pid}"
  waited_seconds=0
  while is_pid_running "${existing_pid}"; do
    if [[ "${waited_seconds}" -ge 5 ]]; then
      kill -9 "${existing_pid}" >/dev/null 2>&1 || true
      break
    fi
    sleep 1
    waited_seconds="$((waited_seconds + 1))"
  done

  if is_pid_running "${existing_pid}"; then
    echo "failed to stop pid=${existing_pid}"
    return 1
  fi

  clear_pid_file
  echo "stopped pid=${existing_pid}"
}

status_loop() {
  local existing_pid
  existing_pid="$(read_pid)"

  if [[ -z "${existing_pid}" ]]; then
    echo "not running"
    return 1
  fi

  if is_pid_running "${existing_pid}"; then
    echo "running pid=${existing_pid}"
    return 0
  fi

  echo "stale pid file pid=${existing_pid}"
  return 1
}

usage() {
  cat <<'EOF'
Usage:
  ./run-news-analysis-loop.sh start
  ./run-news-analysis-loop.sh stop
  ./run-news-analysis-loop.sh status
  ./run-news-analysis-loop.sh run-once
EOF
}

case "${COMMAND}" in
  start)
    start_loop
    ;;
  stop)
    stop_loop
    ;;
  status)
    status_loop
    ;;
  run-once)
    require_kimi
    validate_log_rotation_config
    run_once
    ;;
  *)
    usage
    exit 1
    ;;
esac
