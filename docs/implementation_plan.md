# Plano de Implementação (MVP)

## Como executar este plano

1. Confirmar restrições e decisões em `docs/decisions.md`.
2. Executar por fase, sem antecipar escopo.
3. Validar cada fase com checks objetivos.
4. Atualizar documentação impactada no mesmo commit.

## Regras transversais

- Sem LLM no MVP.
- Sem autodetecção de tipo de arquivo.
- Sem autodetecção de conta/cartão.
- Suporte explícito a múltiplas contas e cartões por banco.
- Exclusão de categorias técnicas dos relatórios principais.
- Parcelamento em cash basis.

---

## Fase 0 — Fundação documental

### Objetivo
Fechar base documental e eliminar ambiguidades do MVP.

### Tarefas
- [ ] Revisar consistência entre README, AGENTS e docs.
- [ ] Confirmar taxonomia e termos canônicos (`Category.kind`, `Category.is_reportable`).
- [ ] Confirmar pipeline oficial de importação e classificação.

### Critério de saída
Documentação coerente e pronta para implementação assistida por agente.

---

## Fase 1 — Setup Django + modelo de dados

### Objetivo
Colocar o projeto Django funcional com entidades centrais no admin.

### Tarefas acionáveis
- [ ] Criar projeto Django.
- [ ] Criar apps base: `accounts`, `imports`, `transactions`, `classification`, `reports`.
- [ ] Registrar apps no `settings`.
- [ ] Implementar models do MVP: `Account`, `ImportBatch`, `Transaction`, `Category`, `MerchantMap`, `ReviewQueue`, `Budget`.
- [ ] Criar migrações iniciais.
- [ ] Registrar models no Django Admin.
- [ ] Criar seed inicial de categorias de consumo.
- [ ] Criar seed inicial de categorias técnicas.
- [ ] Validar via admin o cadastro e a visualização de dados básicos.

### Validação mínima
- [ ] `python manage.py makemigrations --check` sem alterações pendentes.
- [ ] `python manage.py migrate` executa sem erro.
- [ ] Admin abre e permite CRUD básico de `Account`, `Category` e `Transaction`.

### Critério de saída
Base de dados e administração inicial prontas para iniciar importação.

---

## Fase 2 — Importação manual de CSV

### Objetivo
Entregar ingestão manual com parser dedicado e deduplicação canônica.

### Tarefas acionáveis
- [ ] Criar formulário de upload com seleção manual de `file_type` e `account_id`.
- [ ] Criar ciclo de status do `ImportBatch`.
- [ ] Implementar os quatro parsers do MVP.
- [ ] Transformar linhas em `Transaction` canônica.
- [ ] Aplicar deduplicação por `raw_hash` (`account_id + raw_hash`).

### Validação mínima
- [ ] Importação válida gera lote `processed`.
- [ ] Reimportação do mesmo arquivo incrementa `duplicated_rows` e não duplica transações.

### Critério de saída
Fluxo de importação rastreável e idempotente no nível esperado do MVP.

---

## Fase 3 — Classificação automática

### Objetivo
Ativar pipeline determinístico sem LLM.

### Tarefas acionáveis
- [ ] Implementar normalização textual.
- [ ] Implementar match por `MerchantMap`.
- [x] Implementar motor de regras YAML.
- [x] Implementar fallback por similaridade fuzzy.
- [x] Encaminhar baixa confiança para `ReviewQueue`.

### Validação mínima
- [ ] Toda transação termina classificada ou pendente de revisão.
- [ ] `classification_source` preenchido corretamente.

### Critério de saída
Classificação automática funcional e auditável.

---

## Fase 4 — Revisão manual

### Objetivo
Fechar o ciclo humano-no-loop.

### Tarefas acionáveis
- [ ] Implementar listagem e detalhe da `ReviewQueue`.
- [ ] Permitir categorização manual da transação.
- [ ] Atualizar `classification_source` para `manual` quando aplicável.
- [ ] Retroalimentar `MerchantMap` de forma controlada.

### Validação mínima
- [ ] Usuário resolve pendências de ponta a ponta.

### Critério de saída
Fila de revisão operacional com aprendizado incremental.

---

## Fase 5 — Relatórios e orçamento

### Objetivo
Entregar visão de consumo mensal confiável.

### Tarefas acionáveis
- [ ] Relatório por categoria e período.
- [ ] Aplicar filtro por `Category.is_reportable=true` no consumo principal.
- [ ] Exibir orçamento (`Budget`) versus realizado.

### Validação mínima
- [ ] Categorias técnicas não aparecem no total de consumo.

### Critério de saída
Relatórios básicos úteis para uso mensal.

---

## Fase 6 — Estabilização do MVP

### Objetivo
Aumentar robustez para uso recorrente.

### Tarefas acionáveis
- [ ] Cobrir importação, classificação, revisão e relatório com testes automatizados.
- [ ] Endurecer tratamento de erro e logs.
- [ ] Ajustar UX dos fluxos críticos.
- [ ] Consolidar documentação operacional.

### Critério de saída
MVP estável para operação contínua do usuário-alvo.
