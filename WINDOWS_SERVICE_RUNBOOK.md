# Windows Service Runbook

## Objetivo

Empacotar o agent Python para Windows e instala-lo como servico para piloto.

Este piloto usa credencial direta do MinIO no endpoint. Na fase seguinte, o ideal e trocar isso por URL pre-assinada emitida pela API central.

No lab, o endpoint correto do storage e o S3 publicado em `http://s3.homelab.local`, nao o console `minio.homelab.local`.

## Estrutura recomendada no endpoint

- `C:\Program Files\ScreenshotAudit\ScreenshotAuditAgent.exe`
- `C:\Program Files\ScreenshotAudit\agent_config.json`
- `%ProgramData%\ScreenshotAudit\spool`
- `%ProgramData%\ScreenshotAudit\tmp`
- `%ProgramData%\ScreenshotAudit\data\queue.db`
- `%ProgramData%\ScreenshotAudit\logs\agent.log`
- `%ProgramData%\ScreenshotAudit\assets\logo.png`

## 1. Preparar a maquina de build

1. Instale Python 3.12 ou 3.13 no Windows.
2. Abra PowerShell no diretorio do projeto.
3. Crie o ambiente virtual:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-agent.txt pyinstaller
```

## 2. Preparar a configuracao

1. Copie `agent_config.example.json` para `agent_config.json`.
2. Preencha:
   - `minio.access_key`
   - `minio.secret_key`
   - `routing.external_ip_map`
3. Ajuste o logo em `%ProgramData%\ScreenshotAudit\assets\logo.png`.

## 3. Gerar o executavel

```powershell
pyinstaller --noconfirm --onefile --name ScreenshotAuditAgent mock_watermark.py
```

O executavel sera gerado em:

- `dist\ScreenshotAuditAgent.exe`

## 4. Copiar arquivos para o endpoint piloto

Crie os diretorios:

```powershell
New-Item -ItemType Directory -Force -Path "C:\Program Files\ScreenshotAudit" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:ProgramData\ScreenshotAudit\assets" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:ProgramData\ScreenshotAudit\spool" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:ProgramData\ScreenshotAudit\tmp" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:ProgramData\ScreenshotAudit\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:ProgramData\ScreenshotAudit\logs" | Out-Null
```

Copie:

- `dist\ScreenshotAuditAgent.exe` para `C:\Program Files\ScreenshotAudit\`
- `agent_config.json` para `C:\Program Files\ScreenshotAudit\`
- `logo.png` para `%ProgramData%\ScreenshotAudit\assets\`

## 5. Instalar como servico com NSSM

Para piloto, use NSSM. E o jeito mais simples para um executavel console rodar bem como servico.

1. Baixe e extraia o NSSM.
2. Coloque `nssm.exe` em `C:\Tools\nssm\nssm.exe`.
3. Rode:

```powershell
C:\Tools\nssm\nssm.exe install ScreenshotAuditAgent "C:\Program Files\ScreenshotAudit\ScreenshotAuditAgent.exe" --config "C:\Program Files\ScreenshotAudit\agent_config.json"
C:\Tools\nssm\nssm.exe set ScreenshotAuditAgent AppDirectory "C:\Program Files\ScreenshotAudit"
C:\Tools\nssm\nssm.exe set ScreenshotAuditAgent Start SERVICE_AUTO_START
C:\Tools\nssm\nssm.exe set ScreenshotAuditAgent AppStdout "$env:ProgramData\ScreenshotAudit\logs\service-stdout.log"
C:\Tools\nssm\nssm.exe set ScreenshotAuditAgent AppStderr "$env:ProgramData\ScreenshotAudit\logs\service-stderr.log"
Start-Service ScreenshotAuditAgent
```

## 6. Validar

1. Valide o servico:

```powershell
Get-Service ScreenshotAuditAgent
```

2. Execute um teste sem servico:

```powershell
& "C:\Program Files\ScreenshotAudit\ScreenshotAuditAgent.exe" --config "C:\Program Files\ScreenshotAudit\agent_config.json" --once
```

3. Verifique os logs:

```powershell
Get-Content "$env:ProgramData\ScreenshotAudit\logs\agent.log" -Tail 50
```

4. Verifique se o screenshot:
   - entrou no spool
   - foi watermarkado
   - subiu no bucket esperado
   - foi apagado localmente apos sucesso

## 7. Distribuicao inicial

Para o primeiro piloto eu recomendo:

1. Copiar binario e config por GPO de startup ou manualmente.
2. Instalar o servico com PowerShell remoto ou WinRM.
3. Depois que o fluxo estiver estavel, encapsular isso em playbook do Semaphore.

## 8. Quando vale MSI

MSI vale quando:

- o layout de arquivos ja estabilizou
- a configuracao padronizada ja esta definida
- voces quiserem uninstall/upgrade formal
- o rollout ja estiver repetivel

Antes disso, `PyInstaller + NSSM + script de instalacao` e mais rapido e menos custoso.

## 9. Atalho para o canario com WinRM

Se o Python ja estiver presente no host piloto, o playbook `install_agent_canary` pode:

1. copiar `mock_watermark.py` e `requirements-agent.txt`
2. criar um `venv` no proprio Windows
3. instalar `pyinstaller`
4. gerar `ScreenshotAuditAgent.exe`
5. registrar o servico com NSSM

Esse caminho acelera o primeiro piloto e evita travar a validacao do fluxo enquanto o pacote MSI definitivo ainda nao existe.
