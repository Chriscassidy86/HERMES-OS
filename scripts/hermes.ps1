param([Parameter(Mandatory=$true,Position=0)][ValidateSet('start','stop','restart','status','logs','health','dashboard','backup','verify-backup','portfolio','trades','provider','alerts','report','scoreboard','decisions','summary','soak-start','soak-status','soak-stop','soak-export')]$Command,[Parameter(Position=1)]$Target)
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
 'report' { docker compose exec -T hermes-paper python -m reports.validation_cli $db report }
 'scoreboard' { docker compose exec -T hermes-paper python -m reports.validation_cli $db scoreboard }
 'decisions' { docker compose exec -T hermes-paper python -m reports.validation_cli $db decisions }
 'summary' { docker compose exec -T hermes-paper python -m reports.validation_cli $db summary }
 'soak-start' { if($Target -notin @('24h','72h','7d')){throw 'Use soak-start 24h, 72h, or 7d.'}; docker compose exec -T hermes-paper python -m services.wall_clock_soak_cli start $Target --state /app/data/hermes-soak.json --database $db --logs /app/logs }
 'soak-status' { docker compose exec -T hermes-paper python -m services.wall_clock_soak_cli status --state /app/data/hermes-soak.json --database $db --logs /app/logs }
 'soak-stop' { docker compose exec -T hermes-paper python -m services.wall_clock_soak_cli stop --state /app/data/hermes-soak.json --database $db --logs /app/logs }
 'soak-export' { docker compose exec -T hermes-paper python -m services.wall_clock_soak_cli export /app/data/hermes-soak-report.json --state /app/data/hermes-soak.json --database $db --logs /app/logs }
}
