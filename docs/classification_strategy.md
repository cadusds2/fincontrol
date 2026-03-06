# Estratégia de Classificação (MVP sem LLM)

## Objetivo

Classificar transações de forma determinística e auditável, minimizando trabalho manual sem usar LLM.

## Pipeline oficial do MVP

1. **Normalização**
2. **MerchantMap**
3. **Regras YAML**
4. **Similaridade fuzzy**
5. **ReviewQueue**

## 1) Normalização

Transformar texto bruto para chave estável de comparação.

### Ações esperadas
- caixa baixa;
- remoção de acentos;
- remoção de ruído comum (número de autorização, sufixos recorrentes, etc.);
- colapso de espaços;
- criação de `description_norm` e `merchant_norm`.

## 2) MerchantMap

Primeira fonte de classificação por histórico conhecido.

### Regra
- Se `merchant_norm` existir no `MerchantMap`, atribuir categoria mapeada.
- Definir `classification_source = merchant_map`.
- Definir confiança alta (ex.: `0.95`).

## 3) Regras YAML

Conjunto de regras versionadas para padrões recorrentes.

### Exemplo de critérios de regra
- presença de tokens em `description_norm`;
- prefixos/sufixos;
- combinação com direção (débito/crédito);
- exceções explícitas.

### Resultado
- Categoria atribuída conforme regra mais específica.
- `classification_source = rule`.
- Confiança média-alta (ex.: `0.80` a `0.90`).

## 4) Similaridade fuzzy

Fallback para descrições próximas a padrões conhecidos.

### Estratégia
- Comparar `merchant_norm` com chaves existentes no `MerchantMap`.
- Se score >= limiar (ex.: `0.88`), usar categoria do match.
- `classification_source = similarity`.
- Confiança proporcional ao score.

## 5) ReviewQueue

Encaminhar para revisão quando não houver confiança suficiente.

### Critérios de envio
- sem match nas etapas anteriores;
- conflito entre estratégias;
- score abaixo de limiar;
- regra bloqueada por exceção.

### Resultado
- Criar item pendente em `ReviewQueue`.
- `classification_source = unclassified` ou `manual` após revisão.

## Aprendizado com revisão manual

Após decisão do usuário:

- atualizar `Transaction.category`;
- marcar origem como `manual`;
- opcionalmente inserir/atualizar `MerchantMap` com `merchant_norm` e categoria escolhida.

Isso melhora a assertividade futura sem dependência de LLM.

## Tratamento de categorias técnicas

- Se transação for `Pagamento de Fatura` ou `Transferência Interna`, marcar `is_technical = true`.
- Essas transações ficam fora da análise principal de consumo.

## Metas de qualidade do classificador no MVP

- Alta precisão em merchants recorrentes.
- Redução progressiva de itens em revisão com uso contínuo.
- Transparência do motivo da classificação por transação.
