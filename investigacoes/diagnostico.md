# Diagnóstico por Ordem de Gravidade

Problemas ordenados do mais grave para o menos grave, indicando se são **causa** ou **consequência**.

---

<a id="critico"></a>
## Nível Crítico

### Pagamentos somados mais de uma vez (Causa)
- **Problema:** `pagamentos.json` traz IDs repetidos (`ev-002` duplicado e `ev-001` retificado de `15000.0` para `15500.0`) e a tabela `pagamento` não tem `UNIQUE (evento_id)`.
- **Efeito:** como o tribunal reenvia os últimos 7 dias diariamente e o operador reexecuta o script em caso de falha, o mesmo pagamento é somado várias vezes.

### Estorno somado como pagamento (Causa)
- **Problema:** o evento `ev-007` é um `"estorno"` de R\$ 5.000,00, mas o script soma todos os valores sem olhar o campo `tipo`.
- **Efeito:** o processo `0034567-32.2018.8.26.0405` fica com saldo pago de R\$ 10.000,00 em vez de R\$ 0,00.

### Descarte silencioso de eventos com erro (Consequência)
- **Problema:** o script ignora qualquer falha sem gerar log ou alerta.
- **Efeito:** seis eventos do lote falham sem ninguém saber: `ev-002` (valor em texto PT-BR e data `DD/MM/AAAA`), `ev-004` (`null`), `ev-005` (CNJ sem máscara), `ev-009` (`-200`), `ev-010` (sem processo) e `ev-011` (processo ausente no Hub).

### Divergências cadastrais entre Hub e Tribunal (Consequência)
- **Problema:** conferência manual frágil entre `hub.csv` e `tribunal.csv`.
- **Efeito:** um processo pago não está no Hub (`0067890-65.2016.8.26.0053`), um processo do Hub sumiu do arquivo do tribunal (`0056789-54.2017.4.03.6100`), o processo `0045678-43.2021.5.02.0011` mudou de `Município de Santos` para `União` e o `0023456-21.2020.8.26.0053` diverge em R\$ 1.000,00 no valor de face.

### Erro no cálculo do prazo de pagamento (Causa)
- **Problema:** a regra constitucional inclui o dia 2 de abril (`<= 02/04`) no horário de Brasília. O sistema excluiu o dia 2 de abril e não converteu timestamps em UTC (`2025-04-03T01:00:00Z` = `2025-04-02` às 22h BRT).
- **Efeito:** os processos `0012345-10.2019.8.26.0053` e `0056789-54.2017.4.03.6100` ficaram com vencimento em `2027-12-31` em vez de `2026-12-31`.

---

<a id="razoavel"></a>
## Nível Moderado

- **Coluna `CHAR(20)` menor que o padrão CNJ (Causa):** o número CNJ formatado tem 25 caracteres. O limite de 20 caracteres no banco força o uso de números sem pontuação e quebra comparações exatas.
- **Nome do ente devedor sem padrão (Causa):** campo `TEXT` livre permite `MUNICIPIO DE SAO PAULO` e `Município de São Paulo` na mesma base.
- **CSV corrompido pelo Excel (Consequência):** salvar `tribunal.csv` no Excel altera a codificação para `Windows-1252`, troca `,` por `;` e formata números como `45.000,00`.
- **Pagamento anterior à apresentação (Consequência):** `ev-001` (`2025-03-10`) tem data anterior à apresentação do processo `0012345-10.2019.8.26.0053` (`2025-04-02`).
- **Documentação e `schema.sql` defasados (Causa):** `apresentacoes.json` não está documentado, `DOCUMENTACAO_TRIBUNAL.md` não prevê `"estorno"` e faltam as colunas de prazo na tabela `precatorio`.
