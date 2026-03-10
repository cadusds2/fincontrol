# Prompt Codex — Inicializar Repositório Finance Agent

Você está atuando como engenheiro de software no projeto Finance Agent.

## Objetivo
Configurar a base técnica inicial do projeto Django sem implementar regras de negócio completas.

## Protocolo obrigatório de leitura
Leia nesta ordem antes de executar:
1. [`README.md`](../../README.md)
2. [`AGENTS.md`](../../AGENTS.md)
3. [`docs/product_overview.md`](../../docs/product_overview.md)
4. [`docs/decisions.md`](../../docs/decisions.md)
5. [`docs/architecture.md`](../../docs/architecture.md)
6. [`docs/domain_model.md`](../../docs/domain_model.md)
7. [`docs/implementation_plan.md`](../../docs/implementation_plan.md)

## Escopo desta execução
1. Criar projeto Django base e app(s) iniciais.
2. Configurar SQLite como banco padrão.
3. Organizar estrutura de templates e static.
4. Criar configuração inicial para leitura de regras YAML (sem regras finais).
5. Preparar esqueleto de módulos para importação, classificação, revisão e relatório.
6. Registrar no `README.md` instruções mínimas de execução local, se necessário.

## Restrições invioláveis
- Não implementar LLM.
- Não criar funcionalidades fora do escopo do MVP.
- Não remover/alterar decisões fechadas em `docs/decisions.md`.
- Não antecipar regras de fases futuras sem necessidade.

## Entregável esperado
- Estrutura Django inicial funcional.
- Commits claros por etapa.
- Documentação atualizada quando houver impacto.
- Resumo final com:
  - documentos que guiaram decisões;
  - o que foi implementado;
  - o que ficou explicitamente fora de escopo.
