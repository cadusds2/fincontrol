# Analise de merchant_norm com CSVs

Use este fluxo apenas para inspecao local de CSVs reais. Os arquivos reais nao devem ser versionados.

```bash
python manage.py analisar_merchant_norm_csv --file-type extrato_conta_nubank caminho/do/extrato.csv
```

O comando usa o parser dedicado e a normalizacao real do projeto, agrupa candidatos em memoria e nao grava `MerchantMap`, `Transaction` ou `ImportBatch`. A criacao de `MerchantMap` continua vinculada a revisao manual/admin, preservando `classification_source` e a rastreabilidade do MVP.
