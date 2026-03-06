# Plano de Implementação

Documento tático para execução incremental do MVP.

## Fase 0 — Fundação do repositório

### Objetivo
Estabelecer baseline de documentação e organização inicial.

### Entregas
- Estrutura de docs e prompts.
- Definições de domínio e arquitetura registradas.
- Decisões iniciais consolidadas.

### Critério de saída
- Time e agentes conseguem iniciar implementação sem ambiguidade.

## Fase 1 — Modelo de dados e administração básica

### Objetivo
Implementar entidades centrais no Django ORM.

### Entregas
- Modelos: `Account`, `ImportBatch`, `Transaction`, `MerchantMap`, `ReviewQueue`, `Budget`, `Category`.
- Migrações iniciais.
- Cadastro administrativo mínimo para contas e categorias.

### Critério de saída
- Schema funcional e consistente com `docs/domain_model.md`.

## Fase 2 — Importação manual de CSV

### Objetivo
Entregar fluxo completo de ingestão com rastreabilidade por lote.

### Entregas
- Tela de upload com seleção manual de tipo de arquivo e conta/cartão.
- Parsers iniciais para os quatro layouts suportados no MVP.
- Criação de `ImportBatch` e persistência de `Transaction`.
- Deduplicação básica por hash canônico.

### Critério de saída
- Usuário importa CSVs válidos com feedback claro de sucesso/erros.

## Fase 3 — Classificação automática sem LLM

### Objetivo
Classificar transações com pipeline determinístico e auditável.

### Entregas
- Módulo de normalização textual.
- Classificação por `MerchantMap`.
- Motor de regras YAML.
- Mecanismo de similaridade fuzzy.
- Encaminhamento automático para `ReviewQueue`.

### Critério de saída
- Toda transação importada termina classificada ou em revisão.

## Fase 4 — Revisão manual e aprendizado

### Objetivo
Fechar ciclo humano-no-loop com melhoria incremental.

### Entregas
- Tela de fila de revisão com edição de categoria.
- Ação para confirmar categoria e atualizar MerchantMap.
- Registro da origem final da classificação (`manual` quando aplicável).

### Critério de saída
- Revisor consegue tratar pendências e reduzir reincidência de casos iguais.

## Fase 5 — Relatórios e orçamento básico

### Objetivo
Gerar visão simples e útil de consumo mensal.

### Entregas
- Relatório por categoria e período.
- Exclusão de categorias técnicas nos totais principais.
- Visão inicial de orçamento (`Budget` vs realizado).

### Critério de saída
- Usuário visualiza consumo real sem distorção por transações técnicas.

## Fase 6 — Hardening do MVP

### Objetivo
Preparar versão para uso contínuo.

### Entregas
- Testes automatizados principais (importação, classificação, revisão).
- Melhorias de performance e tratamento de erros.
- Ajustes de UX e documentação operacional.

### Critério de saída
- MVP estável para rotina mensal do usuário-alvo.
