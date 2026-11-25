# perguntas

Lista de dúvidas que precisam ser alinhadas com o **Tribunal** e com a **Operação** antes de colocar a rotina de limpeza e importação em produção (atendendo ao [item 4 do Enunciado](../case-candidato/ENUNCIADO.md#o-que-pedimos)):

---

## Para a Operação / Negócio

1. **Padronização e escopo de `ente_devedor`:**
   - Vocês operam com precatórios das três esferas (União, Estados e Municípios) no mesmo fluxo? Existe uma tabela oficial de entes devedores (ou CNPJ/código IBGE) para normalizarmos grafias como `MUNICIPIO DE SAO PAULO` → `Município de São Paulo`?
2. **Conflito de cadastro entre `hub.csv` e `tribunal.csv` (Fonte da Verdade):**
   - Quando o `tribunal.csv` diverge do `hub.csv` — como no processo `0023456-21.2020.8.26.0053` (valor de face `R$ 30.000,00` no Tribunal vs `R$ 31.000,00` no Hub) e no processo `0045678-43.2021.5.02.0011` (`União` no Tribunal vs `Município de Santos` no Hub) — qual base prevalece ou qual fila de revisão manual deve ser acionada?
3. **Processos presentes em apenas uma das bases:**
   - O processo `0067890-65.2016.8.26.0053` está em `tribunal.csv`, foi apresentado e já teve pagamento (`ev-011` de R$ 4.000,00), mas não está no `hub.csv`. Ele deve ser cadastrado automaticamente na importação?
   - E o processo `0056789-54.2017.4.03.6100`, que está no `hub.csv` mas sumiu do `tribunal.csv`, foi liquidado, cancelado ou é de outro tribunal (TRF-3, segmento `4.03`)?
4. **Regra de fuso horário na data de corte de 2 de abril:**
   - Para o cálculo constitucional do `prazo_pagamento`, devemos converter todos os timestamps de `apresentado_em` (como `2025-04-03T01:00:00Z`) para o fuso horário de Brasília (`America/Sao_Paulo`, `-03:00`) antes de aplicar a regra `<= 02 de abril`?
5. **Pagamento anterior à data de apresentação:**
   - No processo `0012345-10.2019.8.26.0053`, o pagamento `ev-001` (`2025-03-10`) ocorreu antes da data de apresentação (`2025-04-02`). Esse pagamento é válido (ex.: parcela incontroversa/erro na data de apresentação) ou deve ser bloqueado para auditoria?

---

## Para o Tribunal (Integração)

1. **Regra de retificação de eventos com mesmo `evento_id` (`ev-001`):**
   - Quando um `evento_id` reaparece com `atualizado_em` mais recente e outro `valor` (como `ev-001` mudando de `15000.0` para `15500.0`), o novo registro **substitui** o valor anterior (total = R$ 15.500,00) ou representa uma diferença complementar?
2. **Semântica de valores negativos com `"tipo": "pagamento"` (`ev-009`):**
   - O evento `ev-009` (`valor: -200`, `tipo: "pagamento"`) é um estorno/ajuste enviado com o `tipo` errado ou é um erro de geração que deve ser rejeitado?
3. **Eventos com `valor: null` (`ev-004`) ou `processo: ""` (`ev-010`):**
   - Sob quais condições o sistema do tribunal exporta eventos sem valor ou sem processo? O tribunal reenviará esses mesmos `evento_id` corrigidos nos lotes seguintes?
4. **Contrato do arquivo `apresentacoes.json` e `tribunal.csv`:**
   - Qual é a periodicidade e o leiaute oficial de `apresentacoes.json` (ausente da versão 2.1 da documentação)?
   - O arquivo `tribunal.csv` original sai do tribunal com vírgula (`,`) ou ponto e vírgula (`;`)? (Para confirmarmos se a troca para `;` ocorre 100% na etapa manual de Excel da operação).
