# Impactos no Negócio

Efeitos diretos das falhas encontradas na carteira de precatórios:

---

<a id="1-inflação-e-distorção-do-saldo-pago-impacto-financeiro-direto"></a>
## Saldo Pago Inflado

- **Pagamentos duplicados:** sem `UNIQUE (evento_id)` no banco, o reenvio diário dos últimos 7 dias e as reexecuções manuais somam os mesmos pagamentos repetidas vezes (`ev-001` e `ev-002`).
- **Estorno somado (+R\$ 10.000,00 de erro):** no processo `0034567-32.2018.8.26.0405`, o estorno `ev-007` (R\$ 5.000,00) é somado ao pagamento `ev-006` (R\$ 5.000,00). O sistema mostra **R\$ 10.000,00 pagos** quando o saldo real é **R\$ 0,00**.

---

## Pagamentos Perdidos sem Alerta

Como o script ignora erros em silêncio:
- **R\$ 7.700,50 em pagamentos válidos deixam de entrar:** `ev-002` (R\$ 2.500,50 em formato PT-BR), `ev-005` (R\$ 1.200,00 sem máscara CNJ) e `ev-011` (R\$ 4.000,00 de processo não cadastrado no Hub).
- **Erros do tribunal passam despercebidos:** `ev-004` (`null`), `ev-009` (`-200`) e `ev-010` (sem processo) somem sem ir para revisão.

---

## Previsão de Caixa Atrasada em 1 Ano

Dois processos que entraram até 2 de abril tiveram o vencimento calculado para **dezembro/2027** em vez de **dezembro/2026**:
- `0012345-10.2019.8.26.0053` (R\$ 45.000,00)
- `0056789-54.2017.4.03.6100` (R\$ 22.000,00)

Isso desloca **R\$ 67.000,00** da carteira em um ano.

---

## Falha na Conciliação Semanal

Os erros de formatação gerados pelo Excel (`;`, `Windows-1252`), nomes sem padrão e CNJs sem pontuação escondem problemas reais de cadastro entre Hub e Tribunal:
- **Diferença de R\$ 1.000,00** no valor de face do processo `0023456-21.2020.8.26.0053`.
- **Troca de devedor** entre `Município de Santos` e `União` no processo `0045678-43.2021.5.02.0011`.
- **Processos omitidos:** `0067890-65.2016.8.26.0053` falta no Hub e `0056789-54.2017.4.03.6100` falta no arquivo do Tribunal.
