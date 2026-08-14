"""
Replace mojibake (broken emoji/Unicode) with clean ASCII equivalents.
Run once to clean all .py and .html files in the project.
"""
import os
import re

# Map of mojibake -> clean replacement
REPLACEMENTS = [
    ("",  ""),       # ✅
    ("",  ""),
    ("", ""),      # ⚠️
    ("",  ""),
    ("",   ""),
    ("-",  "-"),      # •  bullet
    ("š\"", ""),      # ⚔️
    ("", ""),        # emoji prefix
    ("",  ""),
    ("",   ""),
    ("",   ""),
    ("",  ""),       # replacement char
    ("€",  ""),
    ("",   ""),
    ("\u00e2\u009c\u0085", ""),   # UTF-8 ✅ as latin1
    ("\u00e2\u009a\u00a0\u00ef\u00b8\u008f", ""),  # ⚠️
]

TARGET_DIRS = [
    r"d:\STUDYVERSE_FINAL\PROJECT D2",
]
EXTENSIONS = [".py", ".html", ".js"]

def clean_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            original = f.read()
    except Exception as e:
        print(f"  SKIP (read error): {filepath}: {e}")
        return False

    cleaned = original
    for bad, good in REPLACEMENTS:
        cleaned = cleaned.replace(bad, good)

    # Also remove any remaining non-ASCII from print() and flash() strings
    # by stripping standalone mojibake sequences
    # Remove sequences of // followed by non-space non-printable chars
    cleaned = re.sub(r'[][^\x00-\x7F\s]*', '', cleaned)

    if cleaned != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cleaned)
        print(f"  CLEANED: {os.path.basename(filepath)}")
        return True
    return False

total_files = 0
total_cleaned = 0

for base_dir in TARGET_DIRS:
    for root, dirs, files in os.walk(base_dir):
        # Skip hidden dirs, git, pycache, node_modules
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'backups', 'instance'}]
        for fname in files:
            if any(fname.endswith(ext) for ext in EXTENSIONS):
                filepath = os.path.join(root, fname)
                total_files += 1
                if clean_file(filepath):
                    total_cleaned += 1

print(f"\nDone! Cleaned {total_cleaned} / {total_files} files.")
