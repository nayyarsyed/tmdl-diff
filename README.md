<div align="center">
  <svg width="650" height="220" viewBox="0 0 650 220" xmlns="http://www.w3.org/2000/svg">
    <!-- Background -->
    <rect width="650" height="220" fill="#000000" rx="8"/>
    
    <!-- Gold Gradient -->
    <defs>
      <linearGradient id="retroGold" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:#FFD700;stop-opacity:1" />
        <stop offset="50%" style="stop-color:#B8860B;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#8B6508;stop-opacity:1" />
      </linearGradient>
    </defs>

    <!-- Perfectly Aligned ASCII Art -->
    <text x="50%" y="45" font-family="monospace" font-size="10" fill="url(#retroGold)" text-anchor="middle">
      <tspan x="50%" dy="0"> ████████╗███╗   ███╗██████╗ ██╗         ██████╗ ██╗███████╗███████╗</tspan>
      <tspan x="50%" dy="1.2em"> ╚══██╔══╝████╗ ████║██╔══██╗██║         ██╔══██╗██║██╔════╝██╔════╝</tspan>
      <tspan x="50%" dy="1.2em">    ██║   ██╔████╔██║██║  ██║██║         ██║  ██║██║█████╗  █████╗  </tspan>
      <tspan x="50%" dy="1.2em">    ██║   ██║╚██╔╝██║██║  ██║██║         ██║  ██║██║██╔══╝  ██╔══╝  </tspan>
      <tspan x="50%" dy="1.2em">    ██║   ██║ ╚═╝ ██║██████╔╝███████╗    ██████╔╝██║██║     ██║     </tspan>
      <tspan x="50%" dy="1.2em">    ╚═╝   ╚═╝     ╚═╝╚═════╝ ╚══════╝    ╚═════╝ ╚═╝╚═╝     ╚═╝     </tspan>
    </text>

    <!-- Divider -->
    <rect x="25" y="160" width="600" height="4" fill="url(#retroGold)" rx="2"/>
    
    <!-- Subtitle -->
    <text x="50%" y="195" font-family="Courier New, monospace" font-size="16" font-weight="bold" fill="#B8860B" text-anchor="middle" letter-spacing="3">
      [ SEMANTIC POWER BI DIFF TOOL ]
    </text>
  </svg>
</div>

# 🚀 TMDL Diff CLI

**Stop hunting for broken visuals. Start comparing.**

`tmdl-diff` is a high-level semantic comparison tool for Power BI developers. It compares TMDL (Tabular Model Definition Language) and PBIP (Power BI Project) files to instantly identify structural changes that break reports.

## ✨ Key Value
- **Visual Integrity**: Quickly see if a structural change (like a rename) will impact your report visuals.
- **Semantic Diff**: Goes beyond text comparison to understand Tables, Measures, and Columns.
- **CLI Speed**: No need to open heavy PBIX files just to see what's different between versions.
- **Live Detection**: Identify and inspect open Power BI Desktop instances on your machine.

## 📦 Installation

```bash
pip install tmdl-diff
```

## 🚀 Quick Usage

### 1. Compare two Project Files (.pbip)
```bash
tmdl-diff diff version1.pbip version2.pbip
```

### 2. List Open Instances & Files
```bash
tmdl-diff list
```

### 3. Interactive Comparison
```bash
tmdl-diff compare
```

## 📄 License
MIT
