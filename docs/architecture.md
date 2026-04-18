# Arquitetura do Sistema (MVP)

## Visão geral

Arquitetura monolítica em Django com separação por apps e serviços internos:

1. Interface Web (Django Templates, HTMX opcional)
2. Camada de aplicação (fluxos de importação, classificação, revisão, relatório)
3. Domínio (entidades e regras)
4. Persistência (ORM Django + SQLite)

## Estrutura inicial sugerida de apps Django

- `accounts`
  - cadastro e manutenção de `Account`.
- `imports`
  - upload manual, `ImportBatch`, parsers e deduplicação (`external_id + raw_hash` quando disponível, fallback `raw_hash`).
- `transactions`
  - persistência e consulta de `Transaction`.
- `classification`
  - normalização, regra técnica de alias do titular, `MerchantMap`, regras YAML via `ClassificationRuleSet`, similaridade e `ReviewQueue`.
- `reports`
  - relatórios de consumo e visão básica de `Budget`.

## Fluxos críticos do MVP

### 1) Importação manual
1. Usuário seleciona `file_type`, `account_id` e CSV.
2. Sistema cria `ImportBatch`.
3. Parser dedicado transforma linhas para formato canônico.
4. Deduplicação prioriza `account_id + external_id + raw_hash` quando disponível, com fallback para `account_id + raw_hash`.
5. Transações válidas são persistidas e lote é finalizado.

### 2) Classificação
1. Transações entram com `classification_source=unclassified`.
2. Pipeline executa na ordem oficial: normalização → alias do titular (transferência interna) → MerchantMap → regras YAML → similaridade.
3. Sem confiança suficiente, criar item em `ReviewQueue`.

As regras YAML ficam em rulesets versionados no banco e são editadas pelo Django Admin.
O Admin valida o YAML antes da ativação e mantém apenas um `ClassificationRuleSet` ativo por vez.
Proteções técnicas relacionais ou sensíveis, como alias do titular e par Pix no Crédito, permanecem em Python.

### 3) Revisão manual
1. Usuário abre fila pendente.
2. Define categoria final para cada item.
3. Sistema atualiza `Transaction` (`classification_source=manual`) e retroalimenta `MerchantMap` quando aplicável.

### 4) Geração de relatórios
1. Relatório agrega transações por período/categoria.
2. Somente categorias com `Category.is_reportable=true` entram no total principal.
3. Categorias técnicas ficam fora do consumo principal.

## Princípios de implementação

- Sem LLM no MVP.
- Sem autodetecção de tipo de arquivo ou conta/cartão.
- Rastreabilidade ponta a ponta por `ImportBatch`.
- Transparência da origem da classificação.
