# Pipeline de Importação de CSV

## Objetivo

Detalhar o fluxo de importação manual de extratos/faturas no MVP, com rastreabilidade por lote e preparação para classificação.

## Entrada do usuário (obrigatória)

Na tela de importação, o usuário deve informar:

1. **Tipo de arquivo** (seleção manual):
   - Extrato da conta Nubank
   - Fatura do cartão Nubank
   - Extrato da conta Itaú
   - Fatura do cartão Itaú
2. **Conta/Cartão** (seleção manual):
   - registro de `Account` já cadastrado.
3. **Arquivo CSV**.

Não há autodetecção no MVP.

## Etapas do pipeline

## 1) Recebimento e criação do lote
- Validar presença de tipo, conta/cartão e arquivo.
- Criar `ImportBatch` com status `received`.
- Registrar metadados básicos do arquivo.

## 2) Leitura e validação estrutural
- Ler CSV com parser específico por `file_type`.
- Validar colunas obrigatórias por layout.
- Se falha estrutural total, marcar lote como `failed`.

## 3) Transformação para formato canônico
Para cada linha válida:
- mapear data, descrição, valor, sinal e campos auxiliares;
- preencher `description_raw`;
- gerar `description_norm` e `merchant_norm`;
- identificar metadados de parcela quando disponíveis.

## 4) Deduplicação (escopo MVP)
- Calcular `raw_hash` com combinação estável de campos canônicos.
- Se hash já existir na mesma conta e janela temporal definida, sinalizar como duplicado.
- Não persistir duplicatas óbvias; contabilizar em `duplicated_rows`.

## 5) Persistência de transações
- Criar `Transaction` vinculada a `ImportBatch` e `Account`.
- Definir `classification_source = unclassified` inicialmente.
- Persistir em lote com tratamento de erro por linha.

## 6) Atualização de status do lote
- Atualizar contadores (`total_rows`, `imported_rows`, `duplicated_rows`).
- Definir status final:
  - `processed` (sem erros relevantes);
  - `partial` (com erros/linhas descartadas);
  - `failed` (sem linhas importadas).

## 7) Disparo da classificação
- Ao final da importação, acionar pipeline de classificação para as transações do lote.

## Regras específicas por tipo de origem

- Cada `file_type` terá parser dedicado, com mapeamento explícito de colunas.
- Mudanças de layout bancário exigem atualização versionada do parser correspondente.

## Observabilidade e auditoria

- Todo erro de linha deve registrar contexto mínimo (linha, motivo).
- Não registrar dados sensíveis completos em logs de erro.
- Toda transação deve manter vínculo com `ImportBatch` para rastreio.
