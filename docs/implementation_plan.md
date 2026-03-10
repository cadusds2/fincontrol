# Plano de Implementação (MVP)

Documento tático para execução incremental do Finance Agent.

## Como usar este plano (agentes e time)

1. Confirmar restrições e decisões em [`docs/decisions.md`](decisions.md).
2. Selecionar a fase atual e executar apenas o escopo dela.
3. Para cada fase, cumprir: **entradas → tarefas → validação → critério de saída**.
4. Não antecipar escopo de fases futuras sem justificativa explícita.
5. Atualizar documentação impactada no mesmo commit.

## Regras transversais (válidas em todas as fases)

- Sem LLM no MVP.
- Sem autodetecção de tipo de arquivo.
- Sem autodetecção de conta/cartão.
- Manter suporte a múltiplas contas/cartões por banco.
- Excluir categorias técnicas dos relatórios principais.
- Preservar cash basis para parcelas.

Referências: [`AGENTS.md`](../AGENTS.md), [`docs/import_pipeline.md`](import_pipeline.md), [`docs/classification_strategy.md`](classification_strategy.md), [`docs/categories.md`](categories.md).

---

## Fase 0 — Fundação do repositório

### Objetivo
Estabelecer baseline documental e operacional para iniciar implementação sem ambiguidade.

### Entradas obrigatórias
- [`README.md`](../README.md)
- [`AGENTS.md`](../AGENTS.md)
- [`docs/product_overview.md`](product_overview.md)
- [`docs/decisions.md`](decisions.md)

### Tarefas acionáveis
- [ ] Validar consistência entre README, AGENTS, docs e prompts.
- [ ] Garantir links internos navegáveis.
- [ ] Consolidar regras de execução por agentes.

### Validação mínima
- Leitura guiada do repositório está explícita e sem conflito.

### Critério de saída
- Agente consegue iniciar Fase 1 com contexto fechado.

---

## Fase 1 — Modelo de dados e administração básica

### Objetivo
Implementar entidades centrais no Django ORM com consistência de domínio.

### Entradas obrigatórias
- [`docs/domain_model.md`](domain_model.md)
- [`docs/categories.md`](categories.md)
- [`docs/decisions.md`](decisions.md)

### Tarefas acionáveis
- [ ] Criar modelos: `Account`, `ImportBatch`, `Transaction`, `MerchantMap`, `ReviewQueue`, `Budget`, `Category`.
- [ ] Criar migrações iniciais.
- [ ] Incluir cadastro administrativo mínimo para contas e categorias.
- [ ] Garantir suporte a categorias técnicas com sinalização de reportabilidade.

### Validação mínima
- Integridade de relacionamentos e constraints.
- Seed mínimo de categorias essenciais.

### Critério de saída
- Schema funcional e aderente a `docs/domain_model.md`.

---

## Fase 2 — Importação manual de CSV

### Objetivo
Entregar ingestão manual com rastreabilidade por lote e deduplicação básica.

### Entradas obrigatórias
- [`docs/import_pipeline.md`](import_pipeline.md)
- [`docs/domain_model.md`](domain_model.md)
- [`docs/decisions.md`](decisions.md)

### Tarefas acionáveis
- [ ] Criar tela/formulário de upload com seleção manual de tipo e conta/cartão.
- [ ] Implementar criação e atualização de status de `ImportBatch`.
- [ ] Implementar parsers dos quatro layouts suportados no MVP.
- [ ] Transformar registros para formato canônico de `Transaction`.
- [ ] Aplicar deduplicação por hash canônico.

### Validação mínima
- Importação de CSV válido com feedback de sucesso/erro.
- Reimportação não gera duplicação acidental relevante.

### Critério de saída
- Fluxo de importação funcional ponta a ponta, com rastreabilidade.

---

## Fase 3 — Classificação automática sem LLM

### Objetivo
Classificar transações com pipeline determinístico, auditável e transparente.

### Entradas obrigatórias
- [`docs/classification_strategy.md`](classification_strategy.md)
- [`docs/categories.md`](categories.md)
- [`docs/decisions.md`](decisions.md)

### Tarefas acionáveis
- [ ] Implementar normalização textual.
- [ ] Implementar classificação por `MerchantMap`.
- [ ] Implementar motor de regras YAML.
- [ ] Implementar fallback por similaridade fuzzy.
- [ ] Encaminhar baixa confiança para `ReviewQueue`.

### Validação mínima
- Cada transação termina classificada ou em revisão.
- Origem da classificação registrada (`merchant_map`, `rule`, `similarity`, `manual`, `unclassified`).

### Critério de saída
- Pipeline completo ativo sem uso de LLM.

---

## Fase 4 — Revisão manual e aprendizado

### Objetivo
Fechar ciclo humano-no-loop e melhorar assertividade ao longo do uso.

### Entradas obrigatórias
- [`docs/classification_strategy.md`](classification_strategy.md)
- [`docs/domain_model.md`](domain_model.md)

### Tarefas acionáveis
- [ ] Criar tela de fila de revisão.
- [ ] Permitir edição e confirmação de categoria.
- [ ] Atualizar `MerchantMap` de forma segura após revisão.
- [ ] Registrar origem final como `manual` quando aplicável.

### Validação mínima
- Revisor consegue processar pendências de ponta a ponta.

### Critério de saída
- Queda observável de reincidência de casos ambíguos iguais.

---

## Fase 5 — Relatórios e orçamento básico

### Objetivo
Entregar visão mensal simples de consumo real.

### Entradas obrigatórias
- [`docs/categories.md`](categories.md)
- [`docs/decisions.md`](decisions.md)

### Tarefas acionáveis
- [ ] Implementar relatório por categoria e período.
- [ ] Excluir categorias técnicas dos totais principais.
- [ ] Exibir visão inicial de orçamento (`Budget` vs realizado).

### Validação mínima
- Totais de consumo não incluem `Pagamento de Fatura` e `Transferência Interna`.

### Critério de saída
- Usuário visualiza consumo sem distorção por transações técnicas.

---

## Fase 6 — Hardening do MVP

### Objetivo
Preparar versão estável para uso contínuo.

### Entradas obrigatórias
- Fases 1 a 5 concluídas.

### Tarefas acionáveis
- [ ] Cobrir fluxos críticos com testes automatizados (importação, classificação, revisão).
- [ ] Endurecer tratamento de erros e observabilidade.
- [ ] Revisar UX dos fluxos principais.
- [ ] Consolidar documentação operacional final.

### Validação mínima
- Fluxos críticos estáveis em execução recorrente.

### Critério de saída
- MVP pronto para rotina mensal do usuário-alvo.
