# Semaphore Templates

## Project suggestion

Crie um projeto no Semaphore chamado:

- `leakguard`

## Inventories

- `sharex-pilot`
- depois: `sharex-clickip`, `sharex-fiber`, `sharex-intlink`

## Environment

Variaveis comuns:

- `ANSIBLE_HOST_KEY_CHECKING=False`
- `PYTHONUNBUFFERED=1`

Credenciais:

- `ansible_password`
- `leakguard_agent_api_bearer_token`

Observacao:

- o metodo de conexao e o usuario de cada host devem vir do inventario
- use o mesmo padrao de dominio (`winrm/kerberos`) nos hosts que ja estao no AD para evitar divergencias entre piloto e producao
- o secret do token da API deve usar exatamente a chave `leakguard_agent_api_bearer_token`
- o nome do grupo de variaveis pode ser qualquer um, mas a chave interna deve ser exatamente `leakguard_agent_api_bearer_token`
- os templates `*_canary` executam apenas no `HOST-TEST2`; os templates sem `canary` usam todo o grupo `sharex_pilot`
- por compatibilidade temporaria, os playbooks tambem aceitam os aliases `Service token api`, `service_token_api` e a env `LEAKGUARD_AGENT_API_BEARER_TOKEN`

## Templates iniciais

### 1. win_ping

- inventory: `sharex-pilot`
- playbook: `infra/ansible/playbooks/win_ping.yml`
- comportamento: resumo por host sem derrubar a tarefa inteira por um unico host inacessivel

### 2. install_sharex

- inventory: `sharex-pilot`
- playbook: `infra/ansible/playbooks/install_sharex.yml`
- canario pronto: `infra/ansible/playbooks/install_sharex_canary.yml`

### 3. install_agent

- inventory: `sharex-pilot`
- playbook: `infra/ansible/playbooks/install_agent.yml`
- canario pronto: `infra/ansible/playbooks/install_agent_canary.yml`

### 4. configure_sharex_spool

- inventory: `sharex-pilot`
- playbook: `infra/ansible/playbooks/configure_sharex_spool.yml`
- canario pronto: `infra/ansible/playbooks/configure_sharex_spool_canary.yml`

### 5. uninstall_lightshot

- inventory: `sharex-pilot`
- playbook: `infra/ansible/playbooks/uninstall_lightshot.yml`
- canario pronto: `infra/ansible/playbooks/uninstall_lightshot_canary.yml`

### 6. healthcheck_agent

- inventory: `sharex-pilot`
- playbook: `infra/ansible/playbooks/healthcheck_agent.yml`
- canario pronto: `infra/ansible/playbooks/healthcheck_agent_canary.yml`

## Templates operacionais do LeakGuard

### 7. leakguard_capacity_report

- inventory: `leakguard-lab`
- playbook: `infra/ansible/playbooks/leakguard_capacity_report.yml`
- uso: leitura do estado de retenção, Redis, volumetria quente e candidatos frios

### 8. leakguard_maintenance_dry_run

- inventory: `leakguard-lab`
- playbook: `infra/ansible/playbooks/leakguard_maintenance.yml`
- extra vars:
  - `leakguard_maintenance_execute=false`
  - `leakguard_maintenance_prune_evidence=false`

### 9. leakguard_maintenance_execute

- inventory: `leakguard-lab`
- playbook: `infra/ansible/playbooks/leakguard_maintenance.yml`
- extra vars:
  - `leakguard_maintenance_execute=true`
  - `leakguard_maintenance_prune_evidence=false`

### 10. leakguard_prune_evidence

- inventory: `leakguard-lab`
- playbook: `infra/ansible/playbooks/leakguard_maintenance.yml`
- extra vars:
  - `leakguard_maintenance_execute=true`
  - `leakguard_maintenance_prune_evidence=true`
  - `leakguard_maintenance_batch_size=500`

### 11. leakguard_hot_backup

- inventory: `leakguard-lab`
- playbook: `infra/ansible/playbooks/leakguard_hot_backup.yml`
- uso: snapshot quente com `pg_dump`, runtime report e manifesto da camada fria

## Inventário do host do LeakGuard

Novo inventário sugerido:

- `leakguard-lab`
- arquivo: `infra/ansible/inventories/leakguard_lab.ini`

Observações:

- o runner do `Semaphore` atual não tem `docker` nem `docker.sock`
- por isso os templates do LeakGuard devem executar no host Linux via `SSH`
- os playbooks chamam os wrappers em `/var/www/leakguard-api/deploy/run-*.sh`
- configure credencial SSH para o host e `become password` quando necessário

## Agenda sugerida

- `leakguard_capacity_report`: sob demanda ou 1x por dia
- `leakguard_maintenance_dry_run`: sob demanda antes de ajuste de política
- `leakguard_maintenance_execute`: a cada hora
- `leakguard_prune_evidence`: 1x ao dia, fora do horário de pico
- `leakguard_hot_backup`: 1x ao dia antes do off-site do `Duplicati`

## Como isso aparece no UI

Cada execução mostra:

- status geral
- duração
- usuário que disparou
- output por tarefa
- falha por host
- resumo final do Ansible

## Limites uteis no piloto

- `HOSTTESTE`: validado com `winrm/kerberos` e `managed kinit`
- `HOST-TEST2`: deve seguir o mesmo padrao de dominio/kerberos do `HOSTTESTE`

## Estratégia de rollout

No piloto:

- `serial: 1`

Depois:

- grupos por empresa
- rollout por lote
- healthcheck após deploy
- rollback se necessário
