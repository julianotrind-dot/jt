"""Cálculo de prazos processuais em dias úteis (CPC/2015).

Regras aplicadas:
- Art. 219: prazos em dias contam só os dias úteis.
- Art. 224: exclui o dia do começo e inclui o do vencimento. A contagem começa
  no primeiro dia útil seguinte à intimação, e um vencimento em dia não útil
  passa para o próximo dia útil.
- Art. 220: os prazos ficam suspensos de 20 de dezembro a 20 de janeiro.
- Feriados nacionais (fixos e móveis), mais os feriados locais listados em
  dados/feriados_locais.csv.

Uso:
    python3 ferramentas/prazos.py calcular 2026-11-23 15
    python3 ferramentas/prazos.py proximos --dias 10
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQ_PROCESSOS = RAIZ / "dados" / "processos.csv"
ARQ_FERIADOS_LOCAIS = RAIZ / "dados" / "feriados_locais.csv"


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, dia + 1)


def feriados_nacionais(ano: int) -> set[date]:
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (11, 20), (12, 25)]
    p = pascoa(ano)
    moveis = [
        p - timedelta(days=48),  # segunda de Carnaval
        p - timedelta(days=47),  # terça de Carnaval
        p - timedelta(days=2),   # Sexta-feira Santa
        p + timedelta(days=60),  # Corpus Christi
    ]
    return {date(ano, m, d) for m, d in fixos} | set(moveis)


def carregar_feriados_locais(caminho: Path = ARQ_FERIADOS_LOCAIS) -> set[date]:
    if not caminho.exists():
        return set()
    with caminho.open(encoding="utf-8") as f:
        return {date.fromisoformat(l["data"]) for l in csv.DictReader(f) if l.get("data")}


def em_recesso(d: date) -> bool:
    """Art. 220 do CPC: suspensão de 20/12 a 20/01, inclusive."""
    return (d.month == 12 and d.day >= 20) or (d.month == 1 and d.day <= 20)


class Calendario:
    def __init__(self, feriados_locais: set[date] | None = None):
        self.locais = feriados_locais or set()
        self._cache: dict[int, set[date]] = {}

    def feriado(self, d: date) -> bool:
        if d.year not in self._cache:
            self._cache[d.year] = feriados_nacionais(d.year)
        return d in self._cache[d.year] or d in self.locais

    def dia_util(self, d: date) -> bool:
        return d.weekday() < 5 and not self.feriado(d) and not em_recesso(d)

    def proximo_dia_util(self, d: date) -> date:
        while not self.dia_util(d):
            d += timedelta(days=1)
        return d

    def vencimento(self, intimacao: date, dias: int) -> date:
        """Último dia do prazo de `dias` dias úteis contados após a intimação."""
        if dias < 1:
            raise ValueError("o prazo precisa ter pelo menos 1 dia")
        d = intimacao
        contados = 0
        while contados < dias:
            d += timedelta(days=1)
            if self.dia_util(d):
                contados += 1
        return d


def ler_processos(caminho: Path = ARQ_PROCESSOS) -> list[dict]:
    with caminho.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def proximos_prazos(hoje: date, janela: int, cal: Calendario, processos: list[dict]) -> list[dict]:
    """Prazos em aberto que vencem até `janela` dias corridos a partir de hoje (e os já vencidos)."""
    saida = []
    for p in processos:
        if p.get("status", "").strip().lower() == "cumprido":
            continue
        venc = cal.vencimento(date.fromisoformat(p["data_intimacao"]), int(p["prazo_dias_uteis"]))
        faltam = (venc - hoje).days
        if faltam <= janela:
            saida.append({**p, "vencimento": venc.isoformat(), "dias_corridos_restantes": faltam})
    return sorted(saida, key=lambda x: x["vencimento"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("calcular", help="calcula o vencimento de um prazo")
    c.add_argument("intimacao", help="data da intimação (AAAA-MM-DD)")
    c.add_argument("dias", type=int, help="prazo em dias úteis")
    pr = sub.add_parser("proximos", help="lista os prazos que vencem em breve")
    pr.add_argument("--dias", type=int, default=10, help="janela em dias corridos (padrão 10)")
    pr.add_argument("--hoje", default=None, help="data de referência (padrão: hoje)")
    a = ap.parse_args(argv)

    cal = Calendario(carregar_feriados_locais())
    if a.cmd == "calcular":
        v = cal.vencimento(date.fromisoformat(a.intimacao), a.dias)
        print(f"Vencimento: {v.strftime('%d/%m/%Y')} ({['seg','ter','qua','qui','sex','sáb','dom'][v.weekday()]})")
        return 0

    hoje = date.fromisoformat(a.hoje) if a.hoje else date.today()
    itens = proximos_prazos(hoje, a.dias, cal, ler_processos())
    if not itens:
        print("Nenhum prazo vencendo na janela.")
        return 0
    for i in itens:
        r = i["dias_corridos_restantes"]
        alerta = "VENCIDO" if r < 0 else ("HOJE" if r == 0 else f"faltam {r} dias")
        venc = date.fromisoformat(i["vencimento"]).strftime("%d/%m/%Y")
        print(f"[{alerta}] {venc} | {i['processo']} | {i['cliente']} | {i['ato']} | resp.: {i['responsavel']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
