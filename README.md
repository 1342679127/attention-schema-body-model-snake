# Attention Schema for Body Ownership

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

This repository contains the official implementation of the paper:

> **The attention schema as a bridge between body ownership and higher-order consciousness**  
> *Authors: Bojie Feng*  
> *[Try Nature Machine Intelligence, 2026]*  

We propose that body ownership and the attention schema share a common higher‑order internal model mechanism. We implement an artificial agent with an internal body‑state model in a Snake environment and show that this model improves body tracking under limited perception, with resource‑efficient properties. The code allows full replication of all experiments, including three agent types (third‑person omniscient, first‑person reactive, and first‑person body‑model) and systematic parameter searches over spatial resolution, update interval, and memory duration.

---

## 📁 Repository Structure
.
├── snake.py # Main body‑model agent (attention‑schema inspired)
├── thirdperspective.py # Third‑person omniscient baseline (full state)
├── firstperspective.py # First‑person reactive baseline (local view only)
├── baseline_stats.py # Generate baseline reports (reactive & omniscient)
├── param_search.py # Parameter search over 57 combinations (30 repeats each)
├── baseline_report.txt # (generated) baseline performance statistics
├── param_search_report.txt # (generated) optimal parameters and top‑5 results
├── requirements.txt # Python dependencies
└── README.md # This file

text

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- `pip` (package installer)

### Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/yourusername/attention-schema-body.git
cd attention-schema-body
pip install -r requirements.txt
🧪 Running the Experiments
1. Run a single agent interactively (with GUI)
To see the agent in action with the visual interface:

bash
python snake.py          # Body‑model agent (adjust parameters at top of file)
python thirdperspective.py   # Omniscient baseline
python firstperspective.py   # Reactive baseline
Use keyboard controls:

R – reset the game (reset statistics)

M – record current step/length (up to 10 entries)

Arrow keys – manual override (for debugging)

2. Generate the baseline statistics
First, generate the baseline data (reactive and omniscient) by running:

bash
python baseline_stats.py
This will run 30 episodes (1000 steps each) for each baseline and produce baseline_report.txt, which contains the mean ± std and raw data.

3. Perform the full parameter search
This will test all 57 valid combinations (RESOLUTION ∈ {1,2,4}, MEMORY_TIMEOUT ∈ {5,10,20,40,80}, UPDATE_INTERVAL ∈ {1,2,5,10,20} with interval < timeout) and produce param_search_report.txt.

bash
python param_search.py
Expected output: a summary of the optimal parameters and a top‑5 ranking, along with statistical comparisons (Welch’s *t*‑test, Cohen’s *d*) against both baselines. The report is saved to param_search_report.txt.

⚙️ Core Parameters (in snake.py)
You can adjust the three key parameters directly in the file:

Variable	Description	Values tested
RESOLUTION	Spatial coarseness of the internal map (1 = cell‑level)	1, 2, 4
UPDATE_INTERVAL	How often (in steps) the map is updated from vision	1, 2, 5, 10, 20
MEMORY_TIMEOUT	Maximum steps without update before a cell is forgotten	5, 10, 20, 40, 80
Important constraint: To have meaningful forgetting, ensure MEMORY_TIMEOUT > UPDATE_INTERVAL (the parameter search only tests valid combinations where interval < timeout).

📊 Results (from the paper)
The table below summarises the main performance comparison (mean ± SD over 30 runs):

Agent	Observation	Internal model	Max body length
Omniscient	Full state	No	78.23 ± 12.29
Reactive	9×9 local view	No	43.67 ± 1.18
Body‑model	9×9 local view	Yes (optimal)	70.60 ± 8.30
Statistical tests:

Body‑model vs Reactive: *t* = 19.16, *p* < 0.001, Cohen's *d* = 3.24

Body‑model vs Omniscient: *t* = −0.64, *p* = 0.5258 (n.s.)

Full parameter‑search results (top‑5 configurations) are provided in param_search_report.txt.

📝 Citation
If you use this code or build upon our work, please cite our paper:

bibtex
@article{yourpaper2025,
  title={The attention schema as a bridge between body ownership and higher-order consciousness},
  author={Your, Names},
  journal={Journal/Conference},
  year={2025},
  doi={...}
}
🤝 Contributing
We welcome issues and pull requests. Please open an issue first to discuss any major changes.
