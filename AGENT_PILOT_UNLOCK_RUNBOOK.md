# Agent Pilot Unlock Runbook

## Estado atual do canario

- `install_sharex_canary`: ok
- `configure_sharex_spool_canary`: ok
- `uninstall_lightshot_canary`: ok
- `healthcheck_agent_canary`: esperado como `missing`, porque o agent ainda nao foi instalado

## Objetivo desta fase

Destravar o primeiro deploy funcional do `ScreenshotAuditAgent` no `HOST-TEST2`.

## Artefatos obrigatorios no controller

Os playbooks do agent esperam estes arquivos no host Debian:

- `/var/www/audit_screenshot/dist/ScreenshotAuditAgent.exe`
- `/var/www/audit_screenshot/agent_config.json`
- `/var/www/audit_screenshot/logo.png`
- `/var/www/audit_screenshot/bin/nssm.exe`

## Ordem exata de destravamento

### 1. Validar o ShareX no canario

No `HOST-TEST2`:

1. Abra o ShareX novamente depois do playbook de configuracao.
2. Tire um screenshot.
3. Verifique se o arquivo nasceu sob:

- `C:\ProgramData\ScreenshotAudit\spool`

Observacao:

- o ShareX pode criar subpastas como `Screenshots\2026-03`
- o agent ja foi ajustado para varrer o spool de forma recursiva

### 2. Gerar o executavel do agent em Windows

Use uma VM Windows de build ou o proprio host piloto.

Siga [WINDOWS_SERVICE_RUNBOOK.md](./WINDOWS_SERVICE_RUNBOOK.md):

1. criar `.venv`
2. instalar dependencias e `pyinstaller`
3. gerar `dist\ScreenshotAuditAgent.exe`

Comando principal:

```powershell
pyinstaller --noconfirm --onefile --name ScreenshotAuditAgent mock_watermark.py
```

### 3. Fechar o `agent_config.json`

Copie:

- `agent_config.example.json` -> `agent_config.json`

Preencha obrigatoriamente:

- `minio.access_key`
- `minio.secret_key`
- `routing.external_ip_map`

Mantenha este caminho:

- `paths.spool_dir = %ProgramData%\ScreenshotAudit\spool`

### 4. Preparar os arquivos auxiliares

1. Coloque o logo final em:

- `/var/www/audit_screenshot/logo.png`

2. Coloque o `nssm.exe` em:

- `/var/www/audit_screenshot/bin/nssm.exe`

3. Copie o executavel gerado para:

- `/var/www/audit_screenshot/dist/ScreenshotAuditAgent.exe`

4. Copie o config final para:

- `/var/www/audit_screenshot/agent_config.json`

### 5. Rodar o deploy do agent

No Semaphore:

1. `install_agent_canary`
2. `healthcheck_agent_canary`

Resultado esperado do healthcheck:

- `Service exists: True`
- `Service state: running`
- `Queue DB exists: True` ou passa a existir apos o primeiro processamento

### 6. Fazer o teste ponta a ponta

No `HOST-TEST2`:

1. tire um screenshot no ShareX
2. confirme o arquivo no spool
3. confirme que o agent processou
4. confirme upload no bucket do MinIO
5. confirme limpeza local apos sucesso

### 7. So depois disso

1. repetir o mesmo fluxo no `HOSTTESTE`
2. fechar o caminho Kerberos no executor Linux
3. so entao ampliar para mais hosts

## Papel de cada camada

- `ShareX`: gera o screenshot e grava no spool
- `Agent Windows Service`: observa o spool, watermark, SQLite local, upload e retry
- `Semaphore + Ansible + WinRM`: instala, atualiza, configura e faz healthcheck
- `MSI`: opcional depois, quando o pacote do agent estiver estavel
