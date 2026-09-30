# Backtest v1 — kosten 0.30% per kant

> Waarschuwing: data van de huidige Bitvavo-markten. Verdwenen munten ontbreken (survivorship bias),
> dus de cijfers zijn te optimistisch. Een paper-test van maanden wijst géén winnaar aan.

## Hele periode

Periode: 2020-03-07 t/m 2026-09-29

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €15,839 | 7.3% | 0.97 | -14.3% | 0.51 | 8.1% | 377.8% |
| S2 | €17,219 | 8.6% | 0.52 | -36.8% | 0.23 | 28.0% | 194.2% |
| S3 | €85,095 | 38.5% | 0.87 | -71.9% | 0.54 | 50.9% | 1306.8% |
| B1 | €90,116 | 39.8% | 0.87 | -73.6% | 0.54 | 100.0% | 2.7% |
| B2 | €17,613 | 9.1% | 0.52 | -91.6% | 0.10 | 100.0% | 526.1% |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H2 (S1 − S2): verschil -3.0%/jaar, p = 0.65; Sharpe-verschil 0.45, p = 0.08 (2397 dagen)
- H3 (S1 − S3): verschil -40.2%/jaar, p = 0.97; Sharpe-verschil 0.09, p = 0.37 (2397 dagen)
- S1 − B2: verschil -35.1%/jaar, p = 0.87; Sharpe-verschil 0.45, p = 0.09 (2397 dagen)

## In-sample (tot april 2025)

Periode: 2020-03-07 t/m 2025-03-31

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €16,028 | 9.8% | 1.20 | -11.6% | 0.84 | 8.2% | – |
| S2 | €18,503 | 12.9% | 0.72 | -32.3% | 0.40 | 25.8% | – |
| S3 | €130,146 | 65.9% | 1.17 | -70.4% | 0.94 | 52.2% | – |
| B1 | €93,774 | 55.5% | 1.02 | -73.6% | 0.75 | 100.0% | – |
| B2 | €27,588 | 22.2% | 0.67 | -89.7% | 0.25 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H2 (S1 − S2): verschil -4.4%/jaar, p = 0.66; Sharpe-verschil 0.48, p = 0.10 (1850 dagen)
- H3 (S1 − S3): verschil -57.9%/jaar, p = 0.98; Sharpe-verschil 0.03, p = 0.46 (1850 dagen)
- S1 − B2: verschil -48.1%/jaar, p = 0.88; Sharpe-verschil 0.52, p = 0.09 (1850 dagen)

## Holdout (vanaf april 2025, opnieuw op €10.000 gezet) — hier telt het

Periode: 2025-04-01 t/m 2026-09-29

| Portefeuille | Eindwaarde | CAGR | Sharpe | Max drawdown | Calmar | Gem. belegd | Omzet/jaar |
|---|---|---|---|---|---|---|---|
| S1 | €9,884 | -0.8% | -0.12 | -10.1% | -0.08 | 7.7% | – |
| S2 | €9,335 | -4.5% | -0.12 | -33.3% | -0.14 | 35.3% | – |
| S3 | €6,538 | -24.7% | -0.50 | -59.3% | -0.42 | 46.5% | – |
| B1 | €9,622 | -2.5% | 0.15 | -51.7% | -0.05 | 100.0% | – |
| B2 | €6,467 | -25.3% | -0.14 | -72.1% | -0.35 | 100.0% | – |

**Hypotheses** (zie HYPOTHESIS.md; een p-waarde onder 0,05 telt pas na ≥2 jaar forward):

- H1 (S1 drawdown ≤ 50% van B2 én Sharpe S1 ≥ B2): drawdown ja, Sharpe ja
- H2 (S1 − S2): verschil 1.9%/jaar, p = 0.46; Sharpe-verschil 0.01, p = 0.69 (546 dagen)
- H3 (S1 − S3): verschil 19.6%/jaar, p = 0.33; Sharpe-verschil 0.38, p = 0.30 (546 dagen)
- S1 − B2: verschil 8.0%/jaar, p = 0.46; Sharpe-verschil 0.02, p = 0.70 (546 dagen)
