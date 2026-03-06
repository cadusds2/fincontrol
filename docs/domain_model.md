# Modelo de Domínio

## Entidades centrais

## 1) Account
Representa uma conta corrente ou cartão de crédito do usuário.

**Responsabilidades:**
- Identificar a origem financeira de uma transação.
- Permitir múltiplas contas/cartões por banco.

**Campos sugeridos:**
- `id`
- `bank_name` (ex.: Nubank, Itaú)
- `account_type` (`checking`, `credit_card`)
- `display_name` (nome amigável)
- `external_ref` (identificador opcional)
- `is_active`

## 2) ImportBatch
Representa uma execução de importação de um arquivo CSV.

**Responsabilidades:**
- Rastrear arquivo importado e contexto de origem.
- Registrar resultado do processamento.

**Campos sugeridos:**
- `id`
- `account_id` (FK Account)
- `file_type` (extrato/fatura e banco)
- `source_filename`
- `imported_at`
- `status` (`received`, `processed`, `failed`, `partial`)
- `total_rows`
- `imported_rows`
- `duplicated_rows`
- `error_log`

## 3) Transaction
Representa um lançamento financeiro persistido.

**Responsabilidades:**
- Materializar movimento financeiro para classificação e relatório.

**Campos sugeridos:**
- `id`
- `import_batch_id` (FK ImportBatch)
- `account_id` (FK Account)
- `transaction_date`
- `posted_date` (opcional)
- `description_raw`
- `description_norm`
- `merchant_norm`
- `amount`
- `currency` (default BRL)
- `direction` (`debit`, `credit`)
- `category_id` (FK Category, opcional até classificar)
- `classification_source` (`merchant_map`, `rule`, `similarity`, `manual`, `unclassified`)
- `classification_confidence` (0.0 a 1.0)
- `is_technical`
- `is_installment`
- `installment_current`
- `installment_total`
- `installment_key`
- `raw_hash` (apoio a deduplicação)

## 4) MerchantMap
Mapeia `merchant_norm` para categoria preferencial.

**Responsabilidades:**
- Aprender com revisão manual.
- Aumentar precisão da classificação automática futura.

**Campos sugeridos:**
- `id`
- `merchant_norm` (único por escopo definido)
- `category_id` (FK Category)
- `confidence`
- `source` (`seed`, `manual_review`, `migration`)
- `last_used_at`
- `usage_count`

## 5) ReviewQueue
Fila de transações que precisam de revisão manual.

**Responsabilidades:**
- Isolar casos de baixa confiança.
- Priorizar tratamento do usuário.

**Campos sugeridos:**
- `id`
- `transaction_id` (FK Transaction, único)
- `reason` (`low_confidence`, `conflict`, `no_match`, `rule_blocked`)
- `suggested_category_id` (opcional)
- `created_at`
- `resolved_at` (opcional)
- `status` (`pending`, `resolved`, `ignored`)

## 6) Budget
Orçamento por período e categoria.

**Responsabilidades:**
- Registrar meta de gastos para acompanhamento.

**Campos sugeridos:**
- `id`
- `period_month` (ex.: 2025-01)
- `category_id` (FK Category)
- `planned_amount`
- `notes`

## 7) Category (recomendada para o MVP)
Catálogo de categorias de classificação e relatório.

**Responsabilidades:**
- Padronizar taxonomia de consumo e categorias técnicas.

**Campos sugeridos:**
- `id`
- `name`
- `slug`
- `kind` (`consumption`, `technical`)
- `is_reportable` (false para técnicas)
- `is_active`

## Relações principais

- Uma `Account` possui muitos `ImportBatch`.
- Uma `Account` possui muitas `Transaction`.
- Um `ImportBatch` possui muitas `Transaction`.
- Uma `Transaction` pode gerar um item em `ReviewQueue`.
- Uma `Category` pode ser usada por `Transaction`, `MerchantMap` e `Budget`.
- Um `MerchantMap` referencia uma `Category`.

## Regras de domínio críticas

- `Pagamento de Fatura` e `Transferência Interna` são categorias técnicas.
- Transações com categorias técnicas não devem compor relatórios de consumo.
- Parcelas devem ser registradas como movimentos mensais reais (cash basis).
