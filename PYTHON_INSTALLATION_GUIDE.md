# Python Installation Guide for Windows

## Step-by-Step Installation Instructions

### Step 1: Download Python
1. Open your web browser and go to: **https://www.python.org/downloads/**
2. Click the yellow **"Download Python 3.x.x"** button (it will show the latest version)
3. The installer file (e.g., `python-3.12.x-amd64.exe`) will download to your Downloads folder

### Step 2: Run the Installer
1. Navigate to your **Downloads** folder
2. Double-click the `python-3.x.x-amd64.exe` file
3. **IMPORTANT**: On the first screen, check these boxes:
   - ✅ **"Add python.exe to PATH"** (THIS IS CRITICAL!)
   - ✅ "Install launcher for all users" (optional but recommended)
4. Click **"Install Now"** (recommended for most users)
   - This will install Python to: `C:\Users\matth\AppData\Local\Programs\Python\Python3xx\`

### Step 3: Wait for Installation
- The installation will take 2-5 minutes
- You'll see a progress bar
- When complete, you'll see "Setup was successful"

### Step 4: Verify Installation
1. Open a **NEW** Command Prompt or PowerShell window:
   - Press `Win + R`
   - Type `cmd` and press Enter
2. Type: `python --version`
3. You should see: `Python 3.x.x`

### Step 5: Install Required Package
In the same Command Prompt/PowerShell window, type:
```bash
pip install requests
```

This installs the `requests` library needed for the manufacturer extraction script.

### Step 6: Run the Manufacturer Extraction Script
1. Navigate to the project directory:
   ```bash
   cd C:\Users\matth\OneDrive\Documents\PhD\SMASH-BIO
   ```

2. Run the script:
   ```bash
   python extract_ot_manufacturers_from_pmc.py
   ```

3. The script will:
   - Process all publications in the NBIB file
   - Download full-text articles from PubMed Central
   - Extract manufacturer information
   - Create `ot_manufacturers_results.csv` with the results

## Troubleshooting

### Problem: "python is not recognized"
**Solution**: You forgot to check "Add python.exe to PATH" during installation.
- Uninstall Python (Settings > Apps > Python)
- Reinstall and make sure to check the PATH box

### Problem: "pip is not recognized"
**Solution**: 
```bash
python -m pip install requests
```

### Problem: Script can't find the NBIB file
**Solution**: The script looks for the file at:
```
C:\Users\matth\Downloads\pubmed-opticaltwe-set_experimental_bio (1).nbib
```
Make sure the file is in your Downloads folder with this exact name.

## Alternative: Quick Test
To verify Python is working, create a simple test:
1. Open Command Prompt
2. Type: `python`
3. You should see `>>>` prompt
4. Type: `print("Hello, Python!")`
5. Type: `exit()` to quit

## What Happens Next?
Once Python is installed and you run the script:
- It will take approximately 20-30 minutes to process all publications
- You'll see progress updates for each article
- The final CSV file will contain manufacturer information for all experimental studies
- Open the CSV in Excel to view the results

## Need Help?
If you encounter any issues:
1. Make sure you opened a NEW terminal window after installation
2. Verify Python is in PATH: `python --version`
3. Check the error message carefully
4. The script includes detailed error messages to help diagnose issues
