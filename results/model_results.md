# DistilBERT results vs baselines

Strict = exact start, end and label. False alarms = share of PII-free sentences with any alert.


## synthetic_test (1300 sentences)

| System | Strict P | Strict R | Strict F1 | Partial F1 | Macro F1 | False alarms |
|---|---|---|---|---|---|---|
| Pre-flight regex |  79.7 |  61.9 |  69.7 |  70.6 |  74.2 |  52.7% (158/300) |
| Regex + checksum |  88.6 |  61.9 |  72.9 |  73.9 |  76.6 |  17.7% (53/300) |
| DistilBERT |  75.7 |  86.7 |  80.8 |  89.1 |  77.0 |   2.0% (6/300) |
| DistilBERT + checksum filter |  94.6 |  86.7 |  90.4 |  92.2 |  87.4 |   0.0% (0/300) |
| DistilBERT + post-proc |  91.6 |  95.0 |  93.3 |  95.3 |  95.0 |   2.0% (6/300) |
| DistilBERT + post-proc + checksum |  95.3 |  95.0 |  95.2 |  96.8 |  96.6 |   0.0% (0/300) |
| DistilBERT + post-proc + words + checksum |  95.5 |  95.2 |  95.4 |  96.8 |  96.7 |   0.0% (0/300) |
| DistilBERT + normalise + post-proc + repair (final) |  96.9 |  97.7 |  97.3 |  98.5 |  98.3 |   0.0% (0/300) |

Per-label strict F1:

| Label | support | Pre-flight regex | Regex + checksum | DistilBERT | DistilBERT + checksum filter | DistilBERT + post-proc | DistilBERT + post-proc + checksum | DistilBERT + post-proc + words + checksum | DistilBERT + normalise + post-proc + repair (final) |
|---|---|---|---|---|---|---|---|---|---|
| AADHAAR | 324 |  77.1 |  96.3 |  91.5 |  96.5 |  92.5 |  96.5 |  96.5 |  99.8 |
| PAN | 240 | 100.0 | 100.0 |  68.5 |  95.1 | 100.0 | 100.0 | 100.0 | 100.0 |
| PHONE | 232 |  80.7 |  80.7 |  90.6 |  93.3 |  94.3 |  94.5 |  94.5 |  98.5 |
| EMAIL | 138 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| BANK_ACCOUNT | 284 |  48.2 |  48.2 |  81.3 |  89.5 |  82.2 |  89.8 |  89.8 |  94.0 |
| IFSC | 135 |  87.7 |  87.7 |  47.5 |  69.6 |  98.9 |  99.6 |  99.6 | 100.0 |
| GSTIN | 172 | 100.0 | 100.0 |  44.8 |  62.9 | 100.0 | 100.0 | 100.0 | 100.0 |
| PERSON | 611 |   0.0 |   0.0 |  92.1 |  92.1 |  92.1 |  92.1 |  92.7 |  94.1 |

## handwritten_test (136 sentences)

| System | Strict P | Strict R | Strict F1 | Partial F1 | Macro F1 | False alarms |
|---|---|---|---|---|---|---|
| Pre-flight regex |  74.1 |  59.5 |  66.0 |  66.0 |  76.2 |  46.2% (18/39) |
| Regex + checksum |  82.6 |  59.5 |  69.2 |  69.2 |  78.6 |  33.3% (13/39) |
| DistilBERT |  87.1 |  92.3 |  89.6 |  93.1 |  90.5 |   5.1% (2/39) |
| DistilBERT + checksum filter |  92.8 |  92.3 |  92.5 |  95.5 |  94.2 |   2.6% (1/39) |
| DistilBERT + post-proc |  88.2 |  93.5 |  90.8 |  94.2 |  92.9 |   5.1% (2/39) |
| DistilBERT + post-proc + checksum |  92.9 |  93.5 |  93.2 |  96.1 |  96.0 |   2.6% (1/39) |
| DistilBERT + post-proc + words + checksum |  98.2 |  95.8 |  97.0 |  97.6 |  97.2 |   2.6% (1/39) |
| DistilBERT + normalise + post-proc + repair (final) |  99.4 |  98.8 |  99.1 |  99.1 |  99.4 |   2.6% (1/39) |

Per-label strict F1:

| Label | support | Pre-flight regex | Regex + checksum | DistilBERT | DistilBERT + checksum filter | DistilBERT + post-proc | DistilBERT + post-proc + checksum | DistilBERT + post-proc + words + checksum | DistilBERT + normalise + post-proc + repair (final) |
|---|---|---|---|---|---|---|---|---|---|
| AADHAAR | 16 |  56.1 |  72.7 |  91.4 | 100.0 |  91.4 | 100.0 | 100.0 | 100.0 |
| PAN | 15 |  85.7 |  88.2 |  82.4 |  93.3 |  87.5 |  93.3 |  93.3 |  96.8 |
| PHONE | 28 |  91.5 |  91.5 |  94.7 |  98.2 |  94.7 |  98.2 |  98.2 | 100.0 |
| EMAIL | 14 | 100.0 | 100.0 |  93.3 | 100.0 |  93.3 | 100.0 | 100.0 | 100.0 |
| BANK_ACCOUNT | 13 |  81.8 |  81.8 |  96.0 |  96.0 |  96.0 |  96.0 |  96.0 | 100.0 |
| IFSC | 9 |  94.7 |  94.7 |  80.0 |  80.0 |  94.1 |  94.1 |  94.1 | 100.0 |
| GSTIN | 10 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| PERSON | 63 |   0.0 |   0.0 |  86.2 |  86.2 |  86.2 |  86.2 |  96.0 |  98.4 |

Strict F1 by category (hard_negatives has no PII, so it shows false-alarm sentences instead):

| Category | n | Pre-flight regex | Regex + checksum | DistilBERT | DistilBERT + checksum filter | DistilBERT + post-proc | DistilBERT + post-proc + checksum | DistilBERT + post-proc + words + checksum | DistilBERT + normalise + post-proc + repair (final) |
|---|---|---|---|---|---|---|---|---|---|
| ai_prompts | 26 |  69.6 |  69.6 |  94.5 |  95.6 |  94.5 |  95.6 |  95.6 | 100.0 |
| emails_messages | 18 |  66.7 |  66.7 |  94.9 |  96.6 |  94.9 |  96.6 | 100.0 | 100.0 |
| forms_records | 14 |  64.2 |  66.7 |  95.4 |  98.4 |  95.4 |  98.4 |  98.4 |  98.4 |
| code_logs | 14 |  71.0 |  75.9 |  81.3 |  92.9 |  87.5 |  96.6 |  96.6 |  96.6 |
| hinglish_informal | 18 |  68.8 |  66.7 |  60.0 |  63.2 |  65.0 |  66.7 |  94.1 |  97.1 |
| hard_negatives | 28 | 13/28 alarms | 7/28 alarms | 0/28 alarms | 0/28 alarms | 0/28 alarms | 0/28 alarms | 0/28 alarms | 0/28 alarms |
| mixed_tricky | 18 |  74.6 |  81.5 |  94.9 |  96.6 |  94.9 |  96.6 |  96.6 | 100.0 |
