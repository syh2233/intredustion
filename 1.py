sudo tee /usr/local/sbin/cli-proxy-watchdog.sh >/dev/null <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

PROXY_URL="${PROXY_URL:-http://127.0.0.1:10809}"
PROBE_URL="${PROBE_URL:-https://baobao-ai.com/codex/responses}"
ATTEMPTS="${ATTEMPTS:-3}"
FAIL_THRESHOLD="${FAIL_THRESHOLD:-3}"
STATE_FILE="${STATE_FILE:-/run/cli-proxy-watchdog.failcount}"

log(){ printf '[%s] %s\n' "$(date -u +'%F %T UTC')" "$*"; }

probe_once() {
/usr/bin/curl -sS -o /dev/null --max-time 12 --noproxy '' -x "$PROXY_URL" "$PROBE_URL"
}

get_failcount(){ [[ -f "$STATE_FILE" ]] && cat "$STATE_FILE" 2>/dev/null || echo 0; }
set_failcount(){ printf '%s' "$1" >"$STATE_FILE"; }

ok=0
for _ in $(seq 1 "$ATTEMPTS"); do
if probe_once; then ok=1; break; fi
sleep 1
done

if [[ "$ok" == "1" ]]; then
set_failcount 0
log "Probe OK via $PROXY_URL -> $PROBE_URL (failcount reset)"
exit 0
fi

failcount="$(get_failcount)"; failcount="$((failcount + 1))"; set_failcount "$failcount"
log "Probe FAILED ($ATTEMPTS attempts). failcount=$failcount (threshold=$FAIL_THRESHOLD)"

if [[ "$failcount" -ge "$FAIL_THRESHOLD" ]]; then
log "Restarting services: xray.service, cli-proxy-api.service"
systemctl restart xray.service
systemctl restart cli-proxy-api.service
set_failcount 0
fi
EOF

sudo chmod 0755 /usr/local/sbin/cli-proxy-watchdog.sh

      2. 把 unit 改成用 bash 调脚本（更稳，也避免未来遇到 noexec 之类的问题）

sudo tee /etc/systemd/system/cli-proxy-watchdog.service >/dev/null <<'EOF'
[Unit]
Description=CLI proxy watchdog (restart xray/cli-proxy-api on failure)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/flock -n /run/cli-proxy-watchdog.lock /bin/bash /usr/local/sbin/cli-proxy-watchdog.sh
EOF