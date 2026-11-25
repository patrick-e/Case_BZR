import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.limpeza import executar_pipeline_limpeza
from src.normalizacao import Normalizacao


class TestRegrasLimpeza(unittest.TestCase):
    """Testes automatizados para as regras mais arriscadas do domínio de precatórios."""

    def test_normalizacao_processo_cnj(self) -> None:
        # 20 dígitos sem máscara -> deve formatar com 25 caracteres
        proc, alterado = Normalizacao.processo("00234562120208260053")
        self.assertEqual(proc, "0023456-21.2020.8.26.0053")
        self.assertTrue(alterado)

        # Já formatado -> mantém e indica que não houve alteração
        proc_ok, alterado_ok = Normalizacao.processo("0012345-10.2019.8.26.0053")
        self.assertEqual(proc_ok, "0012345-10.2019.8.26.0053")
        self.assertFalse(alterado_ok)

        # Vazio ou inválido -> retorna None
        self.assertEqual(Normalizacao.processo(""), (None, False))
        self.assertEqual(Normalizacao.processo("12345"), (None, False))

    def test_prazo_constitucional_2_de_abril_e_fuso_utc(self) -> None:
        # 1. Apresentado exatamente em 2 de abril -> paga até 31/12 do ano seguinte (2026)
        data_brt, prazo, _ = Normalizacao.apresentado_em_prazo("2025-04-02")
        self.assertEqual(data_brt, date(2025, 4, 2))
        self.assertEqual(prazo, date(2026, 12, 31))

        # 2. Apresentado em 3 de abril -> paga até 31/12 do ano subsequente ao seguinte (2027)
        data_brt, prazo, _ = Normalizacao.apresentado_em_prazo("2025-04-03")
        self.assertEqual(data_brt, date(2025, 4, 3))
        self.assertEqual(prazo, date(2027, 12, 31))

        # 3. Apresentado em 2025-04-03T01:00:00Z (UTC) -> em Brasília (-03:00) ainda é 2025-04-02 às 22h!
        data_brt, prazo, teve_tz = Normalizacao.apresentado_em_prazo("2025-04-03T01:00:00Z")
        self.assertEqual(data_brt, date(2025, 4, 2))
        self.assertEqual(prazo, date(2026, 12, 31))
        self.assertTrue(teve_tz)

        # 4. Ano bissexto (2024-02-29) -> até 2 de abril de 2024 -> 2025-12-31
        data_brt, prazo, _ = Normalizacao.apresentado_em_prazo("2024-02-29")
        self.assertEqual(data_brt, date(2024, 2, 29))
        self.assertEqual(prazo, date(2025, 12, 31))

    def test_conversao_valor_monetario_ptbr(self) -> None:
        val, foi_ptbr = Normalizacao.valor_monetario("2.500,50")
        self.assertEqual(val, Decimal("2500.50"))
        self.assertTrue(foi_ptbr)

        val_neg, _ = Normalizacao.valor_monetario(-200)
        self.assertEqual(val_neg, Decimal("-200.00"))

        val_null, _ = Normalizacao.valor_monetario(None)
        self.assertIsNone(val_null)

    def test_pipeline_deduplicacao_retificacao_e_estorno(self) -> None:
        raiz = Path(__file__).resolve().parent.parent
        resultado = executar_pipeline_limpeza(raiz / "case-candidato" / "dados")

        prec_por_proc = {p["numero_processo"]: p for p in resultado.precatorios}
        pag_por_id = {e["evento_id"]: e for e in resultado.pagamentos}

        # ev-001 teve retificação de 15000.0 para 15500.0 e ev-002 (2500.50) estava duplicado:
        # Total líquido do processo 0012345-10.2019.8.26.0053 deve ser 15500.00 + 2500.50 = 18000.50
        self.assertEqual(pag_por_id["ev-001"]["valor"], "15500.00")
        self.assertEqual(pag_por_id["ev-002"]["valor"], "2500.50")
        self.assertEqual(prec_por_proc["0012345-10.2019.8.26.0053"]["total_pago_liquido"], "18000.50")

        # Processo 0034567-32.2018.8.26.0405 teve pagamento (ev-006 = 5000) e estorno (ev-007 = 5000) -> saldo 0.00
        self.assertEqual(prec_por_proc["0034567-32.2018.8.26.0405"]["total_pago_liquido"], "0.00")

        # Eventos inválidos (ev-004 null, ev-009 -200, ev-010 sem processo) não devem entrar na base limpa
        self.assertNotIn("ev-004", pag_por_id)
        self.assertNotIn("ev-009", pag_por_id)
        self.assertNotIn("ev-010", pag_por_id)


if __name__ == "__main__":
    unittest.main()
