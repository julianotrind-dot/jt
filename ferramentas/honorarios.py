"""Controle de honorários: lista as parcelas vencidas e as que vencem em breve.

Uso:
    python3 ferramentas/honorarios.py
    python3 ferramentas/honorarios.py --dias 7 --hoje 2026-11-23
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "dados" / "honorarios.csv"


def brl(valor: float) -> str:
    s = f"{valor:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def classificar(hoje: date, janela: int, linhas: list[dict]) -> tuple[list[dict], list[dict]]:
    vencidas, a_vencer = [], []
    for l in linhas:
        if l.get("status", "").strip().lower() == "pago":
            continue
        venc = date.fromisoformat(l["vencimento"])
        atraso = (hoje - venc).days
        item = {**l, "valor": float(l["valor"]), "dias_atraso": atraso}
        if atraso > 0:
            vencidas.append(item)
        elif -atraso <= janela:
            a_vencer.append(item)
    vencidas.sort(key=lambda x: -x["dias_atraso"])
    a_vencer.sort(key=lambda x: x["vencimento"])
    return vencidas, a_vencer


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dias", type=int, default=7, help="janela para 'a vencer' (padrão 7)")
    ap.add_argument("--hoje", default=None)
    ap.add_argument("--arquivo", default=str(ARQ))
    a = ap.parse_args(argv)

    hoje = date.fromisoformat(a.hoje) if a.hoje else date.today()
    with open(a.arquivo, encoding="utf-8") as f:
        vencidas, a_vencer = classificar(hoje, a.dias, list(csv.DictReader(f)))

    print(f"VENCIDAS ({len(vencidas)}) – total {brl(sum(v['valor'] for v in vencidas))}")
    for v in vencidas:
        print(f"  {v['cliente']} | {brl(v['valor'])} | venceu {v['vencimento']} ({v['dias_atraso']} dias) | {v['email']}")
    print(f"A VENCER EM {a.dias} DIAS ({len(a_vencer)}) – total {brl(sum(v['valor'] for v in a_vencer))}")
    for v in a_vencer:
        print(f"  {v['cliente']} | {brl(v['valor'])} | vence {v['vencimento']} | {v['email']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
