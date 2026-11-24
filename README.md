# Span-Level PII Detection for Indian Identifiers

A machine-learning approach to finding **personally identifiable information (PII)** in free text at the **span level**: not just "this message contains PII", but *exactly which characters* are an Aadhaar number, a PAN, a phone number, a name, and so on.

This project grew out of [Pre-flight](#background-pre-flight), a Chrome extension that warns employees before they paste sensitive data into AI chat tools. Pre-flight's detection is rule-based (regex). This repository measures where those rules fail and builds an ML model to fix it.

> **Status:** a fine-tuned DistilBERT model plus a small rule-based post-processing step is trained and evaluated.
>
> | Test set | Pre-flight regex (strict F1 / false alarms) | **Final system** (strict F1 / false alarms) |
> |---|---|---|
> | Synthetic (1,300) | 69.7 / 52.7% | **93.9 / 0.3%** |
> | Hand-written (136) | 66.0 / 46.2% | **92.1 / 5.1%** |

---

## Contents
1. [The problem](#1-the-problem)
2. [Task definition](#2-task-definition)
3. [Approach](#3-approach)
4. [Dataset](#4-dataset)
5. [Evaluation](#5-evaluation)
6. [Baseline results](#6-baseline-results)
7. [The model](#7-the-model)
8. [Model results](#8-model-results)
9. [Improving performance](#9-improving-performance)
10. [Repository structure](#10-repository-structure)
11. [Reproduce](#11-reproduce)
12. [Existing PII tools (research)](#12-existing-pii-tools-research)
13. [Limitations](#13-limitations)
14. [Roadmap](#14-roadmap)
15. [Attribution and licences](#15-attribution-and-licences)

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
| 4 | Train an ML model (DistilBERT token classification) | done |
| 5 | Evaluate, analyse errors, improve (post-processing) | done |

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

## 7. The model

**DistilBERT-base-cased, fine-tuned for token classification.**

| Choice | Why |
|---|---|
| Transformer encoder | reads the whole sentence in both directions, so `Order 2798…` and `Aadhaar 2798…` get different predictions |
| DistilBERT | 66M parameters (40% smaller, ~60% faster than BERT-base, ~97% of its accuracy): small enough to run on a laptop and, later, near a browser extension |
| **Cased** | capital letters matter: names (`Rahul`) and codes (`ABCPK1234F`) are case-signalled |
| Fine-tuning | starts from pretrained English knowledge; only needs to learn our 8 labels |

**How text becomes labels (BIO tagging, `pii_detect/tagging.py`).** The tokenizer splits text into sub-word pieces. Each piece gets one of **17 tags**: `O` (not PII) or `B-`/`I-` (beginning / inside) for each of the 8 labels. Character offsets from the tokenizer map gold spans to tags for training, and map predicted tags back to exact character spans at prediction time. Every piece of a span is labelled, not only the first one, because values often do not follow word boundaries (`+91-9876543210`, values inside JSON quotes). A round-trip check (spans → tags → spans) matched on 18,135 of 18,136 examples.

**Training (`pii_detect/train.py`).**

| Setting | Value |
|---|---|
| Loss | cross-entropy per token (special and padding tokens ignored) |
| Optimiser | AdamW, learning rate 5e-5, weight decay 0.01, gradient clipping 1.0 |
| Schedule | linear warm-up for the first 10% of steps, then linear decay |
| Batch size / max length / epochs | 16 / 128 tokens / 4 |
| Hardware | Apple-silicon GPU (MPS), about 3 minutes per epoch |
| Model selection | after every epoch, span-level strict F1 on **validation**; the best epoch is saved. Test sets are never used in training |
| Seed | 42 |

| Epoch | Train loss | Validation strict F1 |
|---|---|---|
| 1 | 0.239 | 78.0 |
| **2** | 0.005 | **88.0** (saved) |
| 3 | 0.001 | 87.1 |
| 4 | 0.0003 | 87.8 |

Training loss kept falling after epoch 2 but validation did not improve: the start of overfitting to the synthetic templates. Selecting by validation F1 handles this automatically.

## 8. Model results

Same test sets and the same metric code as the baselines (`pii_detect/evaluate_model.py`). Full tables: [`results/model_results.md`](results/model_results.md); every remaining error on the hand-written set: [`results/model_errors.md`](results/model_errors.md).

| Test set | System | Strict P | Strict R | Strict F1 | False alarms |
|---|---|---|---|---|---|
| Synthetic (1,300) | Pre-flight regex | 79.7 | 61.9 | 69.7 | 52.7% |
| | Regex + checksum | 88.6 | 61.9 | 72.9 | 17.7% |
| | DistilBERT | 75.7 | 86.7 | 80.8 | 2.0% |
| | DistilBERT + checksum filter | 86.9 | 86.7 | 86.8 | 0.3% |
| | **DistilBERT + post-processing + checksum (final)** | **92.7** | **95.0** | **93.9** | **0.3%** |
| Hand-written (136) | Pre-flight regex | 74.1 | 59.5 | 66.0 | 46.2% |
| | Regex + checksum | 82.6 | 59.5 | 69.2 | 33.3% |
| | DistilBERT | 87.1 | 92.3 | 89.6 | 5.1% |
| | DistilBERT + checksum filter | 90.6 | 92.3 | 91.4 | 5.1% |
| | **Final** | **90.8** | **93.5** | **92.1** | **5.1%** |

**Per-label strict F1, final system vs Pre-flight regex:**

| Label | Synthetic: regex → final | Hand-written: regex → final |
|---|---|---|
| AADHAAR | 77.1 → 96.5 | 56.1 → 100.0 |
| PAN | 100.0 → 100.0 | 85.7 → 93.3 |
| PHONE | 80.7 → 94.3 | 91.5 → 94.7 |
| EMAIL | 100.0 → 100.0 | 100.0 → 93.3 |
| BANK_ACCOUNT | 48.2 → 82.2 | 81.8 → 96.0 |
| IFSC | 87.7 → 98.9 | 94.7 → 94.1 |
| GSTIN | 100.0 → 100.0 | 100.0 → 100.0 |
| PERSON | 0.0 → 92.1 | 0.0 → 86.2 |

**What the model fixed**

- **Context.** Hard-negative sentences (order IDs, PNRs, PAN-shaped SKUs): Pre-flight alerts on 13 of 28, the model on **0 of 28**. All 12 checksum-passing "trap" numbers are correctly ignored.
- **Names** go from 0% to 86–92%, impossible for rules.
- **Bank accounts** are found without a cue word.

**Where it is still weak**

- **Hinglish / informal text: 66.7 F1**, the weakest hand-written category. DistilBERT was pretrained on English.
- **Bank accounts (82 on synthetic)**: no fixed format, so neither checksums nor format rules help.
- One e-mail on the hand-written set is missed, where the regex finds all of them.

## 9. Improving performance

Each step was **tuned on validation only**, then the test sets were run once, so the test numbers are not optimised against.

**Step 1: checksum filter (hybrid).** A neural network cannot compute check digits. After prediction, Aadhaar (Verhoeff), GSTIN (mod-36) and PAN (format + holder-type letter) spans that fail their official check are dropped. Synthetic strict F1 80.8 → 86.8; false alarms 2.0% → 0.3%.

**Step 2: error analysis.** After step 1, IFSC (47.5) and GSTIN (62.9) were the weakest labels, yet partial-match F1 was far higher than strict. The errors were not misses: the model **split one value into pieces with different labels**, because it tags each sub-word piece independently and the three codes look alike (a GSTIN even contains a PAN):

```text
gold   GSTIN 15QYGFL5368X1ZF       ->  model: GSTIN "15" + PAN "QYGFL5368X1ZF"
gold   IFSC  KKBK0911578           ->  model: PAN "KKBK091157" + IFSC "8"
```

**Step 3: span post-processing (`postprocess()` in `pii_detect/model.py`), no retraining.**

1. **Merge** predicted spans that touch (no character between them) into one span.
2. **Vote** one label for the merged span by summed probability.
3. **Format check:** if a PAN / IFSC / GSTIN value fits exactly one official format, that format sets the label.

Effect of each sub-step on **validation** (with checksum filter: final row):

| Post-processing | Strict F1 | PAN | IFSC | GSTIN |
|---|---|---|---|---|
| none | 88.0 | 67.5 | 59.4 | 84.3 |
| merge | 93.2 | 84.5 | 81.2 | 95.5 |
| merge + vote | 93.1 | 84.2 | 80.1 | 95.5 |
| merge + vote + format | 95.9 | 99.5 | 99.3 | 100.0 |
| + checksum filter | **96.8** | 100.0 | 99.3 | 100.0 |

Merging and the format check did the work; **the probability vote did not help**. The model was confidently wrong on those pieces, so its own probabilities could not correct the label. Structure rules could. On the synthetic test this lifted IFSC 47.5 → 98.9 and GSTIN 62.9 → 100.

**Design summary:** the model decides *where* PII is, using context; rules settle what is certain from structure.

**Next candidates:** more Hinglish and bank-account training data (the remaining weak spots), a CRF output layer (learns valid tag sequences instead of fixing them afterwards), and a multilingual encoder for Hinglish.

## 10. Repository structure

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
  tagging.py                spans <-> BIO token tags
  train.py                  fine-tune DistilBERT, keep best epoch by validation F1
  model.py                  load model, predict spans, post-processing, checksum filter
  evaluate_model.py         compare model and baselines on both test sets
data/
  synthetic/                generated train / validation / test + stats + samples
  ai4privacy/train_5k.jsonl filtered public sample
  final/                    what models train and evaluate on
  handwritten/              hand-written test set (annotated source + JSONL)
results/                    baseline + model tables, JSON, error examples
models/                     trained checkpoint (git-ignored; recreate with train.py)
docs/                       research notes on existing PII tools
```

## 11. Reproduce

Python 3.11. Data and baselines need only the standard library; training needs `requirements.txt`.

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

# 5. train (downloads distilbert-base-cased; ~12 min on an Apple-silicon GPU)
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pii_detect.train

# 6. evaluate model vs baselines
.venv/bin/python -m pii_detect.evaluate_model
```

Use the trained model directly:

```python
from pii_detect.model import PIIModel
m = PIIModel.load("models/distilbert-pii")
m.predict("my aadhar is 2798 1933 1904", postprocess_level=3, checksum_filter=True)
```

All generated files are already committed, so steps 1-3 are only needed to regenerate them. The model checkpoint is not committed (size); step 5 recreates it.

## 12. Existing PII tools (research)

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

## 13. Limitations

- **Synthetic-heavy data.** The model's training loss reached ~0 by epoch 2 and the synthetic test (93.9) is easier than real text. The hand-written set and the baselines exist to keep results honest.
- **Small hand-written set.** Per-label counts are small (IFSC 9, GSTIN 10), so those per-label scores are noisy.
- **Addresses are out of scope.** Street addresses and cities are PII in practice but are not among the 8 labels.
- **English and Hinglish (Latin script) only.** No Devanagari or other scripts yet; Hinglish is the weakest category (66.7 F1).
- **Single model.** Only DistilBERT was trained; comparisons with other architectures (e.g. CRF, DeBERTa, GLiNER) are future work.
- **Format rules assume canonical writing.** A PAN written with spaces inside it is not re-labelled by the format check.

## 14. Roadmap

- [x] Research existing tools
- [x] Synthetic + public + hand-written datasets
- [x] Rule-based baselines and evaluation framework
- [x] Model training (DistilBERT token classification)
- [x] Error analysis and improvements (checksum filter, span post-processing)
- [ ] More Hinglish and bank-account training data
- [ ] Comparison with Presidio and a pretrained PII model
- [ ] Integration notes for Pre-flight

## 15. Attribution and licences

- **ai4privacy open-pii-masking-500k** is used under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The sample in `data/ai4privacy/` is a filtered and relabelled subset.
- All synthetic and hand-written examples are fictitious. Names, numbers and e-mail addresses were generated or invented and do not belong to real people.

## Background: Pre-flight

Pre-flight is a Chrome extension (Manifest V3) that intercepts prompts on ChatGPT, Claude, Gemini, Copilot and Perplexity, scans them for sensitive data, and warns the user before sending. Its first detection layer is the regex engine measured in [section 6](#6-baseline-results). This project's model is designed to replace or sit alongside that layer.
