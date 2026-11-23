# Baseline results


## synthetic_test (1300 sentences)

| Detector | Strict P | Strict R | Strict F1 | Partial F1 | Macro F1 | False-alarm rate on clean sentences |
|---|---|---|---|---|---|---|
| Pre-flight regex (current) |  79.7 |  61.9 |  69.7 |  70.6 |  74.2 |  52.7% (158/300) |
| Regex + checksum |  88.6 |  61.9 |  72.9 |  73.9 |  76.6 |  17.7% (53/300) |

Per-label strict F1 (support = number of gold spans):

| Label | support | Pre-flight regex (current) | Regex + checksum |
|---|---|---|---|
| AADHAAR | 324 |  77.1 |  96.3 |
| PAN | 240 | 100.0 | 100.0 |
| PHONE | 232 |  80.7 |  80.7 |
| EMAIL | 138 | 100.0 | 100.0 |
| BANK_ACCOUNT | 284 |  48.2 |  48.2 |
| IFSC | 135 |  87.7 |  87.7 |
| GSTIN | 172 | 100.0 | 100.0 |
| PERSON | 611 |   0.0 |   0.0 |

## handwritten_test (136 sentences)

| Detector | Strict P | Strict R | Strict F1 | Partial F1 | Macro F1 | False-alarm rate on clean sentences |
|---|---|---|---|---|---|---|
| Pre-flight regex (current) |  74.1 |  59.5 |  66.0 |  66.0 |  76.2 |  46.2% (18/39) |
| Regex + checksum |  82.6 |  59.5 |  69.2 |  69.2 |  78.6 |  33.3% (13/39) |

Per-label strict F1 (support = number of gold spans):

| Label | support | Pre-flight regex (current) | Regex + checksum |
|---|---|---|---|
| AADHAAR | 16 |  56.1 |  72.7 |
| PAN | 15 |  85.7 |  88.2 |
| PHONE | 28 |  91.5 |  91.5 |
| EMAIL | 14 | 100.0 | 100.0 |
| BANK_ACCOUNT | 13 |  81.8 |  81.8 |
| IFSC | 9 |  94.7 |  94.7 |
| GSTIN | 10 | 100.0 | 100.0 |
| PERSON | 63 |   0.0 |   0.0 |
