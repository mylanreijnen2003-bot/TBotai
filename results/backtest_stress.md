# Backtest v1 — kosten 0.60% per kant

> Waarschuwing: data van de huidige Bitvavo-markten. Verdwenen munten ontbreken (survivorship bias),
> dus de cijfers zijn te optimistisch. Een paper-test van maanden wijst géén winnaar aan.

## Hele periode

Periode: 2020-03-07 t/m 2026-09-30

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €15,856 | 7.3% | 0.98 | -13.8% | 0.53 | 7.9% | 356.1% |
| S2 | €17,534 | 9.0% | 0.54 | -33.9% | 0.26 | 26.6% | 194.9% |
| S3 | €70,244 | 34.5% | 0.82 | -77.1% | 0.45 | 49.5% | 1298.5% |
| S4 | €42,754 | 24.8% | 0.87 | -50.0% | 0.50 | 28.6% | 1275.5% |
| S7 | €43,836 | 25.2% | 0.90 | -48.4% | 0.52 | 23.5% | 953.6% |
| S8 | €125,985 | 47.1% | 1.11 | -40.8% | 1.15 | 56.7% | 719.7% |
| S9 | €29,366 | 17.9% | 0.59 | -73.4% | 0.24 | 56.5% | 1203.3% |
| S10 | €74,207 | 35.8% | 0.95 | -48.9% | 0.73 | 60.7% | 880.3% |
| B1 | €90,305 | 39.9% | 0.87 | -73.6% | 0.54 | 100.0% | 2.7% |
| B2 | €19,572 | 10.9% | 0.55 | -91.3% | 0.12 | 100.0% | 551.2% |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil -3.2%/jaar, p = 0.66; Sharpe-verschil 0.44, p = 0.08 (2398 dagen)
- H3 (S1 − S3): verschil -37.5%/jaar, p = 0.96; Sharpe-verschil 0.16, p = 0.31 (2398 dagen)
- S1 − B2: verschil -38.2%/jaar, p = 0.88; Sharpe-verschil 0.43, p = 0.10 (2398 dagen)
- S4 − B2: verschil -18.5%/jaar, p = 0.75; Sharpe-verschil 0.32, p = 0.17 (2398 dagen)

## In-sample (tot april 2025)

Periode: 2020-03-07 t/m 2025-03-31

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €15,580 | 9.1% | 1.15 | -13.8% | 0.66 | 8.2% | – |
| S2 | €18,031 | 12.3% | 0.70 | -32.7% | 0.38 | 25.4% | – |
| S3 | €109,482 | 60.3% | 1.11 | -73.4% | 0.82 | 51.4% | – |
| S4 | €42,580 | 33.1% | 1.01 | -50.0% | 0.66 | 31.0% | – |
| S7 | €40,188 | 31.6% | 0.99 | -48.4% | 0.65 | 26.6% | – |
| S8 | €112,151 | 61.1% | 1.25 | -40.8% | 1.50 | 60.9% | – |
| S9 | €29,408 | 23.7% | 0.68 | -73.4% | 0.32 | 56.3% | – |
| S10 | €72,889 | 48.0% | 1.09 | -48.9% | 0.98 | 66.5% | – |
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

Periode: 2025-04-01 t/m 2026-09-30

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €10,180 | 1.2% | 0.24 | -9.9% | 0.12 | 6.8% | – |
| S2 | €9,775 | -1.5% | 0.03 | -31.1% | -0.05 | 30.8% | – |
| S3 | €6,416 | -25.6% | -0.43 | -65.0% | -0.39 | 42.8% | – |
| S4 | €10,054 | 0.4% | 0.11 | -30.7% | 0.01 | 20.2% | – |
| S7 | €10,917 | 6.0% | 0.43 | -18.1% | 0.33 | 12.8% | – |
| S8 | €11,234 | 8.1% | 0.44 | -31.5% | 0.26 | 42.5% | – |
| S9 | €10,009 | 0.1% | 0.22 | -56.4% | 0.00 | 57.1% | – |
| S10 | €10,236 | 1.6% | 0.18 | -22.9% | 0.07 | 41.1% | – |
| B1 | €9,671 | -2.2% | 0.15 | -51.7% | -0.04 | 100.0% | – |
| B2 | €7,184 | -19.8% | 0.05 | -74.3% | -0.27 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil 0.8%/jaar, p = 0.49; Sharpe-verschil 0.21, p = 0.55 (547 dagen)
- H3 (S1 − S3): verschil 20.7%/jaar, p = 0.36; Sharpe-verschil 0.67, p = 0.23 (547 dagen)
- S1 − B2: verschil -2.4%/jaar, p = 0.56; Sharpe-verschil 0.18, p = 0.59 (547 dagen)
- S4 − B2: verschil -1.7%/jaar, p = 0.53; Sharpe-verschil 0.06, p = 0.67 (547 dagen)
