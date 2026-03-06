# Glossário

## Account
Conta corrente ou cartão de crédito cadastrado no sistema e usado como origem das transações importadas.

## ImportBatch
Lote de importação de um CSV, contendo metadados do processo, status e contadores de sucesso/erro.

## Transaction
Lançamento financeiro individual persistido no sistema, associado a uma conta/cartão e a um lote de importação.

## MerchantMap
Tabela de mapeamento entre `merchant_norm` e categoria, usada para classificação automática de alta confiança.

## merchant_norm
Representação normalizada do estabelecimento/merchant derivada da descrição da transação.

## description_raw
Descrição original da transação exatamente como veio no arquivo CSV.

## description_norm
Descrição normalizada para reduzir variações textuais e facilitar classificação.

## ReviewQueue
Fila de transações que precisam de decisão manual por ausência de match ou baixa confiança.

## Category
Taxonomia de categorias usada na classificação. Pode ser de consumo (reportável) ou técnica (não reportável).

## Categoria técnica
Categoria operacional que não representa consumo real (ex.: `Pagamento de Fatura`, `Transferência Interna`).

## Cash basis
Abordagem em que gastos são reconhecidos conforme movimentos mensais efetivos na fatura/extrato.

## Regras YAML
Conjunto de regras declarativas em arquivos YAML para classificar transações por padrões textuais e contexto.

## Similaridade fuzzy
Técnica de comparação aproximada de strings para identificar merchants semelhantes quando não há match exato.
