# Baseline error examples


## synthetic_test: Pre-flight regex (current)

- `Account holder: Fatima Rao  account number: 224209359852901439  Branch: Canara Bank, Noida`
  - MISSED PERSON: `Fatima Rao`
- `ticket 9116254133: user debashish sethi (08875840390) unable to download statement for 2022 2023 2024.`
  - FALSE ALARM PHONE: `9116254133`
  - MISSED PERSON: `debashish sethi`
  - MISSED PHONE: `08875840390`
- `Booking ID 877154749622, seat 23B, departure 3 Dec 2021.`
  - FALSE ALARM AADHAAR: `877154749622`
- `Write a polite email to Nikhil Bhatt asking them to update Aadhar 996123629603 on the HR portal.`
  - MISSED PERSON: `Nikhil Bhatt`
- `Booking ID 2599 9923 5827, seat 23B, departure 27 Nov 2023.`
  - FALSE ALARM AADHAAR: `2599 9923 5827`
- `Write a polite email to L. Modi asking them to update Aadhaar 3143 4923 0166 on the HR portal.`
  - MISSED PERSON: `L. Modi`
- `Vendor: Greenfield Agro | GST Reg. No.: 35APJHF1053A1Z3 | pan card: XWJPP2433Z | Contact: Faizan Patel`
  - MISSED PERSON: `Faizan Patel`
- `Part number TNMP0518190 must be replaced every year`
  - FALSE ALARM IFSC: `TNMP0518190`
- `Vendor: Acme Corp | gstin: 14ESXCF7021J9ZY | PAN no.: BYXAN0466O | Contact: Ananya Swati Nair`
  - MISSED PERSON: `Ananya Swati Nair`
- `Vendor: Vistara Foods | GSTIN: 33WJFHC1389N2ZX | pan card: IAXHH9450D | Contact: S. Hegde`
  - MISSED PERSON: `S. Hegde`
- `Faizan Naidu +91-9774127957`
  - MISSED PERSON: `Faizan Naidu`
- `Ticket 8663922494: user Rohan (9274007635) unable to download statement for 2026-2027-2028.`
  - FALSE ALARM PHONE: `8663922494`
  - MISSED PERSON: `Rohan`

## synthetic_test: Regex + checksum

- `Account holder: Fatima Rao  account number: 224209359852901439  Branch: Canara Bank, Noida`
  - MISSED PERSON: `Fatima Rao`
- `ticket 9116254133: user debashish sethi (08875840390) unable to download statement for 2022 2023 2024.`
  - FALSE ALARM PHONE: `9116254133`
  - MISSED PERSON: `debashish sethi`
  - MISSED PHONE: `08875840390`
- `Write a polite email to Nikhil Bhatt asking them to update Aadhar 996123629603 on the HR portal.`
  - MISSED PERSON: `Nikhil Bhatt`
- `Write a polite email to L. Modi asking them to update Aadhaar 3143 4923 0166 on the HR portal.`
  - MISSED PERSON: `L. Modi`
- `Vendor: Greenfield Agro | GST Reg. No.: 35APJHF1053A1Z3 | pan card: XWJPP2433Z | Contact: Faizan Patel`
  - MISSED PERSON: `Faizan Patel`
- `Part number TNMP0518190 must be replaced every year`
  - FALSE ALARM IFSC: `TNMP0518190`
- `Vendor: Acme Corp | gstin: 14ESXCF7021J9ZY | PAN no.: BYXAN0466O | Contact: Ananya Swati Nair`
  - MISSED PERSON: `Ananya Swati Nair`
- `Vendor: Vistara Foods | GSTIN: 33WJFHC1389N2ZX | pan card: IAXHH9450D | Contact: S. Hegde`
  - MISSED PERSON: `S. Hegde`
- `Faizan Naidu +91-9774127957`
  - MISSED PERSON: `Faizan Naidu`
- `Ticket 8663922494: user Rohan (9274007635) unable to download statement for 2026-2027-2028.`
  - FALSE ALARM PHONE: `8663922494`
  - MISSED PERSON: `Rohan`
- `part number rnlz0540235 must be replaced every year.`
  - FALSE ALARM IFSC: `rnlz0540235`
- `{"user": "debashishdesai@techsolutions.co.in", "account": "25288027049546", "ifsc": "cbin0253208"}`
  - MISSED BANK_ACCOUNT: `25288027049546`

## handwritten_test: Pre-flight regex (current)

- `Can you write a formal letter to the bank? My name is Nivedita Raghunathan and my account number is 50100234789012.`
  - MISSED PERSON: `Nivedita Raghunathan`
  - MISSED BANK_ACCOUNT: `50100234789012`
- `Rewrite this professionally: "Hi, I'm Tenzin Dorje, my Aadhaar is 3588 1399 8697, please process my claim."`
  - MISSED PERSON: `Tenzin Dorje`
- `Summarise the attached complaint from Farhan Siddiqui (farhan.siddiqui@gmail.com) about a late delivery.`
  - MISSED PERSON: `Farhan Siddiqui`
- `I need a rental agreement draft. Tenant: Lalremruati Hmar, PAN BQXPH4421K. Landlord: Om Prakash Chaurasia.`
  - MISSED PERSON: `Lalremruati Hmar`
  - MISSED PERSON: `Om Prakash Chaurasia`
- `Help me reply to Chitra Venugopal, she asked whether her PAN AKZPV7719R is linked with Aadhaar.`
  - MISSED PERSON: `Chitra Venugopal`
- `Draft an offer letter for Zubin Irani, joining on 3 March, CTC 18 LPA.`
  - MISSED PERSON: `Zubin Irani`
- `Create an Excel formula to split full names like Ojas Kelkar into first and last name columns.`
  - MISSED PERSON: `Ojas Kelkar`
- `Our client Baldev Rana wants a refund to account 31028876540, IFSC PUNB0244200. Write the request mail.`
  - MISSED PERSON: `Baldev Rana`
- `Make a short bio for Dr. Anushree Bhattacharya, cardiologist in Kolkata.`
  - MISSED PERSON: `Anushree Bhattacharya`
- `Write a WhatsApp reminder to Hrithik Bhardwaj that his EMI of Rs 12,450 is due on the 5th.`
  - MISSED PERSON: `Hrithik Bhardwaj`
- `Convert this to JSON: name Sowmya Ranganathan, aadhaar 997309114173, city Mysuru`
  - MISSED PERSON: `Sowmya Ranganathan`
- `My grandmother Kamala Devi can't remember her Aadhaar 2753 6455 6810, how do we download e-Aadhaar?`
  - MISSED PERSON: `Kamala Devi`

## handwritten_test: Regex + checksum

- `Can you write a formal letter to the bank? My name is Nivedita Raghunathan and my account number is 50100234789012.`
  - MISSED PERSON: `Nivedita Raghunathan`
  - MISSED BANK_ACCOUNT: `50100234789012`
- `Rewrite this professionally: "Hi, I'm Tenzin Dorje, my Aadhaar is 3588 1399 8697, please process my claim."`
  - MISSED PERSON: `Tenzin Dorje`
- `Summarise the attached complaint from Farhan Siddiqui (farhan.siddiqui@gmail.com) about a late delivery.`
  - MISSED PERSON: `Farhan Siddiqui`
- `I need a rental agreement draft. Tenant: Lalremruati Hmar, PAN BQXPH4421K. Landlord: Om Prakash Chaurasia.`
  - MISSED PERSON: `Lalremruati Hmar`
  - MISSED PERSON: `Om Prakash Chaurasia`
- `Help me reply to Chitra Venugopal, she asked whether her PAN AKZPV7719R is linked with Aadhaar.`
  - MISSED PERSON: `Chitra Venugopal`
- `Draft an offer letter for Zubin Irani, joining on 3 March, CTC 18 LPA.`
  - MISSED PERSON: `Zubin Irani`
- `Create an Excel formula to split full names like Ojas Kelkar into first and last name columns.`
  - MISSED PERSON: `Ojas Kelkar`
- `Our client Baldev Rana wants a refund to account 31028876540, IFSC PUNB0244200. Write the request mail.`
  - MISSED PERSON: `Baldev Rana`
- `Make a short bio for Dr. Anushree Bhattacharya, cardiologist in Kolkata.`
  - MISSED PERSON: `Anushree Bhattacharya`
- `Write a WhatsApp reminder to Hrithik Bhardwaj that his EMI of Rs 12,450 is due on the 5th.`
  - MISSED PERSON: `Hrithik Bhardwaj`
- `Convert this to JSON: name Sowmya Ranganathan, aadhaar 997309114173, city Mysuru`
  - MISSED PERSON: `Sowmya Ranganathan`
- `My grandmother Kamala Devi can't remember her Aadhaar 2753 6455 6810, how do we download e-Aadhaar?`
  - MISSED PERSON: `Kamala Devi`
