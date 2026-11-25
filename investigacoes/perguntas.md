<a id="perguntas"></a>
# Matriz de Alinhamento com Stakeholders (Operação e Tribunal)

Este documento relaciona as definições de negócio e de contrato técnico que precisam ser validadas junto à **Operação Interna** e à **Equipe Técnica do Tribunal** antes da promoção definitiva das regras de saneamento para produção ([item 4 do Enunciado](../case-candidato/ENUNCIADO.md#o-que-pedimos)), indicando também a **regra de contingência adotada no pipeline**.

---

## 1. Alinhamento com a Operação e Negócio

| # | Tópico / Caso Concreto | Questão para Definição | Decisão Adotada no Pipeline (Contingência) |
|---|---|---|---|
| **1.1** | **Fonte da Verdade em Conflitos Cadastrais** (`0023456-21.2020.8.26.0053` e `0045678-43.2021.5.02.0011`) | Quando `tribunal.csv` diverge de `hub.csv` em `valor_face` (R\$ 30.000 vs R\$ 31.000) ou `ente_devedor` (`União` vs `Município de Santos`), qual base deve prevalecer automaticamente e qual fila de revisão deve ser acionada? | Adotado o dado oficial do Tribunal, marcando o precatório com `status_conciliacao = 'em_duvida'` e registrando o conflito no relatório de auditoria. |
| **1.2** | **Processos Ausentes entre Bases** (`0067890-65.2016.8.26.0053` e `0056789-54.2017.4.03.6100`) | Precatórios presentes no Tribunal e com pagamento ativo (`ev-011`), mas ausentes no Hub, devem ser cadastrados automaticamente? E processos ativos no Hub que deixaram de vir no arquivo semanal do Tribunal (ex.: TRF-3 / segmento `4.03`) foram liquidados ou pertencem a outra integração? | Ambos foram mantidos na base consolidada com status `em_duvida` para evitar perda do pagamento `ev-011` (R\$ 4.000,00) e preservar o histórico do Hub até confirmação. |
| **1.3** | **Fuso Horário no Corte Constitucional de 2 de Abril** (`0056789-54.2017.4.03.6100`) | Confirma-se que todos os timestamps de `apresentado_em` (como `2025-04-03T01:00:00Z`) devem ser convertidos para o fuso oficial de Brasília (`America/Sao_Paulo`, `-03:00`) antes de aplicar a regra constitucional `<= 02 de abril`? | **Sim.** Timestamps com timezone são convertidos para `America/Sao_Paulo` antes de extrair a data civil (`2025-04-02`, vencimento em `2026-12-31`). |
| **1.4** | **Pagamento Anterior à Data de Apresentação** (`0012345-10.2019.8.26.0053` / `ev-001`) | O pagamento `ev-001` (`2025-03-10`) ocorreu antes da data de apresentação registrada (`2025-04-02`). Trata-se de adiantamento/parcela incontroversa válida ou erro cadastral na data de apresentação? | O pagamento foi contabilizado e o registro foi sinalizado na seção **Em Dúvida** do relatório de auditoria para validação jurídica. |
| **1.5** | **Catálogo Oficial de Entes Devedores** (`ente_devedor`) | A operação dispõe de uma tabela canônica de entes devedores (com CNPJ ou código IBGE) cobrindo União, Estados e Municípios para vínculo por chave estrangeira? | Implementado dicionário canônico (`ENTES_CANONICOS` em [`src/normalizacao.py`](../src/normalizacao.py)) e proposta tabela de domínio `ente_devedor` no SQL. |

---

## 2. Alinhamento com o Tribunal (Integração Técnica)

| # | Tópico / Caso Concreto | Questão para Definição | Decisão Adotada no Pipeline (Contingência) |
|---|---|---|---|
| **2.1** | **Semântica de Retificação no Mesmo `evento_id`** (`ev-001`) | Quando um `evento_id` é reenviado com `atualizado_em` mais recente e novo `valor` (`15000.0` em `10/03` → `15500.0` em `11/03`), o novo registro **substitui** o valor anterior (total = R\$ 15.500,00) ou representa lançamento complementar? | Assumida **substituição pela versão mais recente** (`atualizado_em` maior), registrando a ocorrência como corrigida e sinalizada em dúvida para confirmação. |
| **2.2** | **Valores Negativos com `"tipo": "pagamento"`** (`ev-009`: `-200`) | O evento `ev-009` (`valor: -200`, `tipo: "pagamento"`) é um estorno emitido com a classificação incorreta na origem ou uma falha de exportação que deve ser rejeitada? | **Descartado da soma financeira** (por violar `CHECK (valor > 0)`) e encaminhado para a lista de dúvidas/quarentena. |
| **2.3** | **Eventos Incompletos na Origem** (`ev-004` com `valor: null` e `ev-010` com `processo: ""`) | Em quais cenários o sistema do tribunal exporta eventos sem valor financeiro ou sem número de processo? Esses mesmos `evento_id` serão reenviados completos nos lotes subsequentes de 7 dias? | **Descartados** com registro detalhado no relatório de auditoria. |
| **2.4** | **Formalização de Leiaute (`apresentacoes.json` e `tribunal.csv`)** | Qual é o contrato oficial e a periodicidade de `apresentacoes.json` (ausente na documentação v2.1)? Adicionalmente, confirma-se que `tribunal.csv` é gerado originalmente em `UTF-8` separado por `,` (sendo a conversão para `Windows-1252` e `;` causada exclusivamente pelo Excel na operação)? | O pipeline implementa detecção automática de delimitador (`,` ou `;`), fallback de codificação (`UTF-8` → `Windows-1252`) e parser flexível de datas ISO/timestamps. |
