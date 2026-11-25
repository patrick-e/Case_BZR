# Relatório de Auditoria — Limpeza e Conciliação de Dados

Relatório gerado automaticamente pelo pipeline de saneamento (`src/limpeza.py`) a partir dos arquivos brutos de `case-candidato/dados/`.

## 1. Resumo Executivo

| Métrica de Processamento | Quantidade | Descrição |
|---|---:|---|
| **Precatórios Consolidados** | `6` | Base unificada (`output/precatorios_limpos.csv`) após cruzamento Hub, Tribunal e Apresentações. |
| **Eventos Financeiros Válidos** | `8` | Pagamentos e estornos normalizados e deduplicados (`output/pagamentos_limpos.json`). |
| **Transformações / Correções** | `20` | Normalizações de máscara CNJ, encoding, datas, fuso horário, valores PT-BR, retificações e estornos. |
| **Registros Descartados** | `4` | Eventos inválidos (duplicatas exatas, valores nulos/negativos ou sem processo). |
| **Itens em Dúvida (Revisão)** | `7` | Divergências cadastrais ou anomalias que requerem validação de negócio/tribunal. |

## 2. Base Consolidada de Precatórios (`precatorios_limpos.csv`)

| Processo (CNJ) | Ente Devedor | Valor de Face (R$) | Apresentado em (BRT) | Prazo Constitucional | Total Pago Líquido (R$) | Status |
|---|---|---:|---|---|---:|---|
| `0012345-10.2019.8.26.0053` | Município de São Paulo | 45000.00 | `2025-04-02` | `2026-12-31` | 18000.50 | `conciliado` |
| `0023456-21.2020.8.26.0053` | Município de São Paulo | 30000.00 | `2025-04-03` | `2027-12-31` | 9200.00 | `em_duvida` |
| `0034567-32.2018.8.26.0405` | Estado de São Paulo | 12500.00 | `2024-02-29` | `2025-12-31` | 0.00 | `conciliado` |
| `0045678-43.2021.5.02.0011` | União | 9800.00 | `2025-04-02` | `2026-12-31` | 3000.00 | `em_duvida` |
| `0056789-54.2017.4.03.6100` | Estado de São Paulo | 22000.00 | `2025-04-02` | `2026-12-31` | 0.00 | `em_duvida` |
| `0067890-65.2016.8.26.0053` | Município de São Paulo | 7000.00 | `2023-12-31` | `2025-12-31` | 4000.00 | `em_duvida` |

## 3. Eventos Financeiros Limpos (`pagamentos_limpos.json`)

| Evento ID | Processo (CNJ) | Tipo | Valor (R$) | Data Pagamento | Atualizado em |
|---|---|---|---:|---|---|
| `ev-001` | `0012345-10.2019.8.26.0053` | `pagamento` | 15500.00 | `2025-03-10` | `2025-03-11T09:00:00-03:00` |
| `ev-002` | `0012345-10.2019.8.26.0053` | `pagamento` | 2500.50 | `2025-04-10` | `2025-04-10T09:00:00-03:00` |
| `ev-003` | `0023456-21.2020.8.26.0053` | `pagamento` | 8000.00 | `2025-05-02` | `2025-05-02T11:00:00-03:00` |
| `ev-005` | `0023456-21.2020.8.26.0053` | `pagamento` | 1200.00 | `2025-06-01` | `2025-06-01T10:00:00-03:00` |
| `ev-006` | `0034567-32.2018.8.26.0405` | `pagamento` | 5000.00 | `2025-02-20` | `2025-02-20T10:00:00-03:00` |
| `ev-007` | `0034567-32.2018.8.26.0405` | `estorno` | 5000.00 | `2025-02-21` | `2025-02-21T10:00:00-03:00` |
| `ev-008` | `0045678-43.2021.5.02.0011` | `pagamento` | 3000.00 | `2025-07-15` | `2025-07-15T10:00:00-03:00` |
| `ev-011` | `0067890-65.2016.8.26.0053` | `pagamento` | 4000.00 | `2025-08-10` | `2025-08-10T10:00:00-03:00` |

## 4. Registros Corrigidos (Transformações Aplicadas)

| Origem | Identificador | Campo | Valor Original | Valor Final | Motivo da Correção |
|---|---|---|---|---|---|
| `apresentacoes.json` | `0045678-43.2021.5.02.0011` | `apresentado_em` | `2025-04-02T23:30:00-03:00` | `2025-04-02` | Timestamp convertido para fuso America/Sao_Paulo (-03:00) e extraída data civil. |
| `apresentacoes.json` | `0056789-54.2017.4.03.6100` | `apresentado_em` | `2025-04-03T01:00:00Z` | `2025-04-02` | Timestamp convertido para fuso America/Sao_Paulo (-03:00) e extraída data civil. |
| `hub.csv` | `0012345-10.2019.8.26.0053` | `ente` | `MUNICIPIO DE SAO PAULO` | `Município de São Paulo` | Padronizada grafia/acentuação e caixa do nome do ente devedor. |
| `hub.csv` | `0012345-10.2019.8.26.0053` | `prazo_pagamento` | `2027-12-31` | `2026-12-31` | Recalculado prazo constitucional (corte <= 02/04 no fuso de Brasília para apresentação em 2025-04-02). |
| `hub.csv` | `0023456-21.2020.8.26.0053` | `processo` | `00234562120208260053` | `0023456-21.2020.8.26.0053` | Adicionada pontuação do padrão CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO). |
| `hub.csv` | `0056789-54.2017.4.03.6100` | `prazo_pagamento` | `2027-12-31` | `2026-12-31` | Recalculado prazo constitucional (corte <= 02/04 no fuso de Brasília para apresentação em 2025-04-02). |
| `tribunal.csv` | `arquivo` | `encoding` | `cp1252 (Windows-1252 / Latin-1)` | `utf-8` | Arquivo salvo em Windows-1252/Latin-1 (pelo Excel) em vez de UTF-8 previsto na documentação. |
| `tribunal.csv` | `arquivo` | `delimitador` | `;` | `,` | Detectado delimitador ';' (gerado pelo Excel) em vez de ',' previsto na documentação. |
| `tribunal.csv` | `0012345-10.2019.8.26.0053` | `valor_face` | `45.000,00` | `45000.00` | Convertido valor monetário do formato PT-BR (ponto de milhar e vírgula decimal) para Decimal. |
| `tribunal.csv` | `0023456-21.2020.8.26.0053` | `valor_face` | `30.000,00` | `30000.00` | Convertido valor monetário do formato PT-BR (ponto de milhar e vírgula decimal) para Decimal. |
| `tribunal.csv` | `0034567-32.2018.8.26.0405` | `valor_face` | `12.500,00` | `12500.00` | Convertido valor monetário do formato PT-BR (ponto de milhar e vírgula decimal) para Decimal. |
| `tribunal.csv` | `0045678-43.2021.5.02.0011` | `valor_face` | `9.800,00` | `9800.00` | Convertido valor monetário do formato PT-BR (ponto de milhar e vírgula decimal) para Decimal. |
| `tribunal.csv` | `0067890-65.2016.8.26.0053` | `valor_face` | `7.000,00` | `7000.00` | Convertido valor monetário do formato PT-BR (ponto de milhar e vírgula decimal) para Decimal. |
| `pagamentos.json` | `ev-002` | `valor` | `2.500,50` | `2500.50` | Convertido valor em string PT-BR ('2.500,50') para Decimal. |
| `pagamentos.json` | `ev-002` | `data_pagamento` | `10/04/2025` | `2025-04-10` | Convertida data de pagamento de DD/MM/AAAA para AAAA-MM-DD. |
| `pagamentos.json` | `ev-002` | `valor` | `2.500,50` | `2500.50` | Convertido valor em string PT-BR ('2.500,50') para Decimal. |
| `pagamentos.json` | `ev-002` | `data_pagamento` | `10/04/2025` | `2025-04-10` | Convertida data de pagamento de DD/MM/AAAA para AAAA-MM-DD. |
| `pagamentos.json` | `ev-005` | `processo` | `00234562120208260053` | `0023456-21.2020.8.26.0053` | Adicionada máscara CNJ ao número do processo no evento de pagamento. |
| `pagamentos.json` | `ev-001` | `valor` | `15000.00` | `15500.00` | Evento retificado pelo tribunal: mantida versão mais recente (atualizado_em 2025-03-11T09:00:00-03:00 > 2025-03-10T10:00:00-03:00). |
| `pagamentos.json` | `ev-007` | `tipo` | `+5000.00 (soma indevida)` | `-5000.00 (estorno abatido)` | Evento de estorno (ev-007) subtraído do total pago do processo 0034567-32.2018.8.26.0405. |

## 5. Registros Descartados (Quarentena)

| Origem | Identificador | Campo | Valor Original | Motivo do Descarte |
|---|---|---|---|---|
| `pagamentos.json` | `ev-002` | `evento_id` | `ev-002` | Duplicata exata de evento_id descartada. |
| `pagamentos.json` | `ev-004` | `valor` | `None` | Evento descartado: valor nulo ou não numérico. |
| `pagamentos.json` | `ev-009` | `valor` | `-200` | Evento descartado e enviado para auditoria: valor <= 0 (-200.00) com tipo='pagamento' (viola CHECK valor > 0 do banco). |
| `pagamentos.json` | `ev-010` | `processo` | `` | Evento descartado: campo 'processo' vazio ou fora do padrão CNJ. |

## 6. Registros em Dúvida (Fila de Alinhamento)

| Origem | Identificador | Campo | Valor Original | Valor Adotado | Justificativa / Ponto de Atenção |
|---|---|---|---|---|---|
| `hub.csv vs tribunal.csv` | `0023456-21.2020.8.26.0053` | `valor_face` | `{'hub': '31000.00', 'tribunal': '30000.00'}` | `30000.00` | Valor de face diverge entre Hub (31000.00) e Tribunal (30000.00). Adotado valor do Tribunal e marcado para revisão. |
| `hub.csv vs tribunal.csv` | `0045678-43.2021.5.02.0011` | `ente_devedor` | `{'hub': 'Município de Santos', 'tribunal': 'União'}` | `União` | Ente devedor diverge entre Hub ('Município de Santos') e Tribunal ('União'). Adotado valor do Tribunal e marcado para revisão. |
| `hub.csv (ausente no tribunal.csv)` | `0056789-54.2017.4.03.6100` | `cadastro_precatorio` | `0056789-54.2017.4.03.6100` | `0056789-54.2017.4.03.6100` | Processo consta no hub.csv e apresentacoes.json, mas não veio no arquivo semanal tribunal.csv. Mantido na base com status 'em_duvida'. |
| `tribunal.csv (ausente no hub.csv)` | `0067890-65.2016.8.26.0053` | `cadastro_precatorio` | `None` | `0067890-65.2016.8.26.0053` | Processo existe em tribunal.csv, apresentacoes.json e possui pagamento, mas não estava cadastrado no hub.csv. Incluído na base limpa para confirmação. |
| `pagamentos.json` | `ev-001` | `valor` | `15000.00` | `15500.00` | Mesmo evento_id (ev-001) enviado com valor alterado de 15000.00 para 15500.00. Assumida substituição pelo mais recente; confirmar com tribunal. |
| `pagamentos.json` | `ev-009` | `valor` | `-200` | `None` | Evento ev-009 do processo 0056789-54.2017.4.03.6100 veio com tipo='pagamento' e valor negativo (-200.00). Confirmar com tribunal se é um estorno mal classificado. |
| `pagamentos.json vs apresentacoes.json` | `ev-001` | `data_pagamento` | `2025-03-10` | `2025-03-10` | Data de pagamento (2025-03-10) do processo 0012345-10.2019.8.26.0053 é anterior à data de apresentação (2025-04-02). |
