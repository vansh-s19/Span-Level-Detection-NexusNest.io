# DistilBERT results vs baselines

Strict = exact start, end and label. False alarms = share of PII-free sentences with any alert.


## synthetic_test (1300 sentences)

| System | Strict P | Strict R | Strict F1 | Partial F1 | Macro F1 | False alarms |
|---|---|---|---|---|---|---|
| Pre-flight regex |  79.7 |  61.9 |  69.7 |  70.6 |  74.2 |  52.7% (158/300) |
| Regex + checksum |  88.6 |  61.9 |  72.9 |  73.9 |  76.6 |  17.7% (53/300) |
| DistilBERT |  75.7 |  86.7 |  80.8 |  89.1 |  77.0 |   2.0% (6/300) |
| DistilBERT + checksum filter |  86.9 |  86.7 |  86.8 |  91.5 |  83.3 |   0.3% (1/300) |
| DistilBERT + post-proc |  91.6 |  95.0 |  93.3 |  95.3 |  95.0 |   2.0% (6/300) |
| DistilBERT + post-proc + checksum (final) |  92.7 |  95.0 |  93.9 |  95.8 |  95.5 |   0.3% (1/300) |

Per-label strict F1:

| Label | support | Pre-flight regex | Regex + checksum | DistilBERT | DistilBERT + checksum filter | DistilBERT + post-proc | DistilBERT + post-proc + checksum (final) |
|---|---|---|---|---|---|---|---|
| AADHAAR | 324 |  77.1 |  96.3 |  91.5 |  96.5 |  92.5 |  96.5 |
| PAN | 240 | 100.0 | 100.0 |  68.5 |  95.1 | 100.0 | 100.0 |
| PHONE | 232 |  80.7 |  80.7 |  90.6 |  90.6 |  94.3 |  94.3 |
| EMAIL | 138 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| BANK_ACCOUNT | 284 |  48.2 |  48.2 |  81.3 |  81.3 |  82.2 |  82.2 |
| IFSC | 135 |  87.7 |  87.7 |  47.5 |  47.5 |  98.9 |  98.9 |
| GSTIN | 172 | 100.0 | 100.0 |  44.8 |  62.9 | 100.0 | 100.0 |
| PERSON | 611 |   0.0 |   0.0 |  92.1 |  92.1 |  92.1 |  92.1 |

## handwritten_test (136 sentences)

| System | Strict P | Strict R | Strict F1 | Partial F1 | Macro F1 | False alarms |
|---|---|---|---|---|---|---|
| Pre-flight regex |  74.1 |  59.5 |  66.0 |  66.0 |  76.2 |  46.2% (18/39) |
| Regex + checksum |  82.6 |  59.5 |  69.2 |  69.2 |  78.6 |  33.3% (13/39) |
| DistilBERT |  87.1 |  92.3 |  89.6 |  93.1 |  90.5 |   5.1% (2/39) |
| DistilBERT + checksum filter |  90.6 |  92.3 |  91.4 |  94.4 |  92.9 |   5.1% (2/39) |
| DistilBERT + post-proc |  88.2 |  93.5 |  90.8 |  94.2 |  92.9 |   5.1% (2/39) |
| DistilBERT + post-proc + checksum (final) |  90.8 |  93.5 |  92.1 |  95.0 |  94.7 |   5.1% (2/39) |

Per-label strict F1:

| Label | support | Pre-flight regex | Regex + checksum | DistilBERT | DistilBERT + checksum filter | DistilBERT + post-proc | DistilBERT + post-proc + checksum (final) |
|---|---|---|---|---|---|---|---|
| AADHAAR | 16 |  56.1 |  72.7 |  91.4 | 100.0 |  91.4 | 100.0 |
| PAN | 15 |  85.7 |  88.2 |  82.4 |  93.3 |  87.5 |  93.3 |
| PHONE | 28 |  91.5 |  91.5 |  94.7 |  94.7 |  94.7 |  94.7 |
| EMAIL | 14 | 100.0 | 100.0 |  93.3 |  93.3 |  93.3 |  93.3 |
| BANK_ACCOUNT | 13 |  81.8 |  81.8 |  96.0 |  96.0 |  96.0 |  96.0 |
| IFSC | 9 |  94.7 |  94.7 |  80.0 |  80.0 |  94.1 |  94.1 |
| GSTIN | 10 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| PERSON | 63 |   0.0 |   0.0 |  86.2 |  86.2 |  86.2 |  86.2 |

Strict F1 by category (hard_negatives has no PII, so it shows false-alarm sentences instead):

| Category | n | Pre-flight regex | Regex + checksum | DistilBERT | DistilBERT + checksum filter | DistilBERT + post-proc | DistilBERT + post-proc + checksum (final) |
|---|---|---|---|---|---|---|---|
| ai_prompts | 26 |  69.6 |  69.6 |  94.5 |  95.6 |  94.5 |  95.6 |
| emails_messages | 18 |  66.7 |  66.7 |  94.9 |  94.9 |  94.9 |  94.9 |
| forms_records | 14 |  64.2 |  66.7 |  95.4 |  98.4 |  95.4 |  98.4 |
| code_logs | 14 |  71.0 |  75.9 |  81.3 |  83.9 |  87.5 |  87.5 |
| hinglish_informal | 18 |  68.8 |  66.7 |  60.0 |  63.2 |  65.0 |  66.7 |
| hard_negatives | 28 | 13/28 alarms | 7/28 alarms | 0/28 alarms | 0/28 alarms | 0/28 alarms | 0/28 alarms |
| mixed_tricky | 18 |  74.6 |  81.5 |  94.9 |  96.6 |  94.9 |  96.6 |
