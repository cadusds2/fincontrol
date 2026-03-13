# Taxonomia de Categorias (MVP)

## Decisão do MVP

Para o MVP, a taxonomia oficial é **simples e estável**. O objetivo é reduzir ambiguidade na classificação e acelerar a revisão manual.

A entidade `Category` usa dois campos canônicos:
- `Category.kind`: define se a categoria é de `consumo` ou `tecnica`.
- `Category.is_reportable`: define se entra nos relatórios principais de consumo.

Regra de consistência no MVP:
- `kind=consumo` => `is_reportable=true`
- `kind=tecnica` => `is_reportable=false`

Não usar nomenclaturas paralelas como `include_in_reports` ou `is_technical` na documentação do MVP.

## Categorias de consumo (MVP)

- Moradia
- Alimentação
- Transporte
- Saúde
- Lazer
- Assinaturas
- Educação
- Compras
- Contas/Serviços
- Investimentos
- Outros

Todas as categorias de consumo são `kind=consumo` e `is_reportable=true`.

## Categorias técnicas (MVP)

- Pagamento de Fatura
- Transferência Interna
- Movimentação de Investimentos

Todas as categorias técnicas são `kind=tecnica` e `is_reportable=false`.

## Evoluções pós-MVP (não obrigatórias agora)

Detalhamento adicional (subcategorias como "Supermercado", "Farmácia", "Streaming" etc.) fica como evolução futura e **não é pré-requisito de implementação do MVP**.
