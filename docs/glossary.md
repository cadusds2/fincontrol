# Glossário

## Account
Conta corrente ou cartão de crédito cadastrado no sistema e usado como origem das transações.

## ImportBatch
Lote de importação de um CSV com metadados do processo, status e contadores.

## Transaction
Lançamento financeiro individual persistido, associado a conta/cartão e lote de importação.

## Category
Taxonomia usada na classificação. No MVP pode ser `kind=consumo` (reportável) ou `kind=tecnica` (não reportável).

## Categoria reportável
Categoria com `Category.is_reportable=true`, incluída nos relatórios principais de consumo.

## Categoria técnica
Categoria com `Category.kind=tecnica` e `Category.is_reportable=false`, usada para movimentos operacionais (ex.: `Pagamento de Fatura`).

## raw_hash
Hash canônico da transação para deduplicação, calculado a partir de campos normalizados (ex.: `sha256(account_id + transaction_date + amount + description_norm)`).

## classification_source
Campo da transação que registra a origem da classificação: `merchant_map`, `rule`, `similarity`, `manual` ou `unclassified`.

## import parser
Parser dedicado para um `file_type` específico, responsável por validar layout CSV e converter para formato canônico.

## MerchantMap
Tabela de mapeamento entre `merchant_norm` e categoria, usada para classificação automática com base no histórico do usuário.

## merchant_norm
Representação normalizada do estabelecimento derivada da descrição da transação.

## description_raw
Descrição original da transação como veio no CSV.

## description_norm
Descrição normalizada para reduzir variações textuais e facilitar classificação.

## ReviewQueue
Fila de transações que exigem decisão manual por ausência de match ou baixa confiança.

## Regras YAML
Conjunto de regras declarativas para classificar transações por padrões textuais e contexto.

## Similaridade fuzzy
Comparação aproximada de strings para localizar merchants similares quando não há match exato.

## Cash basis
Abordagem em que gastos são reconhecidos conforme movimentos mensais efetivos na fatura/extrato.
