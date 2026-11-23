# Span-Level PII Detection for Indian Identifiers

A machine-learning approach to finding **personally identifiable information (PII)** in free text at the **span level**: not just "this message contains PII", but *exactly which characters* are an Aadhaar number, a PAN, a phone number, a name, and so on.

This project grew out of [Pre-flight](#background-pre-flight), a Chrome extension that warns employees before they paste sensitive data into AI chat tools. Pre-flight's detection is rule-based (regex). This repository measures where those rules fail and builds an ML model to fix it.

> **Status:** data pipeline, hand-written test set and rule-based baselines are complete. Model training is the next stage.

---

## Contents
1. [The problem](#1-the-problem)
2. [Task definition](#2-task-definition)
3. [Approach](#3-approach)
4. [Dataset](#4-dataset)
5. [Evaluation](#5-evaluation)
6. [Baseline results](#6-baseline-results)
7. [Repository structure](#7-repository-structure)
8. [Reproduce](#8-reproduce)
9. [Existing PII tools (research)](#9-existing-pii-tools-research)
10. [Limitations](#10-limitations)
11. [Roadmap](#11-roadmap)
12. [Attribution and licences](#12-attribution-and-licences)

---

## 1. The problem

A regex such as `\d{4}[\s-]?\d{4}[\s-]?\d{4}` matches **every** 12-digit number. Order IDs, invoice numbers, tracking numbers and even `+91` phone numbers all look like Aadhaar numbers to it.

Adding the official Aadhaar checksum (Verhoeff) helps, but about **1 in 10 random 12-digit numbers passes the checksum by chance**. So a checksum alone cannot tell `Order 4638 8498 5568` from `Aadhaar 2798 1933 1904`. Only the **context** can.

Rules also cannot find PII that has no fixed format, such as **names** or account numbers written without the word "account".

## 2. Task definition

**Span-level named-entity recognition (NER).** Given a text, return every PII item as `(start, end, label)` character offsets:

```text
"Aadhaar 2798 1933 1904 and order 2061 4431 7746"
 -> [{"start": 8, "end": 22, "label": "AADHAAR", "text": "2798 1933 1904"}]
     (the order number is correctly NOT returned)
```

**8 labels:**

| Label | What it is | Format |
|---|---|---|
| `AADHAAR` | Indian national ID | 12 digits, first digit 2-9, Verhoeff check digit |
| `PAN` | Income-tax ID | 5 letters, 4 digits, 1 letter; 4th letter = holder type |
| `PHONE` | Indian mobile | 10 digits starting 6-9, optional +91 / 0 prefix |
| `EMAIL` | E-mail address | standard |
| `BANK_ACCOUNT` | Bank account number | 9-18 digits |
| `IFSC` | Bank branch code | 4 letters + `0` + 6 characters |
| `GSTIN` | GST registration | 15 characters, contains a PAN, mod-36 check character |
| `PERSON` | A person's name | no fixed format |

## 3. Approach

| Stage | What | Status |
|---|---|---|
| 1 | Research existing PII models and services | done ([docs](docs/research_existing_pii_solutions.md)) |
| 2 | Build a labelled span-level dataset | done |
| 3 | Measure rule-based baselines (Pre-flight's regex, regex + checksum) | done |
| 4 | Train an ML model (token classification) | next |
| 5 | Evaluate, analyse errors, improve | planned |

**Why ML here.** The model reads the words *around* a value ("Aadhaar …" vs "Order …"), so it can separate real identifiers from look-alikes, and it can learn things with no fixed shape, like names. Checksums are kept as an optional post-filter, so the final system can combine both strengths.

## 4. Dataset

No public dataset covers Indian identifiers with a clear licence, so the training data combines **generated** examples with a filtered slice of a **public** dataset. The test data includes a **hand-written** set the generator never produced.

### 4.1 Synthetic data (`datagen/`)

| Component | What it does |
|---|---|
| `checksums.py` | Verhoeff (Aadhaar) and mod-36 (GSTIN) check algorithms, verified against published examples |
| `values.py` | Makes realistic values (valid Aadhaar and GSTIN, PANs with real holder types, Indian phone formats, IFSC with real bank codes) **and hard negatives** (12-digit order IDs, PAN-shaped SKUs, IFSC-shaped item codes, year ranges, 10-digit ticket numbers) |
| `templates.py` | 95 PII sentence patterns + 48 no-PII patterns, styled like real input: AI prompts, e-mails, forms, CSV / JSON / SQL, logs, Hinglish |
| `generate.py` | Fills templates, records exact character offsets, splits by template, validates every offset |

**Key design decisions**

- **Template-level split (anti-leakage).** Each template belongs to exactly one of train, validation or test. A good test score therefore means the model learned the PII itself, not the sentence wording.
- **Label coverage.** The split is reshuffled (deterministically) until every label appears in at least 2 templates in both validation and test. The first random split had zero IFSC examples in validation; this rule fixes that.
- **Hard negatives.** About 23% of examples contain only look-alikes, so the model learns what is *not* PII.
- **Reproducible.** One seed (`42`) regenerates identical files.

### 4.2 Public data: ai4privacy open-pii-masking-500k (`datagen/ai4privacy.py`)

5,000 English rows from [ai4privacy/open-pii-masking-500k-ai4privacy](https://huggingface.co/datasets/ai4privacy/open-pii-masking-500k-ai4privacy) (CC BY 4.0) add realistic variety for names and e-mails.

| Their label | Our handling | Why |
|---|---|---|
| `GIVENNAME`, `SURNAME` | -> `PERSON` (adjacent first + last name merged) | match our full-name convention |
| `EMAIL` | -> `EMAIL` | direct match |
| `TELEPHONENUM` | row dropped | mostly non-Indian formats; our `PHONE` means Indian numbers |
| `IDCARDNUM`, `TAXNUM`, `SOCIALNUM`, `PASSPORTNUM`, `DRIVERLICENSENUM`, `CREDITCARDNUMBER` | row dropped | labelling real-looking IDs as "not PII" would teach the wrong thing |
| everything else (city, date, street…) | plain text | outside our 8 labels |

These rows go into **training only**. Validation and test stay 100% our own data. The ai4privacy 400k release was not used: its licence is non-commercial, and neither release has Aadhaar or PAN labels (India-region IDs there are generic `IDCARDNUM` values that do not follow the PAN format).

### 4.3 Hand-written test set (`data/handwritten/`)

136 realistic sentences written by hand, in 7 categories: AI prompts, e-mails, forms, code and logs, Hinglish, hard negatives, and mixed tricky cases. They use **names not present in the generator** and include **12 deliberate traps**: order and tracking numbers that pass the Aadhaar checksum by chance. Labels are written as `[[LABEL|value]]` in `test_annotated.txt` for easy human review, and every labelled value is validated by the converter.

### 4.4 Final numbers

| Split | Sentences | Source | Notes |
|---|---|---|---|
| train | 15,400 | 10,400 synthetic + 5,000 ai4privacy | PERSON 11,584 · PHONE 2,780 · EMAIL 2,026 · PAN 1,864 · AADHAAR 1,399 · BANK_ACCOUNT 1,010 · GSTIN 604 · IFSC 511 |
| validation | 1,300 | synthetic | used for model selection |
| test (synthetic) | 1,300 | synthetic, unseen templates | stable per-label numbers |
| test (hand-written) | 136 | hand-written | realistic; small per-label counts |

Each line of a `.jsonl` file:

```json
{"id": "train-000001", "text": "UID 350490613959 linked with mobile 9162019700",
 "spans": [{"start": 4, "end": 16, "label": "AADHAAR", "text": "350490613959"},
           {"start": 36, "end": 46, "label": "PHONE", "text": "9162019700"}],
 "kind": "positive", "template_id": "P081", "source": "synthetic"}
```

## 5. Evaluation

Implemented once in `pii_detect/metrics.py` and used for every detector.

- **Strict match:** same label and exactly the same start and end. This is the headline metric.
- **Partial match:** same label and overlapping characters. It shows whether errors are misses or boundary mistakes.
- **Precision, recall, F1** per label, plus micro-average (all labels pooled) and macro-average (each label counts equally).
- **False-alarm rate:** the share of sentences with no PII where the detector still raised an alert. For a tool like Pre-flight this is what users feel; every false alarm interrupts them.

Token-level accuracy is deliberately **not** used: most tokens are not PII, so a model that predicts "no PII" everywhere would still score above 90%.

## 6. Baseline results

Pre-flight's regex was ported faithfully from its `detectors.js` (same patterns, same `isPlausibleAadhaar` heuristic). "Regex + checksum" adds Verhoeff, the GSTIN checksum and the PAN holder-type rule.

| Test set | Detector | Strict P | Strict R | Strict F1 | False alarms on clean sentences |
|---|---|---|---|---|---|
| Synthetic (1,300) | Pre-flight regex | 79.7 | 61.9 | 69.7 | **52.7%** |
| | Regex + checksum | 88.6 | 61.9 | 72.9 | 17.7% |
| Hand-written (136) | Pre-flight regex | 74.1 | 59.5 | 66.0 | **46.2%** |
| | Regex + checksum | 82.6 | 59.5 | 69.2 | 33.3% |

**What the errors show** (full list in [`results/baseline_errors.md`](results/baseline_errors.md)):

1. **12-digit look-alikes.** Pre-flight's regex flagged 192 order and reference numbers as Aadhaar on the synthetic test. The checksum cut this to 25; those 25 pass the checksum by chance and only context can reject them.
2. **A phone becomes an Aadhaar.** `+919811230045` (91 + a mobile number = 12 digits) is flagged as Aadhaar by the regex.
3. **Shape-identical codes.** PAN-shaped SKUs and IFSC-shaped item codes are always flagged.
4. **Bank accounts (F1 48%).** The rule needs a cue word, so "acct", "Acc No" or no cue at all is missed. A greedy pattern also swallows trailing text (`3199310307441 - 11`).
5. **Phones with a leading 0** (`08875840390`) are missed.
6. **Names: 0%.** Rules cannot detect `PERSON`, the most frequent PII type.

Rules are excellent on rigid formats (PAN, GSTIN, e-mail: 100%) and weak on **context** and on **PII without a fixed format**. That is the gap the ML model targets.

## 7. Repository structure

```text
datagen/                    dataset construction
  checksums.py              Verhoeff + GSTIN check algorithms
  values.py                 PII value makers and hard negatives
  templates.py              sentence templates (positive / negative)
  generate.py               synthetic dataset builder (template-level split)
  ai4privacy.py             filter + merge 5k ai4privacy rows into train
  handwritten.py            convert [[LABEL|value]] markup to JSONL
pii_detect/                 detection and evaluation
  metrics.py                span-level strict / partial metrics, false-alarm rate
  baselines.py              Pre-flight regex port, regex + checksum
  run_baselines.py          evaluate baselines on both test sets
  data.py                   loaders, label list, test-set paths
data/
  synthetic/                generated train / validation / test + stats + samples
  ai4privacy/train_5k.jsonl filtered public sample
  final/                    what models train and evaluate on
  handwritten/              hand-written test set (annotated source + JSONL)
results/                    baseline tables, JSON, error examples
docs/                       research notes on existing PII tools
```

## 8. Reproduce

Python 3.11. Stages 1-3 need only the standard library.

```bash
python3.11 -m venv .venv

# 1. synthetic data
.venv/bin/python -m datagen.generate

# 2. ai4privacy sample (download ~142 MB first)
mkdir -p data/raw/ai4privacy
curl -L -o data/raw/ai4privacy/open_pii_500k_part.jsonl \
  "https://huggingface.co/datasets/ai4privacy/open-pii-masking-500k-ai4privacy/resolve/main/data/validation/test.jsonl"
.venv/bin/python -m datagen.ai4privacy

# 3. hand-written test set
.venv/bin/python -m datagen.handwritten

# 4. baselines
.venv/bin/python -m pii_detect.run_baselines
```

All generated files are already committed, so steps 1-3 are only needed to regenerate them.

## 9. Existing PII tools (research)

Summary of [`docs/research_existing_pii_solutions.md`](docs/research_existing_pii_solutions.md):

| Tool | Type | Indian IDs | Notes |
|---|---|---|---|
| Microsoft Presidio | open-source framework (regex + spaCy/transformer NER) | via custom recognizers | orchestrates rules and models; good baseline |
| GLiNER-PII (urchade, NVIDIA, knowledgator) | zero-shot NER | not trained on them | label names given at run time |
| Piiranha (mDeBERTa-v3) | token classifier, 17 types | no | non-commercial licence; reports token accuracy, which is inflated by class imbalance |
| AWS Comprehend | cloud API | Aadhaar, PAN, NREGA, voter ID | English and Spanish only; no custom types |
| Google Cloud DLP | cloud API | `INDIA_AADHAAR_INDIVIDUAL`, `INDIA_PAN_INDIVIDUAL` | text leaves the device |
| Azure AI Language | cloud API | PAN (Aadhaar likely as "Unique Identification Number") | support varies by language |

A recurring pattern across Indian-focused models: **a model for context-dependent PII plus checksums for structured IDs**. This project follows that design.

## 10. Limitations

- **Synthetic-heavy data.** Scores on the synthetic test are likely higher than on real-world text. The hand-written set and the baselines exist to keep results honest.
- **Small hand-written set.** Per-label counts are small (IFSC 9, GSTIN 10), so those per-label scores are noisy.
- **Addresses are out of scope.** Street addresses and cities are PII in practice but are not among the 8 labels.
- **English and Hinglish (Latin script) only.** No Devanagari or other scripts yet.

## 11. Roadmap

- [x] Research existing tools
- [x] Synthetic + public + hand-written datasets
- [x] Rule-based baselines and evaluation framework
- [ ] Model selection and training (token classification)
- [ ] Error analysis and improvements (e.g. more data for weak labels, checksum post-filter, threshold tuning)
- [ ] Comparison with Presidio and a pretrained PII model
- [ ] Integration notes for Pre-flight

## 12. Attribution and licences

- **ai4privacy open-pii-masking-500k** is used under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The sample in `data/ai4privacy/` is a filtered and relabelled subset.
- All synthetic and hand-written examples are fictitious. Names, numbers and e-mail addresses were generated or invented and do not belong to real people.

## Background: Pre-flight

Pre-flight is a Chrome extension (Manifest V3) that intercepts prompts on ChatGPT, Claude, Gemini, Copilot and Perplexity, scans them for sensitive data, and warns the user before sending. Its first detection layer is the regex engine measured in [section 6](#6-baseline-results). This project's model is designed to replace or sit alongside that layer.
