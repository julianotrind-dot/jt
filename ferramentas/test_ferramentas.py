import unittest
from datetime import date

from prazos import Calendario, em_recesso, feriados_nacionais, pascoa, proximos_prazos
from honorarios import brl, classificar


class TestPrazos(unittest.TestCase):
    def setUp(self):
        self.cal = Calendario()

    def test_pascoa(self):
        self.assertEqual(pascoa(2026), date(2026, 4, 5))
        self.assertEqual(pascoa(2027), date(2027, 3, 28))

    def test_feriados_moveis_2026(self):
        f = feriados_nacionais(2026)
        self.assertIn(date(2026, 2, 16), f)  # segunda de Carnaval
        self.assertIn(date(2026, 2, 17), f)  # terça de Carnaval
        self.assertIn(date(2026, 4, 3), f)   # Sexta-feira Santa
        self.assertIn(date(2026, 6, 4), f)   # Corpus Christi
        self.assertIn(date(2026, 11, 20), f) # Consciência Negra

    def test_recesso(self):
        self.assertTrue(em_recesso(date(2026, 12, 20)))
        self.assertTrue(em_recesso(date(2027, 1, 20)))
        self.assertFalse(em_recesso(date(2027, 1, 21)))
        self.assertFalse(em_recesso(date(2026, 12, 19)))

    def test_prazo_simples(self):
        # Intimação na segunda 09/11/2026; 5 dias úteis: 10, 11, 12, 13 e 16.
        self.assertEqual(self.cal.vencimento(date(2026, 11, 9), 5), date(2026, 11, 16))

    def test_intimacao_na_sexta(self):
        # Sexta 06/11/2026: a contagem começa na segunda 09/11.
        self.assertEqual(self.cal.vencimento(date(2026, 11, 6), 1), date(2026, 11, 9))

    def test_pula_feriado(self):
        # Intimação 19/11/2026 (qui); 20/11 é feriado, então o 1º dia útil é 23/11.
        self.assertEqual(self.cal.vencimento(date(2026, 11, 19), 1), date(2026, 11, 23))

    def test_atravessa_recesso(self):
        # Intimação 16/12/2026 (qua): 17, 18 e 19(sáb, não conta) -> 17 e 18 contam;
        # suspensão até 20/01; 21/01/2027 (qui) é o 3º dia útil.
        self.assertEqual(self.cal.vencimento(date(2026, 12, 16), 3), date(2027, 1, 21))

    def test_feriado_local(self):
        cal = Calendario({date(2026, 11, 24)})
        self.assertEqual(cal.vencimento(date(2026, 11, 23), 1), date(2026, 11, 25))

    def test_proximos_ignora_cumpridos(self):
        procs = [
            {"processo": "A", "cliente": "X", "ato": "c", "responsavel": "r",
             "data_intimacao": "2026-11-16", "prazo_dias_uteis": "5", "status": "aberto"},
            {"processo": "B", "cliente": "Y", "ato": "c", "responsavel": "r",
             "data_intimacao": "2026-11-16", "prazo_dias_uteis": "5", "status": "cumprido"},
        ]
        r = proximos_prazos(date(2026, 11, 23), 10, self.cal, procs)
        self.assertEqual([p["processo"] for p in r], ["A"])


class TestHonorarios(unittest.TestCase):
    def test_brl(self):
        self.assertEqual(brl(1234567.8), "R$ 1.234.567,80")

    def test_classificar(self):
        linhas = [
            {"cliente": "A", "valor": "100", "vencimento": "2026-11-01", "status": "aberto", "email": ""},
            {"cliente": "B", "valor": "200", "vencimento": "2026-11-25", "status": "aberto", "email": ""},
            {"cliente": "C", "valor": "300", "vencimento": "2026-11-01", "status": "pago", "email": ""},
            {"cliente": "D", "valor": "400", "vencimento": "2027-01-10", "status": "aberto", "email": ""},
        ]
        venc, av = classificar(date(2026, 11, 23), 7, linhas)
        self.assertEqual([v["cliente"] for v in venc], ["A"])
        self.assertEqual(venc[0]["dias_atraso"], 22)
        self.assertEqual([v["cliente"] for v in av], ["B"])


if __name__ == "__main__":
    unittest.main()
