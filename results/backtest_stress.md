# Backtest v1 — kosten 0.60% per kant

> Waarschuwing: data van de huidige Bitvavo-markten. Verdwenen munten ontbreken (survivorship bias),
> dus de cijfers zijn te optimistisch. Een paper-test van maanden wijst géén winnaar aan.

## Hele periode

Periode: 2020-03-07 t/m 2026-10-01

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €15,912 | 7.3% | 0.99 | -13.8% | 0.53 | 7.9% | 356.2% |
| S2 | €17,616 | 9.0% | 0.54 | -33.9% | 0.27 | 26.6% | 195.3% |
| S3 | €71,403 | 34.9% | 0.82 | -77.1% | 0.45 | 49.5% | 1298.7% |
| S4 | €43,329 | 25.0% | 0.87 | -50.0% | 0.50 | 28.6% | 1276.5% |
| S10 | €74,206 | 35.8% | 0.95 | -48.9% | 0.73 | 60.7% | 879.7% |
| M1 | €81,749 | 37.7% | 1.09 | -39.0% | 0.97 | 48.7% | 841.1% |
| M2 | €49,713 | 27.7% | 1.10 | -25.2% | 1.10 | 32.8% | 504.7% |
| B1 | €90,304 | 39.9% | 0.87 | -73.6% | 0.54 | 100.0% | 2.7% |
| B2 | €19,975 | 11.2% | 0.55 | -91.3% | 0.12 | 100.0% | 554.1% |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil -3.2%/jaar, p = 0.65; Sharpe-verschil 0.45, p = 0.08 (2399 dagen)
- H3 (S1 − S3): verschil -37.7%/jaar, p = 0.96; Sharpe-verschil 0.16, p = 0.30 (2399 dagen)
- S1 − B2: verschil -38.5%/jaar, p = 0.88; Sharpe-verschil 0.43, p = 0.10 (2399 dagen)
- S4 − B2: verschil -18.6%/jaar, p = 0.75; Sharpe-verschil 0.32, p = 0.17 (2399 dagen)

## In-sample (tot april 2025)

Periode: 2020-03-07 t/m 2025-03-31

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €15,580 | 9.1% | 1.15 | -13.8% | 0.66 | 8.2% | – |
| S2 | €18,031 | 12.3% | 0.70 | -32.7% | 0.38 | 25.4% | – |
| S3 | €109,482 | 60.3% | 1.11 | -73.4% | 0.82 | 51.4% | – |
| S4 | €42,580 | 33.1% | 1.01 | -50.0% | 0.66 | 31.0% | – |
| S10 | €72,889 | 48.0% | 1.09 | -48.9% | 0.98 | 66.5% | – |
| M1 | €76,141 | 49.3% | 1.24 | -39.0% | 1.26 | 52.8% | – |
| M2 | €45,963 | 35.1% | 1.24 | -25.2% | 1.39 | 35.1% | – |
| B1 | €93,774 | 55.5% | 1.02 | -73.6% | 0.75 | 100.0% | – |
| B2 | €27,853 | 22.4% | 0.68 | -89.9% | 0.25 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil -4.4%/jaar, p = 0.66; Sharpe-verschil 0.45, p = 0.12 (1850 dagen)
- H3 (S1 − S3): verschil -54.8%/jaar, p = 0.98; Sharpe-verschil 0.04, p = 0.45 (1850 dagen)
- S1 − B2: verschil -49.2%/jaar, p = 0.88; Sharpe-verschil 0.47, p = 0.12 (1850 dagen)
- S4 − B2: verschil -23.8%/jaar, p = 0.75; Sharpe-verschil 0.33, p = 0.21 (1850 dagen)

## Holdout (vanaf april 2025, opnieuw op €10.000 gezet) — hier telt het

Periode: 2025-04-01 t/m 2026-10-01

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €10,216 | 1.4% | 0.28 | -9.9% | 0.14 | 6.8% | – |
| S2 | €9,821 | -1.2% | 0.04 | -31.1% | -0.04 | 30.8% | – |
| S3 | €6,522 | -24.8% | -0.40 | -65.0% | -0.38 | 42.9% | – |
| S4 | €10,189 | 1.3% | 0.16 | -30.7% | 0.04 | 20.3% | – |
| S10 | €10,236 | 1.6% | 0.18 | -22.9% | 0.07 | 41.2% | – |
| M1 | €10,775 | 5.1% | 0.36 | -24.9% | 0.20 | 34.7% | – |
| M2 | €10,839 | 5.5% | 0.44 | -19.8% | 0.28 | 25.1% | – |
| B1 | €9,671 | -2.2% | 0.15 | -51.7% | -0.04 | 100.0% | – |
| B2 | €7,332 | -18.7% | 0.07 | -74.3% | -0.25 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil 0.7%/jaar, p = 0.49; Sharpe-verschil 0.23, p = 0.54 (548 dagen)
- H3 (S1 − S3): verschil 19.8%/jaar, p = 0.37; Sharpe-verschil 0.68, p = 0.23 (548 dagen)
- S1 − B2: verschil -3.5%/jaar, p = 0.57; Sharpe-verschil 0.20, p = 0.58 (548 dagen)
- S4 − B2: verschil -2.2%/jaar, p = 0.53; Sharpe-verschil 0.09, p = 0.66 (548 dagen)
