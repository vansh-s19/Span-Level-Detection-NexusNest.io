# DistilBERT errors


## synthetic_test

- `Write a polite email to Prakash Dutta asking them to update UID 7343-0438-3741 on the HR portal.`
  - MISSED AADHAAR: `7343-0438-3741`
- `19/08/2021 - payment TXN418217092829 - Rajesh Subramanian - bank account 11777893217915 - INR 92,786`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `TXN418217092829`
- `Arindam George 6141697365`
  - FALSE ALARM / WRONG PERSON: `Arinda`
  - MISSED PERSON: `Arindam George`
- `2024-04-28 - payment 679030060645 - Rashmi Mehta - a/c 92972976921 - Rs. 17,86,787`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `679030060645`
- `ERROR login failed for shalinibose@outlook.com from Kochi at 23/01/2021`
  - FALSE ALARM / WRONG PERSON: `Kochi`
- `22 Aug 2025 - payment UTR883236914935 - Rekha Iyengar - Acc No 4047466106726827 - Rs. 17,93,403`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `883236914935`
- `Write a polite email to Varun Pandey asking them to update UID 7594 0138 3416 on the HR portal.`
  - MISSED AADHAAR: `7594 0138 3416`
- `23/02/2022 - payment 596035186507 - Arun Singh - Acc No 60956908281 - ₹26,66,692`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `596035186507`
- `Write a polite email to S. Nair asking them to update UID 4235 7676 4055 on the HR portal.`
  - MISSED AADHAAR: `4235 7676 4055`
- `24 Apr 2020 - payment TXN431576408381 - K. Malhotra - account number 175140855609935727 - ₹81,88,848`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `TXN431576408381`
- `20/06/2024 - payment TXN691431284595 - Harpreet Yadav - account number 645353389542139790 - Rs. 30,72,260`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `TXN691431284595`
- `2026-02-01 - payment UTR182725274717 - Vivaan Mishra - bank account 4957881070910907 - 69,31,519 rupees`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `182725274717`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `4957881070910907 - 69`
  - MISSED BANK_ACCOUNT: `4957881070910907`
- `2021-09-15 - payment TXN979612161849 - R. Kumar - a/c 390488652175316 - 3,75,711 rupees`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `79612161849`
- `4 Mar 2021 - payment UTR541666797841 - Sanjay Rao - A/c no 890370275643335643 - ₹85,04,277`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `541666797841`
- `Write a polite email to Kavitha Ghosh asking them to update UID 9731-9988-5690 on the HR portal.`
  - MISSED AADHAAR: `9731-9988-5690`
- `7 May 2023 - payment TXN884502046134 - Rekha Kaul - Acc No 785949378014 - 64,37,517 rupees`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `TX`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `884502046134`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `785949378014 - 64`
  - MISSED BANK_ACCOUNT: `785949378014`
- `24/05/2020 - payment UTR306702612036 - Balaji Thakur - A/c no 858810053046 - ₹54,55,796`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `6702612036`
- `PRANAV GOWDA 75639-25491`
  - MISSED PERSON: `PRANAV GOWDA`
  - MISSED PHONE: `75639-25491`
- `Karthik Patel 62930 66129`
  - MISSED PHONE: `62930 66129`
- `Tushar 6028982601`
  - MISSED PERSON: `Tushar`
  - MISSED PHONE: `6028982601`
- `{"user": "rfernandes@outlook.com", "account": "94057214250643", "ifsc": "IDIB0139456"}`
  - FALSE ALARM / WRONG IFSC: `IDIB`
  - FALSE ALARM / WRONG IFSC: `39456`
  - MISSED IFSC: `IDIB0139456`
- `16/01/2024 - payment TXN367018356586 - Jaspreet Vivaan Mathew - Account No. 7596315247316707 - ₹32,14,768`
  - FALSE ALARM / WRONG BANK_ACCOUNT: `367018356586`
- `pfa scanned copy of aadhaar card of saanvi ghosh - 5855 4227 4973`
  - FALSE ALARM / WRONG PERSON: `saanvi`
  - FALSE ALARM / WRONG PERSON: `hosh`
  - MISSED PERSON: `saanvi ghosh`
- `thomas lalitha chatterjee 95403 61165`
  - FALSE ALARM / WRONG PERSON: `thomas`
  - FALSE ALARM / WRONG PERSON: `lit`
  - MISSED PERSON: `thomas lalitha chatterjee`
- `Shalini Fernandes 95898-24670`
  - MISSED PHONE: `95898-24670`

(25 sentences with at least one error shown)


## handwritten_test

- `I need a rental agreement draft. Tenant: Lalremruati Hmar, PAN BQXPH4421K. Landlord: Om Prakash Chaurasia.`
  - FALSE ALARM / WRONG PERSON: `O`
  - FALSE ALARM / WRONG PERSON: `Prakash Chaurasia`
  - MISSED PERSON: `Om Prakash Chaurasia`
- `Can you explain PAN structure using this example: AAACR5055K?`
  - MISSED PAN: `AAACR5055K`
- `Can someone call Mrs. D'Costa back on 9821054673? She called about the warranty.`
  - FALSE ALARM / WRONG PERSON: `. D'Costa`
  - MISSED PERSON: `D'Costa`
- `Vikrant, the courier tracking number is 463884985568, it should reach by Monday.`
  - FALSE ALARM / WRONG PHONE: `463884985568`
- `Supplier: Kaveri Agro Foods | GSTIN: 29IERFH5436E9ZE | Contact: Ponnusamy 94431 66002`
  - MISSED PERSON: `Ponnusamy`
- `logger.info(f"Created account {acct_id} for {user_name}")  # no PII here, only variables`
  - FALSE ALARM / WRONG EMAIL: `.info`
- `{"order":"205948201833","sku":"KXMTR4471P","qty":2}`
  - FALSE ALARM / WRONG PHONE: `205948201833`
  - FALSE ALARM / WRONG PAN: `KXMTR4471P`
- `email_regex = r"[^@]+@[^@]+\.[^@]+"  # used to validate someone@example.com-style input`
  - FALSE ALARM / WRONG EMAIL: `rege`
- `mera pan card FKTPS4590E hai, ITR file karna hai help karo`
  - FALSE ALARM / WRONG PERSON: `karo`
- `paisa 20014587903 me bhej do, ifsc BARB0VJAMSH`
  - MISSED BANK_ACCOUNT: `20014587903`
- `sir mera email rohitkr.1999@gmail.com pe bhej dijiye`
  - FALSE ALARM / WRONG PERSON: `mera`
  - FALSE ALARM / WRONG PERSON: `hej dijiye`
- `yaar Golu ne order 956378276082 cancel kar diya`
  - FALSE ALARM / WRONG PERSON: `Go`
  - FALSE ALARM / WRONG PERSON: `r diya`
  - MISSED PERSON: `Golu`
- `aadhaar no 6571 7847 2673 wala card kho gaya, kya karu`
  - FALSE ALARM / WRONG PERSON: `gaya`
- `Sunaina didi ka pan CQUPS8812H aur mobile 9599304821`
  - FALSE ALARM / WRONG PERSON: `Sunaina didi`
  - MISSED PERSON: `Sunaina`
- `ok Aman bhai done`
  - FALSE ALARM / WRONG PERSON: `Aman bhai done`
  - MISSED PERSON: `Aman`
- `kal Mishra ji ko 50k transfer karna hai`
  - MISSED PERSON: `Mishra`
- `Call 9810022334 for delivery, not the ticket number 9810022335 printed on the slip.`
  - MISSED PHONE: `9810022334`
- `Deepa and Joseph Kurian co-own account 67203348891 at FDRL0001234.`
  - MISSED IFSC: `FDRL0001234`

(18 sentences with at least one error shown)

