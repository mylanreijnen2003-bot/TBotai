# Backtest v1 — kosten 0.30% per kant

> Waarschuwing: data van de huidige Bitvavo-markten. Verdwenen munten ontbreken (survivorship bias),
> dus de cijfers zijn te optimistisch. Een paper-test van maanden wijst géén winnaar aan.

## Hele periode

Periode: 2020-03-07 t/m 2026-09-30

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €17,011 | 8.4% | 1.12 | -12.0% | 0.70 | 7.9% | 357.0% |
| S2 | €18,132 | 9.5% | 0.56 | -33.5% | 0.28 | 26.6% | 194.2% |
| S3 | €91,608 | 40.1% | 0.89 | -71.9% | 0.56 | 49.5% | 1312.2% |
| S4 | €55,307 | 29.7% | 0.99 | -45.0% | 0.66 | 28.6% | 1275.8% |
| S5 | €48,646 | 27.2% | 0.96 | -46.7% | 0.58 | 41.9% | 1219.7% |
| B1 | €90,575 | 39.9% | 0.87 | -73.6% | 0.54 | 100.0% | 2.7% |
| B2 | €21,919 | 12.7% | 0.57 | -90.5% | 0.14 | 100.0% | 552.6% |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H5 (S5 CAGR ≥ B1 én drawdown ≤ 60% van B1): rendement nee, drawdown nee
- H2 (S1 − S2): verschil -2.6%/jaar, p = 0.62; Sharpe-verschil 0.56, p = 0.03 (2398 dagen)
- H3 (S1 − S3): verschil -40.5%/jaar, p = 0.98; Sharpe-verschil 0.23, p = 0.23 (2398 dagen)
- S1 − B2: verschil -38.8%/jaar, p = 0.89; Sharpe-verschil 0.56, p = 0.04 (2398 dagen)
- S4 − B2: verschil -16.3%/jaar, p = 0.72; Sharpe-verschil 0.42, p = 0.08 (2398 dagen)
- S5 − B1: verschil -23.1%/jaar, p = 0.91; Sharpe-verschil 0.09, p = 0.54 (2398 dagen)

## In-sample (tot april 2025)

Periode: 2020-03-07 t/m 2025-03-31

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €16,405 | 10.3% | 1.28 | -11.7% | 0.88 | 8.2% | – |
| S2 | €18,493 | 12.9% | 0.73 | -32.3% | 0.40 | 25.4% | – |
| S3 | €133,176 | 66.7% | 1.18 | -71.4% | 0.93 | 51.4% | – |
| S4 | €52,075 | 38.5% | 1.13 | -45.0% | 0.85 | 31.0% | – |
| S5 | €50,872 | 37.8% | 1.14 | -46.7% | 0.81 | 45.4% | – |
| B1 | €93,774 | 55.5% | 1.02 | -73.6% | 0.75 | 100.0% | – |
| B2 | €30,419 | 24.5% | 0.70 | -89.7% | 0.27 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H5 (S5 CAGR ≥ B1 én drawdown ≤ 60% van B1): rendement nee, drawdown nee
- H2 (S1 − S2): verschil -3.9%/jaar, p = 0.63; Sharpe-verschil 0.55, p = 0.06 (1850 dagen)
- H3 (S1 − S3): verschil -57.6%/jaar, p = 0.98; Sharpe-verschil 0.10, p = 0.38 (1850 dagen)
- S1 − B2: verschil -49.9%/jaar, p = 0.88; Sharpe-verschil 0.58, p = 0.06 (1850 dagen)
- S4 − B2: verschil -21.6%/jaar, p = 0.72; Sharpe-verschil 0.43, p = 0.12 (1850 dagen)
- S5 − B1: verschil -27.4%/jaar, p = 0.91; Sharpe-verschil 0.12, p = 0.53 (1850 dagen)

## Holdout (vanaf april 2025, opnieuw op €10.000 gezet) — hier telt het

Periode: 2025-04-01 t/m 2026-09-30

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €10,372 | 2.5% | 0.45 | -8.8% | 0.28 | 6.8% | – |
| S2 | €9,845 | -1.0% | 0.05 | -30.7% | -0.03 | 30.7% | – |
| S3 | €6,879 | -22.1% | -0.33 | -62.6% | -0.35 | 42.8% | – |
| S4 | €10,630 | 4.2% | 0.31 | -27.6% | 0.15 | 20.2% | – |
| S5 | €9,566 | -2.9% | -0.14 | -23.5% | -0.12 | 29.8% | – |
| B1 | €9,671 | -2.2% | 0.15 | -51.7% | -0.04 | 100.0% | – |
| B2 | €7,335 | -18.7% | 0.07 | -73.9% | -0.25 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H5 (S5 CAGR ≥ B1 én drawdown ≤ 60% van B1): rendement nee, drawdown ja
- H2 (S1 − S2): verschil 1.6%/jaar, p = 0.47; Sharpe-verschil 0.40, p = 0.38 (547 dagen)
- H3 (S1 − S3): verschil 17.3%/jaar, p = 0.40; Sharpe-verschil 0.78, p = 0.18 (547 dagen)
- S1 − B2: verschil -2.6%/jaar, p = 0.56; Sharpe-verschil 0.38, p = 0.43 (547 dagen)
- S4 − B2: verschil 0.6%/jaar, p = 0.50; Sharpe-verschil 0.24, p = 0.53 (547 dagen)
- S5 − B1: verschil -8.4%/jaar, p = 0.59; Sharpe-verschil -0.29, p = 0.76 (547 dagen)
