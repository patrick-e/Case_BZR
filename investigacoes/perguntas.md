<a id="perguntas"></a>
# Perguntas para a Operação e o Tribunal

Pontos que precisam ser confirmados antes de levar a rotina para produção.

---

## Para a Operação

1. **Conflito entre Hub e Tribunal:** quando `valor_face` (`0023456-21.2020.8.26.0053`: R\$ 31.000 vs R\$ 30.000) ou `ente_devedor` (`0045678-43.2021.5.02.0011`: `Município de Santos` vs `União`) divergirem, qual base prevalece? *(No script: usamos o valor do Tribunal e marcamos como `em_duvida`)*.
2. **Processos em apenas uma base:** o processo `0067890-65.2016.8.26.0053` veio no Tribunal e recebeu pagamento (`ev-011`), mas não está no Hub — deve ser cadastrado automaticamente? E o `0056789-54.2017.4.03.6100`, que está no Hub mas não veio no `tribunal.csv`, foi liquidado ou é de outro tribunal (TRF-3)? *(No script: mantivemos ambos como `em_duvida`)*.
3. **Fuso horário no corte de 2 de abril:** todos os horários em UTC (`2025-04-03T01:00:00Z`) devem ser convertidos para Brasília (`-03:00`) antes de aplicar a regra de 2 de abril? *(No script: convertemos para Brasília)*.
4. **Pagamento antes da apresentação:** no processo `0012345-10.2019.8.26.0053`, o pagamento `ev-001` (`10/03/2025`) é anterior à apresentação (`02/04/2025`). O pagamento é válido ou a data de apresentação está errada? *(No script: mantivemos o pagamento e sinalizamos em dúvida)*.
5. **Cadastro de Entes Devedores:** existe uma lista oficial de entes (com CNPJ ou código IBGE) para evitarmos nomes digitados manualmente?

---

## Para o Tribunal

1. **Retificação de `evento_id` (`ev-001`):** quando o mesmo `evento_id` reaparece com `atualizado_em` mais novo e valor diferente (`15000.0` → `15500.0`), o novo valor substitui o anterior? *(No script: substituímos pelo mais recente)*.
2. **Valor negativo com tipo `"pagamento"` (`ev-009`):** o valor `-200` é um estorno enviado com o `tipo` errado ou uma falha que deve ser descartada? *(No script: descartamos e sinalizamos em dúvida)*.
3. **Eventos incompletos (`ev-004` e `ev-010`):** eventos enviados com `valor: null` ou `processo: ""` serão reenviados corrigidos nos lotes seguintes? *(No script: descartamos)*.
4. **Especificação de `apresentacoes.json` e `tribunal.csv`:** qual o leiaute oficial de `apresentacoes.json`? O `tribunal.csv` original sai do tribunal em `UTF-8` separado por vírgula?
