# Estratégia de Classificação (MVP)

## Princípios

- Pipeline determinístico e auditável.
- Sem LLM no MVP.
- Toda transação termina classificada ou em `ReviewQueue`.
- Origem da classificação registrada em `Transaction.classification_source`.

## Pipeline oficial (ordem obrigatória)

1. **Normalização**
2. **MerchantMap**
3. **Regras YAML**
4. **Similaridade fuzzy**
5. **ReviewQueue**

## Por que MerchantMap vem antes das regras YAML

`MerchantMap` é aplicado antes porque:
- é mais específico para o histórico real do usuário;
- tende a ter maior precisão para merchants recorrentes;
- evita custo de avaliação de regras mais genéricas quando já existe mapeamento confiável.

## Etapas detalhadas

### 1) Normalização
- Gerar `description_norm` e `merchant_norm` a partir de `description_raw`.
- Aplicar normalizações estáveis (casefold, remoção de ruído textual e espaços redundantes).

### 2) MerchantMap
- Buscar `merchant_norm` no mapa.
- Em caso de match, atribuir categoria diretamente.
- Registrar `classification_source=merchant_map`.

### 3) Regras YAML
- Avaliar regras declarativas por prioridade.
- Primeira regra válida vence.
- Registrar `classification_source=rule`.

### 4) Similaridade fuzzy
- Comparar `merchant_norm` com base conhecida.
- Aplicar categoria apenas se score >= limiar definido em configuração.
- Registrar `classification_source=similarity`.

### 5) ReviewQueue
- Se nenhuma etapa anterior produzir classificação confiável, criar item pendente.
- Registrar `classification_source=unclassified` até decisão humana.

## Classificação manual

Ao revisar uma pendência:
- usuário define categoria final;
- sistema atualiza a transação com `classification_source=manual`;
- sistema pode inserir/atualizar `MerchantMap` para aprendizado futuro.

## Regras de transparência

- Toda classificação deve ser explicável por fonte (`merchant_map`, `rule`, `similarity`, `manual`, `unclassified`).
- Logs não devem expor dados sensíveis completos.
- Mudanças de comportamento devem ser rastreáveis por versão de regras YAML.
