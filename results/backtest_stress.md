# Backtest v1 — kosten 0.60% per kant

> Waarschuwing: data van de huidige Bitvavo-markten. Verdwenen munten ontbreken (survivorship bias),
> dus de cijfers zijn te optimistisch. Een paper-test van maanden wijst géén winnaar aan.

## Hele periode

Periode: 2020-03-07 t/m 2026-09-29

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €14,713 | 6.1% | 0.82 | -16.1% | 0.38 | 8.1% | 376.2% |
| S2 | €16,619 | 8.1% | 0.49 | -37.4% | 0.22 | 28.0% | 194.6% |
| S3 | €65,531 | 33.1% | 0.80 | -77.0% | 0.43 | 51.0% | 1292.3% |
| B1 | €89,848 | 39.8% | 0.87 | -73.6% | 0.54 | 100.0% | 2.7% |
| B2 | €15,836 | 7.3% | 0.50 | -92.2% | 0.08 | 100.0% | 525.3% |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H2 (S1 − S2): verschil -3.5%/jaar, p = 0.69; Sharpe-verschil 0.33, p = 0.17 (2397 dagen)
- H3 (S1 − S3): verschil -37.4%/jaar, p = 0.97; Sharpe-verschil 0.02, p = 0.49 (2397 dagen)
- S1 − B2: verschil -34.7%/jaar, p = 0.86; Sharpe-verschil 0.32, p = 0.20 (2397 dagen)

## In-sample (tot april 2025)

Periode: 2020-03-07 t/m 2025-03-31

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €15,209 | 8.6% | 1.07 | -13.7% | 0.63 | 8.2% | – |
| S2 | €18,049 | 12.4% | 0.69 | -32.7% | 0.38 | 25.8% | – |
| S3 | €107,537 | 59.8% | 1.10 | -72.2% | 0.83 | 52.3% | – |
| B1 | €93,774 | 55.5% | 1.02 | -73.6% | 0.75 | 100.0% | – |
| B2 | €25,426 | 20.2% | 0.66 | -89.9% | 0.22 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H2 (S1 − S2): verschil -5.0%/jaar, p = 0.69; Sharpe-verschil 0.37, p = 0.19 (1850 dagen)
- H3 (S1 − S3): verschil -55.2%/jaar, p = 0.98; Sharpe-verschil -0.03, p = 0.54 (1850 dagen)
- S1 − B2: verschil -47.5%/jaar, p = 0.87; Sharpe-verschil 0.41, p = 0.16 (1850 dagen)

## Holdout (vanaf april 2025, opnieuw op €10.000 gezet) — hier telt het

Periode: 2025-04-01 t/m 2026-09-29

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €9,678 | -2.2% | -0.38 | -11.5% | -0.19 | 7.7% | – |
| S2 | €9,248 | -5.1% | -0.15 | -33.7% | -0.15 | 35.2% | – |
| S3 | €6,094 | -28.2% | -0.62 | -61.9% | -0.46 | 46.5% | – |
| B1 | €9,622 | -2.5% | 0.15 | -51.7% | -0.05 | 100.0% | – |
| B2 | €6,337 | -26.3% | -0.16 | -72.5% | -0.36 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe nee
- H2 (S1 − S2): verschil 1.1%/jaar, p = 0.49; Sharpe-verschil -0.23, p = 0.84 (546 dagen)
- H3 (S1 − S3): verschil 22.8%/jaar, p = 0.28; Sharpe-verschil 0.24, p = 0.41 (546 dagen)
- S1 − B2: verschil 8.0%/jaar, p = 0.46; Sharpe-verschil -0.22, p = 0.85 (546 dagen)
