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
| S7 | €53,229 | 29.0% | 0.99 | -44.9% | 0.65 | 23.4% | 947.7% |
| S8 | €144,732 | 50.2% | 1.16 | -40.6% | 1.24 | 56.6% | 721.1% |
| S9 | €37,048 | 22.1% | 0.66 | -70.7% | 0.31 | 56.5% | 1212.5% |
| S10 | €88,918 | 39.5% | 1.02 | -45.7% | 0.87 | 60.7% | 881.0% |
| B1 | €90,575 | 39.9% | 0.87 | -73.6% | 0.54 | 100.0% | 2.7% |
| B2 | €21,919 | 12.7% | 0.57 | -90.5% | 0.14 | 100.0% | 552.6% |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil -2.6%/jaar, p = 0.62; Sharpe-verschil 0.56, p = 0.03 (2398 dagen)
- H3 (S1 − S3): verschil -40.5%/jaar, p = 0.98; Sharpe-verschil 0.23, p = 0.23 (2398 dagen)
- S1 − B2: verschil -38.8%/jaar, p = 0.89; Sharpe-verschil 0.56, p = 0.04 (2398 dagen)
- S4 − B2: verschil -16.3%/jaar, p = 0.72; Sharpe-verschil 0.42, p = 0.08 (2398 dagen)

## In-sample (tot april 2025)

Periode: 2020-03-07 t/m 2025-03-31

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €16,405 | 10.3% | 1.28 | -11.7% | 0.88 | 8.2% | – |
| S2 | €18,493 | 12.9% | 0.73 | -32.3% | 0.40 | 25.4% | – |
| S3 | €133,176 | 66.7% | 1.18 | -71.4% | 0.93 | 51.4% | – |
| S4 | €52,075 | 38.5% | 1.13 | -45.0% | 0.85 | 31.0% | – |
| S7 | €47,384 | 35.9% | 1.09 | -44.9% | 0.80 | 26.6% | – |
| S8 | €124,749 | 64.5% | 1.30 | -40.6% | 1.59 | 60.8% | – |
| S9 | €35,169 | 28.2% | 0.76 | -70.7% | 0.40 | 56.3% | – |
| S10 | €83,406 | 52.0% | 1.15 | -45.7% | 1.14 | 66.5% | – |
| B1 | €93,774 | 55.5% | 1.02 | -73.6% | 0.75 | 100.0% | – |
| B2 | €30,419 | 24.5% | 0.70 | -89.7% | 0.27 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil -3.9%/jaar, p = 0.63; Sharpe-verschil 0.55, p = 0.06 (1850 dagen)
- H3 (S1 − S3): verschil -57.6%/jaar, p = 0.98; Sharpe-verschil 0.10, p = 0.38 (1850 dagen)
- S1 − B2: verschil -49.9%/jaar, p = 0.88; Sharpe-verschil 0.58, p = 0.06 (1850 dagen)
- S4 − B2: verschil -21.6%/jaar, p = 0.72; Sharpe-verschil 0.43, p = 0.12 (1850 dagen)

## Holdout (vanaf april 2025, opnieuw op €10.000 gezet) — hier telt het

Periode: 2025-04-01 t/m 2026-09-30

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €10,372 | 2.5% | 0.45 | -8.8% | 0.28 | 6.8% | – |
| S2 | €9,845 | -1.0% | 0.05 | -30.7% | -0.03 | 30.7% | – |
| S3 | €6,879 | -22.1% | -0.33 | -62.6% | -0.35 | 42.8% | – |
| S4 | €10,630 | 4.2% | 0.31 | -27.6% | 0.15 | 20.2% | – |
| S7 | €11,239 | 8.1% | 0.54 | -16.4% | 0.50 | 12.8% | – |
| S8 | €11,602 | 10.4% | 0.52 | -29.8% | 0.35 | 42.4% | – |
| S9 | €10,546 | 3.6% | 0.30 | -54.9% | 0.07 | 57.1% | – |
| S10 | €10,687 | 4.5% | 0.32 | -20.9% | 0.22 | 41.1% | – |
| B1 | €9,671 | -2.2% | 0.15 | -51.7% | -0.04 | 100.0% | – |
| B2 | €7,335 | -18.7% | 0.07 | -73.9% | -0.25 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil 1.6%/jaar, p = 0.47; Sharpe-verschil 0.40, p = 0.38 (547 dagen)
- H3 (S1 − S3): verschil 17.3%/jaar, p = 0.40; Sharpe-verschil 0.78, p = 0.18 (547 dagen)
- S1 − B2: verschil -2.6%/jaar, p = 0.56; Sharpe-verschil 0.38, p = 0.43 (547 dagen)
- S4 − B2: verschil 0.6%/jaar, p = 0.50; Sharpe-verschil 0.24, p = 0.53 (547 dagen)
