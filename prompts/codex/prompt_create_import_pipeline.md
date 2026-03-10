# Prompt Codex — Implementar Pipeline de Importação

Você está implementando o fluxo de importação de CSV do Finance Agent.

## Objetivo
Entregar pipeline de importação manual com rastreabilidade por lote e integração ao classificador.

## Protocolo obrigatório de leitura
Leia antes de implementar:
1. [`AGENTS.md`](../../AGENTS.md)
2. [`docs/import_pipeline.md`](../../docs/import_pipeline.md)
3. [`docs/domain_model.md`](../../docs/domain_model.md)
4. [`docs/decisions.md`](../../docs/decisions.md)
5. [`docs/classification_strategy.md`](../../docs/classification_strategy.md)
6. [`docs/categories.md`](../../docs/categories.md)

## Escopo desta execução
1. Tela/formulário de upload com:
   - seleção manual de tipo de arquivo;
   - seleção manual de conta/cartão;
   - seleção do CSV.
2. Criação de `ImportBatch` e atualização de status.
3. Parsers por tipo de arquivo suportado no MVP:
   - Extrato conta Nubank
   - Fatura cartão Nubank
   - Extrato conta Itaú
   - Fatura cartão Itaú
4. Transformação para formato canônico de `Transaction`.
5. Deduplicação básica por hash canônico.
6. Disparo do pipeline de classificação ao final da importação.

## Regras críticas de domínio
- Não implementar autodetecção de tipo de arquivo.
- Não implementar autodetecção de conta/cartão.
- Preservar estratégia cash basis para compras parceladas no cartão.
- Garantir classificação técnica de `Pagamento de Fatura` e `Transferência Interna`.
- Garantir que categorias técnicas não entrem no relatório principal.
- Garantir logs úteis sem exposição de dados sensíveis.

## Entregável esperado
- Fluxo de importação funcionando ponta a ponta.
- Testes básicos de parser e persistência.
- Documentação atualizada em caso de ajuste de contrato de dados.
- Resumo final com riscos conhecidos e próximos passos sequenciais.
