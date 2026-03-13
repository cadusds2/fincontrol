# Visão Geral do Produto

## Problema

Consolidar gastos pessoais de múltiplas contas e cartões é difícil quando os dados chegam em CSVs com layouts diferentes por banco.

## Proposta do Finance Agent

Sistema web que centraliza importação manual de CSV, classifica transações por pipeline determinístico e envia casos ambíguos para revisão manual.

## Objetivo do MVP

Entregar um fluxo completo para:
1. importar CSVs suportados;
2. classificar sem LLM;
3. revisar pendências;
4. gerar relatório simples de consumo por categoria.

## Usuário-alvo inicial

Pessoa física com Nubank e/ou Itaú, com múltiplas contas/cartões e necessidade de controle mensal simples.

## Fontes suportadas no MVP

- extrato_conta_nubank
- fatura_cartao_nubank
- extrato_conta_itau
- fatura_cartao_itau

## Premissas operacionais

- Seleção manual de tipo de arquivo no upload.
- Seleção manual de conta/cartão no upload.
- Sem integração bancária por API.
- Sem LLM no MVP.

## Requisitos funcionais de alto nível

- Cadastro de múltiplas contas/cartões por banco.
- Importação com `ImportBatch` e rastreabilidade.
- Deduplicação por `raw_hash` canônico (`account_id + raw_hash`).
- Classificação: normalização → MerchantMap → regras YAML → similaridade → ReviewQueue.
- Revisão manual com aprendizado incremental em `MerchantMap`.
- Relatórios considerando apenas categorias reportáveis (`Category.is_reportable=true`).

## Requisitos não funcionais

- Simplicidade de operação local (Django + SQLite).
- Reprodutibilidade e transparência da classificação.
- Base preparada para evolução pós-MVP sem quebrar decisões atuais.
