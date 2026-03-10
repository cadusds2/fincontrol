# Prompt Codex — Criar Modelos de Domínio

Você está implementando os modelos do Finance Agent no Django ORM.

## Objetivo
Implementar os modelos centrais do MVP com aderência estrita ao domínio documentado.

## Protocolo obrigatório de leitura
Leia antes de implementar:
1. [`AGENTS.md`](../../AGENTS.md)
2. [`docs/domain_model.md`](../../docs/domain_model.md)
3. [`docs/categories.md`](../../docs/categories.md)
4. [`docs/decisions.md`](../../docs/decisions.md)
5. [`docs/implementation_plan.md`](../../docs/implementation_plan.md)

## Escopo desta execução
Implementar:
- `Account`
- `ImportBatch`
- `Transaction`
- `MerchantMap`
- `ReviewQueue`
- `Budget`
- `Category`

## Requisitos específicos
1. Incluir campos de parcelas em `Transaction`:
   - `is_installment`
   - `installment_current`
   - `installment_total`
   - `installment_key`
2. Suportar categorias técnicas (`Pagamento de Fatura`, `Transferência Interna`) e sinalização de reportabilidade.
3. Definir relacionamentos e constraints coerentes com o domínio.
4. Gerar migrações iniciais.
5. Incluir seed mínimo para categorias essenciais.

## Restrições invioláveis
- Sem LLM.
- Sem criação de modelos não justificados na documentação.
- Manter nomes consistentes com os documentos oficiais.
- Não quebrar decisões registradas em `docs/decisions.md`.

## Entregável esperado
- Modelos e migrações funcionais.
- Explicação breve de decisões técnicas não explícitas na documentação.
- Resumo final indicando quais documentos foram usados para cada decisão estrutural.
