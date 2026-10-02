# Backtest v1 — kosten 0.30% per kant

> Waarschuwing: data van de huidige Bitvavo-markten. Verdwenen munten ontbreken (survivorship bias),
> dus de cijfers zijn te optimistisch. Een paper-test van maanden wijst géén winnaar aan.

## Hele periode

Periode: 2020-03-07 t/m 2026-10-01

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €17,072 | 8.5% | 1.13 | -12.0% | 0.71 | 7.9% | 357.2% |
| S2 | €18,218 | 9.6% | 0.57 | -33.5% | 0.29 | 26.6% | 194.5% |
| S3 | €93,139 | 40.4% | 0.90 | -71.9% | 0.56 | 49.5% | 1312.5% |
| S4 | €56,064 | 30.0% | 1.00 | -45.0% | 0.67 | 28.6% | 1276.9% |
| S10 | €88,917 | 39.5% | 1.02 | -45.7% | 0.86 | 60.7% | 880.4% |
| M1 | €96,967 | 41.3% | 1.17 | -37.1% | 1.11 | 48.6% | 839.8% |
| M2 | €54,832 | 29.6% | 1.16 | -24.3% | 1.22 | 32.8% | 505.5% |
| B1 | €90,574 | 39.9% | 0.87 | -73.6% | 0.54 | 100.0% | 2.7% |
| B2 | €22,392 | 13.1% | 0.57 | -90.5% | 0.14 | 100.0% | 555.7% |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil -2.6%/jaar, p = 0.61; Sharpe-verschil 0.57, p = 0.03 (2399 dagen)
- H3 (S1 − S3): verschil -40.7%/jaar, p = 0.97; Sharpe-verschil 0.24, p = 0.23 (2399 dagen)
- S1 − B2: verschil -39.1%/jaar, p = 0.89; Sharpe-verschil 0.56, p = 0.04 (2399 dagen)
- S4 − B2: verschil -16.4%/jaar, p = 0.72; Sharpe-verschil 0.43, p = 0.08 (2399 dagen)

## In-sample (tot april 2025)

Periode: 2020-03-07 t/m 2025-03-31

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €16,405 | 10.3% | 1.28 | -11.7% | 0.88 | 8.2% | – |
| S2 | €18,493 | 12.9% | 0.73 | -32.3% | 0.40 | 25.4% | – |
| S3 | €133,176 | 66.7% | 1.18 | -71.4% | 0.93 | 51.4% | – |
| S4 | €52,075 | 38.5% | 1.13 | -45.0% | 0.85 | 31.0% | – |
| S10 | €83,406 | 52.0% | 1.15 | -45.7% | 1.14 | 66.5% | – |
| M1 | €86,761 | 53.2% | 1.31 | -37.1% | 1.43 | 52.7% | – |
| M2 | €49,461 | 37.1% | 1.29 | -24.3% | 1.53 | 35.1% | – |
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

Periode: 2025-04-01 t/m 2026-10-01

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €10,409 | 2.7% | 0.49 | -8.8% | 0.31 | 6.8% | – |
| S2 | €9,892 | -0.7% | 0.07 | -30.7% | -0.02 | 30.7% | – |
| S3 | €6,994 | -21.2% | -0.30 | -62.6% | -0.34 | 42.9% | – |
| S4 | €10,776 | 5.1% | 0.36 | -27.6% | 0.19 | 20.3% | – |
| S10 | €10,687 | 4.5% | 0.32 | -20.9% | 0.22 | 41.2% | – |
| M1 | €11,196 | 7.8% | 0.49 | -23.1% | 0.34 | 34.7% | – |
| M2 | €11,098 | 7.2% | 0.54 | -18.6% | 0.39 | 25.1% | – |
| B1 | €9,671 | -2.2% | 0.15 | -51.7% | -0.04 | 100.0% | – |
| B2 | €7,494 | -17.5% | 0.09 | -73.9% | -0.24 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H4 (S4 CAGR ≥ B2 én drawdown ≤ 70% van B2): rendement ja, drawdown ja
- H2 (S1 − S2): verschil 1.5%/jaar, p = 0.47; Sharpe-verschil 0.43, p = 0.37 (548 dagen)
- H3 (S1 − S3): verschil 16.4%/jaar, p = 0.41; Sharpe-verschil 0.79, p = 0.17 (548 dagen)
- S1 − B2: verschil -3.7%/jaar, p = 0.57; Sharpe-verschil 0.40, p = 0.41 (548 dagen)
- S4 − B2: verschil 0.1%/jaar, p = 0.51; Sharpe-verschil 0.27, p = 0.51 (548 dagen)
