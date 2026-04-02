# Modelo de Domínio (MVP)

Este documento define o contrato de dados do MVP com foco em implementabilidade.

## Convenções gerais

- `id`: chave primária.
- `created_at` e `updated_at`: recomendados para auditoria em todas as entidades.
- Todos os campos monetários devem usar precisão decimal (sem float).
- Toda `Transaction` deve ter vínculo obrigatório com `Account` e `ImportBatch`.

## 1) Account

**Propósito:** representar conta corrente ou cartão de crédito de origem das transações.

**Campos obrigatórios (MVP):**
- `bank_name`
- `account_type` (`checking`, `credit_card`)
- `display_name`
- `is_active`

**Campos opcionais (MVP):**
- `external_ref`

**Relações:**
- 1:N com `ImportBatch`
- 1:N com `Transaction`

## 2) ImportBatch

**Propósito:** rastrear uma execução de importação manual de CSV.

**Campos obrigatórios (MVP):**
- `account_id` (FK `Account`)
- `file` (upload do CSV original)
- `file_type` (layout/banco explícito)
- `reference_month`
- `source_filename`
- `status` (`received`, `processed`, `partial`, `failed`)
- `rows_total`
- `rows_imported`
- `rows_skipped`
- `total_rows`
- `imported_rows`
- `duplicated_rows`
- `imported_at`

**Campos opcionais (MVP):**
- `error_log`

**Relações:**
- N:1 com `Account`
- 1:N com `Transaction`

## 3) Category

**Propósito:** padronizar classificação e reportabilidade.

**Campos obrigatórios (MVP):**
- `name`
- `slug`
- `kind` (`consumo`, `tecnica`)
- `is_reportable`

**Campos opcionais (MVP):**
- `description`
- `is_active` (padrão `true`)

**Regras obrigatórias (MVP):**
- `kind=consumo` implica `is_reportable=true`.
- `kind=tecnica` implica `is_reportable=false`.

## 4) Transaction

**Propósito:** registrar lançamento financeiro canônico para classificação e relatório.

**Campos obrigatórios (MVP):**
- `import_batch_id` (FK `ImportBatch`)
- `account_id` (FK `Account`)
- `transaction_date`
- `description_raw`
- `description_norm`
- `merchant_raw`
- `merchant_norm`
- `amount`
- `currency` (padrão `BRL`)
- `direction` (`debit`, `credit`)
- `raw_hash`
- `classification_source` (`merchant_map`, `rule`, `similarity`, `manual`, `unclassified`)

**Campos opcionais (MVP):**
- `posted_date`
- `category_id` (FK `Category`)
- `classification_confidence` (0.0 a 1.0)
- `is_installment`
- `installment_current`
- `installment_total`
- `installment_key`

**Regras obrigatórias (MVP):**
- unicidade por `account_id + raw_hash`.
- `classification_source=unclassified` na criação, antes do pipeline de classificação.

## 5) MerchantMap

**Propósito:** mapear merchant recorrente para categoria com aprendizado incremental.

**Campos obrigatórios (MVP):**
- `merchant_norm`
- `category_id` (FK `Category`)
- `source` (`seed`, `manual_review`)

**Campos opcionais (MVP):**
- `confidence`
- `usage_count`
- `last_used_at`

**Relações:**
- N:1 com `Category`

## 6) ReviewQueue

**Propósito:** controlar pendências de classificação manual.

**Campos obrigatórios (MVP):**
- `transaction_id` (FK `Transaction`, único)
- `reason` (`low_confidence`, `conflict`, `no_match`)
- `status` (`pending`, `resolved`, `ignored`)
- `created_at`

**Campos opcionais (MVP):**
- `suggested_category_id` (FK `Category`)
- `resolved_at`
- `resolution_note`

**Relações:**
- 1:1 com `Transaction`
- N:1 opcional com `Category` (sugestão)

## 7) Budget

**Propósito:** definir orçamento mensal por categoria de consumo.

**Campos obrigatórios (MVP):**
- `period_month` (formato `YYYY-MM`)
- `category_id` (FK `Category`)
- `planned_amount`

**Campos opcionais (MVP):**
- `notes`

**Regras obrigatórias (MVP):**
- `Budget` só pode apontar para `Category.kind=consumo`.
- unicidade por `period_month + category_id`.

## Relações-chave do domínio

- `Account` 1:N `ImportBatch`
- `Account` 1:N `Transaction`
- `ImportBatch` 1:N `Transaction`
- `Category` 1:N `Transaction`
- `Category` 1:N `MerchantMap`
- `Transaction` 1:1 `ReviewQueue`
- `Category` 1:N `Budget`
