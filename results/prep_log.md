# Data prep log

Raw rows (both sheets): 1,067,371

| Rule | Rows removed |
|---|---:|
| Sheet overlap (2010-12-01..09 in both sheets) | 22,523 |
| Exact duplicate rows | 11,812 |
| Non-product stock codes (postage, fees, adjustments) | 5,980 |
| Price <= 0 | 5,928 |

Clean rows: 1,021,128 (2009-12-01 to 2011-12-09)
Return lines kept as negatives: 17,914
