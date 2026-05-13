"""
setup_repo.py
─────────────
Run this script once on your local machine to create the full
retail-inventory-risk-profiling repository structure automatically.

Usage:
    python setup_repo.py
"""

import os

# ── Folder structure ──────────────────────────────────────────────────────────
FOLDERS = [
    "data",
    "notebooks",
    "scripts",
    "outputs/charts",
]

# ── Placeholder files ─────────────────────────────────────────────────────────
# These are empty stubs so git tracks the folders and the repo is immediately runnable.
PLACEHOLDER_FILES = {
    "data/.gitkeep":           "",
    "outputs/.gitkeep":        "",
    "outputs/charts/.gitkeep": "",
}

# ── .gitignore ────────────────────────────────────────────────────────────────
GITIGNORE = """\
# Data files (download manually from Kaggle)
data/*.xlsx
data/*.csv

# Python
__pycache__/
*.py[cod]
*.egg-info/
.env
venv/
.venv/

# Jupyter
.ipynb_checkpoints/

# OS
.DS_Store
Thumbs.db
"""

def create_structure():
    base = os.path.dirname(os.path.abspath(__file__))

    print("Creating folder structure...")
    for folder in FOLDERS:
        path = os.path.join(base, folder)
        os.makedirs(path, exist_ok=True)
        print(f"  ✓ {folder}/")

    print("\nCreating placeholder files...")
    for filepath, content in PLACEHOLDER_FILES.items():
        full_path = os.path.join(base, filepath)
        with open(full_path, "w") as f:
            f.write(content)
        print(f"  ✓ {filepath}")

    gitignore_path = os.path.join(base, ".gitignore")
    with open(gitignore_path, "w") as f:
        f.write(GITIGNORE)
    print("  ✓ .gitignore")

    print("\n✅ Repository structure ready.")
    print("\nNext steps:")
    print("  1. Download online_retail_II.xlsx from Kaggle → place in data/")
    print("  2. pip install -r requirements.txt")
    print("  3. Run notebooks/stockout_overstock_risk_profiling.ipynb")
    print("     OR: cd scripts && python analysis.py")

if __name__ == "__main__":
    create_structure()
