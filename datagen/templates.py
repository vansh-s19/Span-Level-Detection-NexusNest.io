"""
Sentence templates.

Slot syntax:
  {UPPERCASE}  -> PII, becomes a labelled span (see values.PII_SLOTS)
  {lowercase}  -> unlabelled filler: cues, context, or hard negatives
                  (see values.FILLERS)

POSITIVE templates contain at least one PII slot (many also contain
look-alike negatives, so the model sees PII and non-PII side by side).
NEGATIVE templates contain no PII at all, only look-alikes.

Templates are split between train / validation / test (see generate.py),
so the test set uses sentence patterns the model never trained on.

The styles mimic what Pre-flight actually sees: prompts typed into an AI
chat, pasted e-mails, forms, CSV rows, JSON snippets and support tickets.
"""

POSITIVE_TEMPLATES = [
    # --- prompts to an AI assistant ---
    "Can you draft a KYC reminder for {PERSON}? Her {pan_cue} is {PAN} and {aadhaar_cue} {AADHAAR}.",
    "Write a polite email to {PERSON} asking them to update {aadhaar_cue} {AADHAAR} on the HR portal.",
    "Summarise this: customer {PERSON} ({EMAIL}, {phone_cue} {PHONE}) complained about order {num12}.",
    "Please fix the grammar: my name is {PERSON} and my {aadhaar_cue} is {AADHAAR}",
    "Translate to Hindi - Dear {PERSON}, your {pan_cue} {PAN} has been linked successfully.",
    "help me write a loan application, applicant {PERSON}, {pan_cue} {PAN}, salary {amount} per month",
    "Make a table with these rows: {PERSON}, {PHONE}, {EMAIL}",
    "Generate a rent agreement between {PERSON} and {PERSON2} for a flat in {city}, rent {amount}.",
    "Check if this is a valid IFSC: {IFSC}. The account is {BANK_ACCOUNT} with {bank}.",
    "I am {PERSON}, can you explain why my refund of {amount} for invoice {invoice} is delayed? Reach me at {PHONE}.",
    "Explain GST filing for my firm, {gst_cue} {GSTIN}, turnover around {amount}.",
    "rewrite formally: hi this is {PERSON} my number is {PHONE} call me back",
    "Create a cover letter for {PERSON}, email {EMAIL}, applying to {company} in {city}.",
    "Can you verify these details before I submit: {aadhaar_cue} {AADHAAR}, {pan_cue} {PAN}, {phone_cue} {PHONE}",
    "Fill this form for me. Name: {PERSON}. {acct_cue}: {BANK_ACCOUNT}. {ifsc_cue}: {IFSC}.",
    "Write a WhatsApp message to {PERSON} reminding about the payment of {amount} due on {date}.",
    "Debug this: user {EMAIL} cannot log in after version {version} update",
    "pls summarise the complaint from {PERSON} regarding ticket {num10}, her email is {EMAIL}",
    "Draft a salary slip note for {PERSON} (employee {empid}), credited to {acct_cue} {BANK_ACCOUNT}.",
    "My father {PERSON} wants to open an FD, his {pan_cue} is {PAN}, which bank is best?",

    # --- e-mails / messages ---
    "Hi {PERSON}, please share your {aadhaar_cue} and {pan_cue} for onboarding. Regards, {PERSON2}",
    "Dear Sir, kindly transfer the amount to {acct_cue} {BANK_ACCOUNT}, {ifsc_cue} {IFSC}, {bank} {city} branch.",
    "Hello team, {PERSON} has joined today. Contact: {PHONE}, {EMAIL}.",
    "Please find attached the invoice {invoice} for {qty} units. Our {gst_cue} is {GSTIN}.",
    "{title} {PERSON}, your account {BANK_ACCOUNT} has been credited with {amount} on {date}.",
    "Forwarding the documents of {PERSON}: {aadhaar_cue} {AADHAAR}, {pan_cue} {PAN}.",
    "Thanks {PERSON}! I've noted your new number {PHONE}.",
    "As discussed, the vendor {company} ({gst_cue} {GSTIN}) will deliver {product} by {date}.",
    "Reminder: {PERSON} needs to submit the {pan_cue} copy ({PAN}) before {date}.",
    "Can you reach {PERSON2} on {PHONE}? {PERSON} is on leave till {date}.",
    "PFA scanned copy of aadhaar card of {PERSON} - {AADHAAR}",
    "Payment of {amount} received from {PERSON} via UTR {txn}. Receipt sent to {EMAIL}.",
    "Hi, this is {PERSON} from {company}. You can mail me at {EMAIL} or ping on {PHONE}.",
    "The refund for order {num12} will go to {PERSON}'s {acct_cue} {BANK_ACCOUNT}.",
    "kindly update my mobile no to {PHONE} and email to {EMAIL}, regards {PERSON}",

    # --- forms / key-value records ---
    "Name: {PERSON} | {aadhaar_cue}: {AADHAAR} | DOB: {date} | {phone_cue}: {PHONE}",
    "Applicant: {PERSON}; {pan_cue}: {PAN}; City: {city}; Pincode: {pincode}",
    "Beneficiary Name - {PERSON}, {acct_cue} - {BANK_ACCOUNT}, {ifsc_cue} - {IFSC}",
    "Employee {empid} | {PERSON} | {EMAIL} | {PHONE} | {city}",
    "Vendor: {company} | {gst_cue}: {GSTIN} | {pan_cue}: {PAN} | Contact: {PERSON}",
    "KYC STATUS: PENDING. Customer {PERSON}, {aadhaar_cue} {AADHAAR}, {pan_cue} {PAN}.",
    "Nominee: {PERSON2} (relation: spouse), {phone_cue} {PHONE}",
    "Bill To: {PERSON}, {city} - {pincode}. {gst_cue}: {GSTIN}. Invoice: {invoice}.",
    "{PERSON}, {AADHAAR}, {PAN}, {PHONE}",
    "Customer ID {empid} - {PERSON} - {EMAIL}",
    "Guarantor details: {PERSON2}, {pan_cue} {PAN}, {aadhaar_cue} {AADHAAR}, ph {PHONE}",
    "Account holder: {PERSON}  {acct_cue}: {BANK_ACCOUNT}  Branch: {bank}, {city}",

    # --- CSV / JSON / logs pasted into a prompt ---
    "name,phone,email\n{PERSON},{PHONE},{EMAIL}",
    "id,name,aadhaar,pan\n{qty},{PERSON},{AADHAAR},{PAN}",
    '{{"name": "{PERSON}", "pan": "{PAN}", "mobile": "{PHONE}"}}',
    '{{"user": "{EMAIL}", "account": "{BANK_ACCOUNT}", "ifsc": "{IFSC}"}}',
    "ERROR login failed for {EMAIL} from {city} at {date}",
    "INSERT INTO customers VALUES ('{PERSON}', '{PHONE}', '{AADHAAR}');",
    "{date} - payment {txn} - {PERSON} - {acct_cue} {BANK_ACCOUNT} - {amount}",
    "gstin={GSTIN}&invoice={invoice}&amount={amount}",

    # --- HR / finance / support notes ---
    "Payroll update: {PERSON} bank changed to {bank}, {acct_cue} {BANK_ACCOUNT}, {ifsc_cue} {IFSC}.",
    "Background verification for {PERSON} completed. {pan_cue} {PAN} verified, {aadhaar_cue} {AADHAAR} verified.",
    "Ticket {num10}: user {PERSON} ({PHONE}) unable to download statement for {years}.",
    "Interview scheduled with {PERSON} on {date}. Candidate email: {EMAIL}.",
    "Loan file of {PERSON}: {pan_cue} {PAN}, CIBIL pending, {phone_cue} {PHONE}.",
    "The supplier's {gst_cue} {GSTIN} does not match the PAN {PAN} on the invoice.",
    "Claim raised by {PERSON} for {amount}; reimburse to {acct_cue} {BANK_ACCOUNT}.",
    "Delivery partner {PERSON} ({PHONE}) will pick up AWB {num10} today.",
    "For TDS, we need {PERSON}'s {pan_cue}: {PAN}",
    "{PERSON} reported that the OTP {otp} was not received on {PHONE}.",
    "Batch {sku} dispatched to {PERSON}, {city}. Contact {PHONE}.",

    # --- informal / noisy ---
    "my aadhar is {AADHAAR} pls check",
    "pan {PAN} name {PERSON}",
    "call {PERSON} on {PHONE} asap",
    "send it to {EMAIL} thx",
    "acc no {BANK_ACCOUNT} ifsc {IFSC} name {PERSON}",
    "bro my number changed, new one is {PHONE}",
    "{PERSON} ka aadhaar {AADHAAR} hai, verify kar do",
    "uska pan card number {PAN} hai aur mobile {PHONE}",
    "plz share gst {GSTIN} wala invoice {invoice}",
    "mail me at {EMAIL} or whatsapp {PHONE}",
    "Aadhaar {AADHAAR} and order {num12} are both 12 digits, which one is the Aadhaar?",
    "{PERSON} {PHONE}",
    "ok so {PERSON2} said {PERSON} will pay {amount} by {date}",
    "his pan is {PAN} not {sku}, the second one is the product code",
    "transfer done to {BANK_ACCOUNT} ({bank}), ref {txn}",
    "UID {AADHAAR} linked with mobile {PHONE}",
    "need help, {PERSON} lost the aadhaar card ({AADHAAR}), how to reprint?",
    "is {IFSC} the ifsc for {bank} {city}?",
    "pls verify gstin {GSTIN} for {company}",
    "Email from {EMAIL}: invoice {invoice} still unpaid",
    "{PERSON} from {city} called about refund {txn}",
    "{title} {PERSON} and {title} {PERSON2} attended the meeting on {date}.",
    "Assign the ticket to {PERSON}.",
    "Who is {PERSON}? Their email {EMAIL} keeps bouncing.",
    "Account {BANK_ACCOUNT} was debited {amount} on {date} for policy {longnum}.",
]

NEGATIVE_TEMPLATES = [
    # 12-digit look-alikes (Aadhaar-shaped)
    "Your order {num12} has been shipped and will arrive by {date}.",
    "Invoice number {num12} for {amount} is due on {date}.",
    "Reference no. {num12} - please quote this in all communication.",
    "Tracking ID {num12}: package left the {city} hub.",
    "The barcode on the box reads {num12}.",
    "Policy number {num12} renewed for {years}.",
    "Transaction {txn} of {amount} was successful.",
    "Consignment {longnum} is out for delivery in {city}.",
    "Order {num12} and order {num12} were merged into one shipment.",
    "Booking ID {num12}, seat 23B, departure {date}.",
    # 10-digit look-alikes (phone-shaped)
    "Ticket {num10} has been escalated to L2 support.",
    "AWB {num10} is held at customs in {city}.",
    "Complaint {num10} resolved on {date}.",
    "Use coupon batch {num10} for the {product} offer.",
    "PNR {num10} is confirmed for {date}.",
    "Serial number {num10} is printed under the {product}.",
    # PAN / IFSC-shaped codes
    "SKU {sku} is out of stock; reorder {qty} units of {product}.",
    "Model {sku} {product} costs {amount}.",
    "Batch code {sku} failed the quality check.",
    "Part number {itemcode} must be replaced every year.",
    "Item code {itemcode} and {sku} are listed in the catalogue.",
    "Licence key prefix {sku} applies to version {version}.",
    # years, dates, amounts, versions
    "Budget plan {years} has been approved.",
    "Compare revenue for {years} across all regions.",
    "Sales grew by 12% between {date} and {date}.",
    "The meeting is on {date} at the {city} office.",
    "Total payable: {amount} including GST.",
    "Upgrade to version {version} before {date}.",
    "Our {city} office pincode is {pincode}.",
    "The OTP is valid for 10 minutes. Do not share it.",
    "Employee {empid} has completed onboarding training.",
    "PO {invoice} for {qty} {product} was approved.",
    # generic business / AI prompts with no PII
    "Write a product description for {product} priced at {amount}.",
    "Explain how Aadhaar based e-KYC works in simple words.",
    "What is the format of a PAN card number?",
    "How do I find the IFSC code of my bank branch?",
    "Summarise the Q3 report for {company}; revenue was {amount}.",
    "Draft an email announcing the new {city} office opening on {date}.",
    "What documents are needed for a GST registration?",
    "Generate 5 tagline ideas for {company}.",
    "Convert {amount} to US dollars.",
    "List the steps to link a mobile number with a bank account.",
    "The account team in {city} will share the report by {date}.",
    "Please call the customer care number on the website for help.",
    "My phone is not charging, what should I do?",
    "Email the finance team about invoice {invoice}.",
    "order {num12} not delivered yet pls check",
    "ref {longnum} payment failed retry",
]
