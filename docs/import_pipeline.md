# Pipeline de Importação Manual (MVP)

## Objetivo

Importar CSV com rastreabilidade por lote, validação por parser dedicado e deduplicação canônica.

## Entradas obrigatórias no upload

1. `file_type` (seleção manual):
   - extrato_conta_nubank
   - fatura_cartao_nubank
   - extrato_conta_itau
   - fatura_cartao_itau
2. `account_id` (seleção manual de conta/cartão já cadastrado)
3. `reference_month` (mês de referência do lote)
4. arquivo CSV (`ImportBatch.file`)

Não há autodetecção no MVP.

## Etapas do pipeline

### 1) Recebimento e criação do lote
- Validar presença de `file_type`, `account_id` e arquivo.
- Criar `ImportBatch` com status `received`.

### 2) Leitura e validação estrutural
- Selecionar parser dedicado conforme `file_type` usando contrato único de parser.
- Validar colunas obrigatórias do layout antes de processar as linhas.
- Se falha estrutural total, finalizar `ImportBatch` como `failed`.

### 3) Transformação para formato canônico
Para cada linha válida:
- mapear data, descrição, valor, moeda e direção;
- preencher `description_raw`;
- gerar `description_norm`, `merchant_raw` e `merchant_norm`;
- mapear metadados de parcela quando existirem.

### 4) Deduplicação canônica (MVP)
- Calcular `raw_hash` sobre campos normalizados.
- Fórmula de referência do MVP:
  - `raw_hash = sha256(account_id + transaction_date + amount + description_norm)`
- Escopo de unicidade: `account_id + raw_hash`.
- Se já existir transação com a mesma chave canônica, tratar como duplicata.
- Duplicata não é persistida e incrementa `ImportBatch.duplicated_rows`.

### 5) Persistência de transações
- Criar `Transaction` vinculada a `ImportBatch` e `Account`.
- Iniciar com `classification_source=unclassified`.

### 6) Fechamento do lote
- Atualizar `rows_total`, `rows_imported`, `rows_skipped` e métricas legadas (`total_rows`, `imported_rows`, `duplicated_rows`).
- Definir status final:
  - `processed`: sem erros relevantes;
  - `partial`: com linhas descartadas/erros parciais;
  - `failed`: sem linhas importadas.

### 7) Disparo da classificação
- Nesta primeira versão funcional da importação, transações entram como `classification_source=unclassified`.
- O disparo automático do pipeline completo será conectado na fase de classificação.

## Regras de parser no MVP

- Cada `file_type` possui parser dedicado e testável.
- Mudanças de layout bancário exigem atualização explícita do parser correspondente.

## Observabilidade e auditoria

- Registrar erros por linha com motivo objetivo.
- Não expor dados sensíveis completos em logs.
- Manter vínculo obrigatório entre `Transaction` e `ImportBatch`.
