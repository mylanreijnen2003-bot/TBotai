"""Paper-portefeuille: nepgeld, echte prijzen, kosten per verhandelde euro.

Uitvoering: het signaal komt op het slot van dag t; de order wordt uitgevoerd
tegen de OPEN van dag t+1, met `cost_per_side` kosten op elke verhandelde euro.
Er is geen hefboom: kopen kan alleen met aanwezig cash.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Trade:
    symbol: str
    side: str        # "buy" of "sell"
    qty: float
    price: float
    notional: float  # qty × price in EUR
    cost: float      # kosten in EUR
    reason: str


@dataclass
class Portfolio:
    name: str
    cash: float
    qty: dict[str, float] = field(default_factory=dict)

    def value(self, prices: dict[str, float]) -> float:
        return self.cash + sum(q * prices[s] for s, q in self.qty.items() if q > 0 and s in prices)

    def weights(self, prices: dict[str, float]) -> dict[str, float]:
        eq = self.value(prices)
        if eq <= 0:
            return {}
        return {s: q * prices[s] / eq for s, q in self.qty.items() if q > 0 and s in prices}

    def rebalance(
        self,
        targets: dict[str, float] | None,
        prices: dict[str, float],
        universe: list[str],
        cost: float,
        band: float,
        min_order: float,
        use_band: bool,
        follow_universe: bool,
    ) -> list[Trade]:
        """Stuur bij naar de doelgewichten. Geeft de uitgevoerde trades terug."""
        eq = self.value(prices)
        if eq <= 0:
            return []
        cur = self.weights(prices)
        plan: dict[str, tuple[float, str]] = {}  # munt -> (doelgewicht, reden)

        # 1. munten buiten het universum volledig verkopen
        if follow_universe:
            for s in list(cur):
                if s not in universe:
                    plan[s] = (0.0, "buiten universum")

        # 2. doelgewichten (None = vandaag niets doen)
        if targets is not None:
            for s in set(targets) | set(cur):
                if s in plan:
                    continue
                tgt = max(0.0, float(targets.get(s, 0.0)))
                c = cur.get(s, 0.0)
                if tgt == 0.0 and c > 0:
                    plan[s] = (0.0, "uitstap")
                elif tgt > 0 and c == 0:
                    plan[s] = (tgt, "instap")
                elif tgt > 0 and c > 0:
                    if not use_band or abs(c - tgt) / tgt > band:
                        plan[s] = (tgt, "bijsturen")

        trades: list[Trade] = []
        # 3. eerst verkopen (maakt cash vrij), dan kopen
        for s, (tgt, why) in sorted(plan.items()):
            if s not in prices or not prices[s] > 0:
                continue  # geen prijs: kan niet handelen
            c = cur.get(s, 0.0)
            if tgt >= c:
                continue
            p = prices[s]
            if tgt == 0.0:
                q = self.qty.get(s, 0.0)  # volledige uitstap, ook als klein
            else:
                q = (c - tgt) * eq / p
                if q * p < min_order:
                    continue
            notional = q * p
            fee = notional * cost
            self.cash += notional - fee
            self.qty[s] = self.qty.get(s, 0.0) - q
            if self.qty[s] <= 1e-12:
                self.qty.pop(s, None)
            trades.append(Trade(s, "sell", q, p, notional, fee, why))

        buys = []
        for s, (tgt, why) in sorted(plan.items()):
            if s not in prices or not prices[s] > 0:
                continue
            c = cur.get(s, 0.0)
            if tgt <= c:
                continue
            buys.append((s, (tgt - c) * eq, why))
        need = sum(n * (1 + cost) for _, n, _ in buys)
        scale = min(1.0, self.cash / need) if need > 0 else 1.0
        for s, n, why in buys:
            notional = min(n * scale, self.cash / (1 + cost))
            if notional < min_order:
                continue
            fee = notional * cost
            p = prices[s]
            self.cash -= notional + fee
            if self.cash < 0:
                self.cash = 0.0  # afrondingsverschil, nooit echt negatief
            self.qty[s] = self.qty.get(s, 0.0) + notional / p
            trades.append(Trade(s, "buy", notional / p, p, notional, fee, why))

        assert self.cash >= 0, "cash negatief: hefboom is niet toegestaan"
        assert not any(math.isnan(v) for v in self.qty.values())
        return trades
