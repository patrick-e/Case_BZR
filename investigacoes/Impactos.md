# Impactos no Negócio e na Operação

Abaixo estão consolidados os impactos gerados pelas falhas mapeadas em [`investigacao.md`](investigacao.md) e classificadas em [`diagnostico.md`](diagnostico.md):

---

## 1. Inflação e distorção do saldo pago (Impacto Financeiro Direto)
- **Pagamentos multiplicados:** Como o tribunal reenvia os eventos dos últimos 7 dias diariamente, o arquivo contém duplicatas (`ev-002`) e retificações (`ev-001`), e a tabela `pagamento` não tem `UNIQUE (evento_id)`, cada reenvio ou reexecução manual do script soma novamente valores já contabilizados.
- **Estornos somados como pagamentos:** O evento `ev-007` (`estorno` de R$ 5.000,00 no processo `0034567-32.2018.8.26.0405`), ao ser somado em vez de subtraído, gera um erro de **R$ 10.000,00** no saldo daquele processo (deveria zerar o pagamento `ev-006` de R$ 5.000,00, mas o total pago passa a constar como R$ 10.000,00).

## 2. Perda silenciosa de eventos financeiros (Cegueira Operacional)
- Como o script ignora falhas sem gerar log ou alerta ([item 5 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional)), pagamentos reais como `ev-002` (`"2.500,50"`), `ev-005` (CNJ sem máscara) e `ev-011` (R$ 4.000,00 de processo ausente no Hub) deixam de entrar no sistema sem que a operação saiba.
- Eventos anômalos (`ev-004` com `null`, `ev-009` com `-200`, `ev-010` sem número de processo) também desaparecem sem auditoria.

## 3. Priorização errada da carteira de precatórios (Impacto Estratégico)
- A equipe prioriza a carteira com base no `prazo_pagamento` ([item 4 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional)).
- Devido ao erro na data limite de `02/04` e à falta de conversão do fuso UTC (`Z`) para Brasília (`-03:00`), dois dos cinco processos do [`hub.csv`](../case-candidato/dados/hub.csv) (`0012345-10.2019.8.26.0053` e `0056789-54.2017.4.03.6100`, somando **R$ 67.000,00** em valor de face) tiveram a previsão de recebimento empurrada de **dez/2026 para dez/2027** (1 ano de atraso na projeção de caixa).

## 4. Quebra da conciliação semanal entre Hub e Tribunal (Risco Cadastral)
- O uso de `TEXT` livre sem normalização para `ente_devedor` (`MUNICIPIO DE SAO PAULO` vs `Município de São Paulo`) e a mistura de CNJ com e sem pontuação fazem a conferência exata do operador falhar mesmo para registros que representam o mesmo processo/ente.
- Enquanto o operador lida com falsos erros de formatação (agravados pelo Excel alterando `,` para `;` em `tribunal.csv`), divergências reais graves passam despercebidas:
  - Diferença de **R$ 1.000,00** no `valor_face` do processo `0023456-21.2020.8.26.0053` (`31000.00` vs `30.000,00`).
  - Troca de devedor entre `Município de Santos` e `União` no processo `0045678-43.2021.5.02.0011` (alterando completamente o risco de crédito e a esfera orçamentária).
  - Precatórios inteiros presentes em uma base e ausentes na outra (`0056789-54.2017.4.03.6100` e `0067890-65.2016.8.26.0053`).
