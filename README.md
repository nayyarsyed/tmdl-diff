# 🚀 TMDL Diff CLI

**Stop hunting for broken visuals. Start comparing.**

`tmdl-diff` is a high-level semantic comparison tool for Power BI developers. It compares TMDL (Tabular Model Definition Language) and PBIP (Power BI Project) files to instantly identify structural changes that break reports.

Whether you renamed a measure, changed a table structure, or modified a calculation, this tool saves hours of manual checking by showing you exactly what changed at the CLI level.

## ✨ Key Value
- **Visual Integrity**: Quickly see if a structural change (like a rename) will impact your report visuals.
- **Semantic Diff**: Goes beyond text comparison to understand Tables, Measures, and Columns.
- **CLI Speed**: No need to open heavy PBIX files just to see what's different between versions.
- **Live Detection**: Identify and inspect open Power BI Desktop instances on your machine.

## 📦 Installation

Install directly from PyPI (once published):
```bash
pip install tmdl-diff
```

Or install locally for development:
```bash
git clone https://github.com/your-username/tmdl-diff.git
cd tmdl-diff
pip install -e .
```

## 🚀 Quick Usage

### 1. Compare two Project Files (.pbip)
The most common way to compare two versions of a model:
```bash
tmdl-diff diff version1.pbip version2.pbip
```

### 2. List Open Instances & Files
See what Power BI models are currently running or available in your folder:
```bash
tmdl-diff list
```

### 3. Interactive Comparison
Don't remember the filenames? Use the interactive picker:
```bash
tmdl-diff compare
```

### 4. Direct TMDL Comparison
Compare raw `.tmdl` files exported from Tabular Editor or Power BI:
```bash
tmdl-diff diff table1.tmdl table2.tmdl
```

## 🛠️ How it works
1. **PBIP Parsing**: Recursively scans `.SemanticModel` folders for TMDL definitions.
2. **Semantic Analysis**: Groups changes by Table, Measure, and Relationship.
3. **Smart Formatting**: Provides a color-coded, high-level summary of additions, deletions, and modifications.

## 📄 License
MIT
