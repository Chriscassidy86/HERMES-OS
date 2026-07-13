param([Parameter(Mandatory=$true)][ValidateSet('start','stop','restart','status','logs','health','dashboard','backup','verify-backup','portfolio','trades','provider','alerts')]$Command)
$db='/app/data/hermes.sqlite3';$backup='/app/data/hermes-backup.sqlite3'
switch($Command){
 'start' { docker compose up -d --build }
 'stop' { docker compose down }
 'restart' { docker compose restart }
 'status' { docker compose ps }
 'logs' { docker compose logs --tail 200 -f }
 'health' { docker compose exec -T hermes-paper python scripts/healthcheck.py }
 'dashboard' { Start-Process 'http://127.0.0.1:8765/' }
 'backup' { docker compose exec -T hermes-paper python -m database.maintenance backup $db $backup }
 'verify-backup' { docker compose exec -T hermes-paper python -m database.maintenance verify-backup $db $backup }
 'portfolio' { docker compose exec -T hermes-paper python -m reports.operator_cli $db portfolio }
 'trades' { docker compose exec -T hermes-paper python -m reports.operator_cli $db trades }
 'provider' { docker compose exec -T hermes-paper python -m reports.operator_cli $db provider }
 'alerts' { docker compose exec -T hermes-paper python -m reports.operator_cli $db alerts }
}
