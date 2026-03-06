# Categorias do Projeto

## Objetivo

Definir taxonomia inicial de categorias para classificação e relatórios do MVP.

## Categorias de consumo (entram nos relatórios principais)

- Alimentação
- Supermercado
- Transporte
- Combustível
- Moradia
- Saúde
- Educação
- Lazer
- Assinaturas
- Compras Online
- Serviços Financeiros
- Impostos e Taxas
- Viagem
- Pets
- Presentes e Doações
- Trabalho
- Outros Consumos

## Categorias técnicas (não entram nos relatórios principais)

- Pagamento de Fatura
- Transferência Interna
- Ajuste/Estorno Técnico

## Diretrizes de uso

- Categorias técnicas devem ter `is_reportable = false`.
- Relatórios de consumo devem filtrar apenas categorias de consumo.
- Caso uma transação seja técnica, ela não deve compor totais de gasto por estilo de vida.

## Observações de evolução

- A lista de consumo pode crescer conforme novos padrões aparecerem.
- Alterações na taxonomia devem ser registradas em `docs/decisions.md`.
