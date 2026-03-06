# Prompt Codex — Criar Modelos de Domínio

Você está implementando os modelos do Finance Agent no Django ORM.

## Contexto obrigatório
Leia antes:
1. `AGENTS.md`
2. `docs/domain_model.md`
3. `docs/categories.md`
4. `docs/decisions.md`
5. `docs/implementation_plan.md`

## Objetivo
Implementar os modelos centrais do MVP:
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
5. Incluir dados seed mínimos para categorias essenciais.

## Restrições
- Sem LLM.
- Sem criação de modelos não justificados pela documentação.
- Manter nomes consistentes com a documentação.

## Entregável esperado
- Modelos e migrações funcionais.
- Breve explicação de decisões técnicas que não estavam explícitas.
