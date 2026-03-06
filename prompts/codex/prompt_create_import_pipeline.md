# Prompt Codex — Implementar Pipeline de Importação

Você está implementando o fluxo de importação de CSV do Finance Agent.

## Contexto obrigatório
Leia antes:
1. `AGENTS.md`
2. `docs/import_pipeline.md`
3. `docs/domain_model.md`
4. `docs/decisions.md`
5. `docs/classification_strategy.md`

## Objetivo
Entregar o pipeline de importação manual com rastreabilidade e integração ao classificador.

## Escopo
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
5. Deduplicação básica por hash.
6. Disparo do pipeline de classificação ao final da importação.

## Regras importantes
- Não implementar autodetecção de tipo de arquivo.
- Não implementar autodetecção de conta/cartão.
- Garantir logs de erro úteis sem vazar dados sensíveis.

## Entregável esperado
- Fluxo de importação funcionando ponta a ponta.
- Testes básicos de parser e persistência.
- Documentação atualizada em caso de ajuste de contrato de dados.
