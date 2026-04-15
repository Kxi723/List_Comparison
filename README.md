# 📦 SFTP Reconciler

> An automated Python toolkit designed to reconcile expected shipment documents from CSV report against actual files uploaded to SFTP server. Built to ensure zero missed uploads and eliminate tedious manual checks.

## 📖 Background & Problem Statement

During my internship, a service issue caused the **DocuShare** and **SFTP server** stop syncing properly. As an intern, I had to manually cross-check the daily document uploads to SFTP. 

The manual process was time-consuming and prone to human error. So I developed this automation script to reliably identify **missing documents** that haven't been uploaded, as well as documents uploaded **in advance**.

## ⚙️ How It Works (The Logic)

The reconciliation process is split into two main scripts:

### 1. `csv_extractor.py` - Identifying Expected Documents
Receives a CSV containing shipment data. The crucial columns are `Ship Ref` (the document's filename) and `POD`.
- **The Process:** The script reads the directory containing the CSV files and specifically picks the **two most recent files**. 
- **60-Day Lookback:** It filters for data within the last 60 days. *Why 60 days?* My supervisor advised that some PODs might unpredictably update or appear for older dates. Comparing 60 days covers edge cases securely without sacrificing performance.
- **Diffing:** It compares the two CSVs to extract strictly the **newly added** `Ship Ref`s (data present in the newest CSV but not the older one). 
- **Output:** Generates a `.txt` file containing these new references for the next script to use.

### 2. `sync_validator.py` - Validating Against SFTP
After running the first script, I manually SSH into our SFTP server to fetch a list of files uploaded in the last 10 days and place it as a text file in the `/sftp/` directory.
- **The Process:** The script compares the **two newest SFTP text files** (to find newly uploaded documents) against the fresh CSV data.
- **Reconciliation:** It consolidates the current state, resolving logic to categorize shipments into two core outputs:
  - ❌ **Missing Documents (In CSV, NOT in SFTP):** Files that were documented but failed to reach from SFTP. These require upload.
  - ⚠️ **Pre-uploads (In SFTP, NOT in CSV):** Files found in SFTP server but missing from the CSV report. These are usually files uploaded early by admins, or cases where the CSV report isn't latest version.
- **Carry-over:** Elegantly handles ongoing sync gaps by tracking and carrying forward previous "missing" or "pre-uploaded" documents across multiple days until they eventually reconcile.

## 🛡️ Safety & Safeguards Built-In

To prevent user mistakes (like running scripts twice sequentially) or misinterpreting data, I designed several defensive safety mechanisms:

- **Timestamp Marking:** Once text files (SFTP or CSV data files) are processed, the script explicitly appends a timestamp (e.g., `_HHMMSS`) to the filename. This serves to "lock" the file, ensuring that the exact same dataset will not be consumed twice inadvertently.
- **Duplicate-Safe Exports:** Avoids creating redundant output reports if there are no new discrepancy changes compared to the last run.
- **Empty State Logging:** Safely generates empty tracking files and logs whenever "no new data is found", leaving a reliable, traceable record of the script's execution.

## 📁 Repository Structure

```text
sftp_reconciler/
├── csv_extractor.py        # 1st Step: Extracts & diffs new Ship Refs from CSV
├── sync_validator.py       # 2nd Step: Compares CSV data vs SFTP log, generates reports
├── config.py               # Shared configuration and logging setup
├── activity.log            # Runtime log for audit and debugging (auto-generated)
├── evisibility_folder/     # Input: CSV exports & script-generated .txt lists
├── sftp/                   # Input: SFTP file listing logs
├── missing/                # Output: Reports of Ship Refs NOT yet in SFTP
└── in_advance/             # Output: Reports of files in SFTP but NOT in CSV
```

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8+
- Required packages:
  ```bash
  pip install pandas python-dotenv
  ```

### Running the Toolkit

**Step 1: Extract new expected shipments**
1. Ensure at least two recent `.csv` files are inside `evisibility_folder/`
2. Run the extractor:
   ```bash
   python csv_extractor.py
   ```
   *This outputs an updated expected list text file in the same folder.*

**Step 2: Compare against SFTP records**
1. Place the fetched SFTP `.txt` listings into the `sftp/` directory.
2. Run the validator:
   ```bash
   python sync_validator.py
   ```
   *This will compile discrepancy reports inside `missing/` and `in_advance/`, output results directly to the terminal, and securely lock the processed files by renaming them with timestamps.*
