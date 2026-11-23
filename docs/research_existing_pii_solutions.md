# Existing PII detection models, datasets and services

Research notes for the NexusNest.io assignment. Written 2026-11-23.

**Reliability note.** These notes come from web-search summaries, not from reading each official page in full. Items marked *(verify)* should be checked on the official page before you state them in the technical round. Model-card accuracy numbers are self-reported by the authors.

## 1. The approaches, in one picture

| Approach | How it finds PII | Strength | Weakness |
|---|---|---|---|
| Regex / rules (what Pre-flight does today) | Pattern match, e.g. 12 digits | Fast, explainable, no training data | No context: any 12-digit number matches. Cannot find names or addresses |
| Regex + checksum | Pattern, then validate (Aadhaar uses the Verhoeff checksum) | Far fewer false positives on structured IDs | Still blind to context and to free-text PII |
| Token-classification NER (BERT / DeBERTa / XLM-R) | Model labels each token (BIO tags), spans are rebuilt from tags | Learns context; finds names, addresses, IDs | Needs labelled data; fixed label set |
| Zero-shot NER (GLiNER family) | You pass label names at inference time | Flexible; new label with no retraining | Lower precision on rare or ambiguous labels |
| LLM-based | Prompt an LLM to list PII | Strong on context, any language | Slow, costly, can hallucinate spans, and sends text to a third party |
| Hybrid (rules + model + LLM) | Combine the above | Best practical accuracy | More moving parts |

A recurring design in the Indian-PII models found (Chitragupta, MeridianPII, sakshi-pii-in) is a split. A model handles names, addresses and dates. Deterministic rules plus checksums handle Aadhaar, PAN and similar IDs.

## 2. Open-source libraries and models

### Microsoft Presidio (library)
- An `AnalyzerEngine` runs a registry of recognizers over text. A separate Anonymizer redacts.
- Recognizers can be regex (with checksum validation), spaCy / Stanza / transformer NER, or custom code.
- It is not a single model. It is a framework that orchestrates models and rules, and it is designed to be customised.
- Some recognizers are loose (a driver's licence number can be any 9 digits), so users tune thresholds.
- Best used as a baseline to compare against.

### GLiNER family (zero-shot NER)
- `urchade/gliner_multi_pii-v1`: fine-tuned from `gliner_multi-v2.1` on a synthetic PII dataset made with Mistral. Apache-2.0. Six European languages. Not trained on Indian IDs.
- `nvidia/gliner-PII`: built on `gliner_large-v2.1`. NVIDIA reports strict F1 of 0.87 on its Nemotron-PII benchmark. NVIDIA Open Model License.
- `knowledgator/gliner-pii-base-v1.0`: 60+ predefined PII categories plus custom labels.
- Good to try as a baseline because you pass labels like "aadhaar number" at run time.

### Piiranha (`iiiorg/piiranha-v1-detect-personal-information`)
- Token classifier on `microsoft/mdeberta-v3-base`. 17 PII types, six languages, 256-token context.
- Self-reported: 98.48% precision and 98.27% recall for PII vs non-PII, 99.44% token accuracy.
- The card says the accuracy figure is inflated by class imbalance, because most tokens are not PII. This is a useful point to understand: **do not use token accuracy for PII; use entity-level precision, recall and F1.**
- Licence is cc-by-nc-nd-4.0 (non-commercial, no derivatives) *(verify)*.

### Indian-focused token classifiers (all self-reported, unverified)
- `arunp0/chitragupta-pii-indic`: XLM-RoBERTa-large tagger plus checksum rules; Aadhaar via Verhoeff.
- `plingampally/meridianpii-hi-v1/v2` and `rotalabs/sakshi-pii-in`: token classifiers for Indian PII; both say structured IDs belong in a regex-plus-checksum layer.

## 3. Cloud services

| Service | Notes |
|---|---|
| AWS Comprehend (Detect PII) | 22 universal and 14 country-specific entity types. India: Aadhaar, PAN, NREGA, voter number. English and Spanish only. No custom entity types. Aadhaar format described as 12 digits with a space or hyphen after the 4th and 8th digit |
| Google Cloud Sensitive Data Protection (DLP) | Built-in infoTypes include `INDIA_AADHAAR_INDIVIDUAL` and `INDIA_PAN_INDIVIDUAL` (from a third-party blog; *verify* on Google's infoType reference or via `infoTypes.list`) |
| Azure AI Language PII | India PAN listed; "India Unique Identification Number" is probably Aadhaar (my inference, *verify*). Category support varies by language |
| Private AI, Nightfall and similar | Commercial; Private AI published a benchmark post comparing PII tools. Vendor benchmarks are marketing as much as science |

All of these are paid APIs, and your text leaves your machine. For a privacy tool like Pre-flight that is a design concern, not just a cost one.

## 4. Datasets

| Dataset | Notes |
|---|---|
| `ai4privacy/pii-masking-400k` | About 407k synthetic entries, 17 classes in the base version, token-classification format. **Licence is academic / non-commercial only** *(verify)*. Has little or no Aadhaar/PAN coverage |
| Nemotron-PII (NVIDIA) | 100k synthetic records (50k train / 50k test), 55+ entity types, span-level labels, CC BY 4.0. Released Oct 2025 |
| `abishekcodes/PII-Synthetic` (HF) | Synthetic sentences with BIO tags including AADHAAR, PAN, PHONE_NUMBER, PERSON. Licence and size not confirmed |
| arXiv 2504.12308 data | About 17k semi-synthetic sentences, 16 PII types across India, UK, US. Highlights that no open dataset is diverse across languages and geographies |
| PIIBench (arXiv 2604.15776) | A unified benchmark that merges several sources. Papers note each dataset has its own label vocabulary, so cross-dataset scores need label normalisation |

**Takeaway:** no single public dataset gives realistic Indian ID coverage with a clean licence. Generating your own synthetic data for Aadhaar, PAN, Indian phone numbers and Indian names/addresses (using valid checksums and realistic surrounding text) is likely part of the answer.

## 5. Research worth citing in the interview

- *An Evaluation Study of Hybrid Methods for Multilingual PII Detection* (arXiv 2510.07551, Centific, NeurIPS 2025 workshop). Proposes RECAP: regex rules plus an LLM in a three-phase pipeline across 13 low-resource locales. Claims large weighted-F1 gains over fine-tuned NER and zero-shot LLMs. Hindi F1 went from 0.486 to 0.696. Uses the `nervaluate` evaluation framework.
- *Unmasking the Reality of PII Masking Models* (arXiv 2504.12308). Argues existing PII-masking models have performance gaps.
- *Fine-Tuning Over Architectural Complexity: Broad-Coverage PII Detection on PIIBench with DeBERTa* (arXiv 2605.25816). Fine-tuning a DeBERTa token classifier beats more complex architectures.

## 6. What this means for the assignment (not yet decided)

1. **Why plain 12-digit regex is wrong.** Any 12-digit number (an order ID, a phone number with country code) matches. Real Aadhaar numbers also pass the Verhoeff checksum and do not start with 0 or 1. A model that sees surrounding words ("my Aadhaar is ...") can tell them apart.
2. **Framing.** Treat PII detection as token classification with BIO labels and report **entity-level** precision, recall and F1 (e.g. with `seqeval` or `nervaluate`), not token accuracy.
3. **Baselines to compare against.** Pre-flight's existing regex, Presidio, and one pretrained model (GLiNER or Piiranha). Showing your model against these answers "how did you measure it".
4. **Likely model choice.** A small pretrained transformer (DistilBERT / DeBERTa-v3-small / XLM-R base) fine-tuned for token classification is trainable on a laptop or free GPU in the time available.
5. **Open questions for you** (see the chat message that accompanies this file).

## Sources

- Presidio: https://microsoft.github.io/presidio/analyzer
- GLiNER multi PII: https://huggingface.co/urchade/gliner_multi_pii-v1
- NVIDIA GLiNER-PII: https://huggingface.co/nvidia/gliner-PII
- Knowledgator GLiNER PII: https://huggingface.co/knowledgator/gliner-pii-base-v1.0
- Piiranha: https://huggingface.co/iiiorg/piiranha-v1-detect-personal-information
- ai4privacy 400k: https://huggingface.co/datasets/ai4privacy/pii-masking-400k
- Nemotron-PII blog: https://huggingface.co/blog/nvidia/nemotron-pii
- AWS Comprehend PII: https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html
- AWS India entity types announcement: https://aws.amazon.com/about-aws/whats-new/2022/05/amazon-comprehend-detects-redacts-pll-entity-types-across-us-uk-canada-india
- Google Sensitive Data Protection infoTypes: https://docs.cloud.google.com/sensitive-data-protection/docs/infotypes-reference
- Azure PII entity categories: https://learn.microsoft.com/azure/ai-services/language-service/personally-identifiable-information/concepts/entity-categories
- Hybrid PII study: https://arxiv.org/abs/2510.07551
- PII masking models study: https://arxiv.org/pdf/2504.12308
- PIIBench: https://arxiv.org/pdf/2604.15776
- DeBERTa on PIIBench: https://arxiv.org/pdf/2605.25816
- Indian PII dataset (abishekcodes): https://huggingface.co/datasets/abishekcodes/PII-Synthetic
- Chitragupta (via article): https://pub.towardsai.net/yama-judges-chitragupta-keeps-the-records-open-source-ai-for-indian-languages-b7f8bf3b7576
- Private AI benchmark: https://www.private-ai.com/en/blog/pii-solutions-benchmark
