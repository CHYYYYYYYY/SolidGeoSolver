# FGPS - FormalGeo Problem Solver

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

FGPS (FormalGeo Problem Solver) is an automated geometric problem-solving system based on the FormalGeo framework. It formally represents geometric problems and automatically solves them using various search strategies. The project also integrates AI models for generating Condition Description Language (CDL).

## ✨ Key Features

- 🔍 **Multiple Search Strategies**: Supports both Forward Search and Backward Search.
- 🎯 **Diverse Search Algorithms**: Includes Breadth-First Search (BFS), Depth-First Search (DFS), Random Search (RS), and Beam Search (BS).
- 📊 **FormalGeo7k_v2 Dataset**: Built-in dataset containing 1,810 geometric problems with full formal representation.
- 🔧 **Flexible Configuration**: Supports multi-process parallel searching with customizable depth, timeout, and beam size.
- 🤖 **AI Integration**: (Optional) Tools for CDL generation using LLMs like Gemini and ChatGPT.

## 📁 Project Structure

The core implementation is located in the `src/` directory.

```
FGPS-main/
├── src/fgps/              # Main Package
│   ├── search.py         # Search Algorithms Implementation
│   ├── run.py            # Execution & Auto-Solver Scripts
│   ├── enhanced_search.py # Enhanced Search Capabilities
│   ├── utils.py          # Utility Functions & Argument Parsing
│   └── formalgeo7k_v2/   # Dataset Directory
│       ├── problems/     # Problem Files (JSON format)
│       ├── images/       # Problem Diagrams
│       └── gdl/          # Geometric Description Language Definitions
│
├── formalgeo/             # FormalGeo Core Library (Engine, Parser, Solver)
└── gemini/                # (Optional) AI Model Evaluation Tools
```

### `src/fgps/` Details

This directory contains the core logic for the problem solver:

- **`search.py`**: The heart of the solver. It implements the search strategies (Forward/Backward) and algorithms (BFS, DFS, RS, BS). It handles the state space search to find a sequence of theorems that proves the target goal.
- **`run.py`**: The entry point for running the solver. It supports two modes:
    - `run`: Interactive mode for solving a single problem.
    - `auto_run`: Batch mode for solving all problems in the dataset automatically.
- **`formalgeo7k_v2/`**: The dataset directory.
    - **`problems/`**: Contains JSON files for each problem. Each file describes the problem's construction (CDL), text (CDL), and goal.
    - **`gdl/`**: Contains `predicate_GDL.json` and `theorem_GDL.json`, defining the fundamental geometric predicates and theorems used by the solver.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# Install core dependencies
pip install -r requirements.txt

# Or install manually
pip install formalgeo psutil func-timeout sympy
```

### Usage

All commands should be executed from the `src/fgps` directory.

#### 1. Interactive Solver

Solve a specific problem by entering its ID (pid).

```bash
cd src/fgps
python run.py --func run --dataset_name formalgeo7k_v2
```

Example input:
```
<pid>: 113
```

#### 2. Batch Solver

Automatically attempt to solve all problems in the dataset.

```bash
cd src/fgps
python run.py --func auto_run --dataset_name formalgeo7k_v2
```

#### 3. Advanced Search

Use `search.py` to customize search algorithms and parameters.

```bash
cd src/fgps
python search.py \
    --dataset_name formalgeo7k_v2 \
    --method fw \
    --strategy bfs \
    --max_depth 1500 \
    --timeout 60
```

**Arguments:**
- `--method`: Search direction (`fw` for Forward, `bw` for Backward).
- `--strategy`: Search algorithm (`bfs`, `dfs`, `rs`, `bs`).
- `--max_depth`: Maximum search depth.
- `--timeout`: Timeout in seconds for a single problem.
- `--beam_size`: Beam size (only for Beam Search).
- `--process_count`: Number of parallel processes.

## 🔧 Configuration

### Dataset Path

The default dataset path is `src/fgps`. You can specify a custom path:

```bash
python run.py --path_datasets /path/to/datasets
```

### Logging

Logs are saved in `src/fgps` by default. Change the log directory:

```bash
python search.py --path_logs /path/to/logs
```

## ❓ FAQ

**Q: How do I choose a search strategy?**
- **BFS**: Finds the shortest proof path but consumes more memory.
- **DFS**: Memory-efficient but may explore very deep paths.
- **BS (Beam Search)**: Balances between quality and efficiency; requires tuning `beam_size`.

**Q: How can I improve the success rate?**
1. Increase `max_depth`.
2. Increase `timeout`.
3. Try Backward Search (`--method bw`).

## 🤝 Contribution

Contributions are welcome! Please fork the repository and submit a Pull Request.

## 📄 License

This project is licensed under the MIT License. The dataset in `src/fgps/formalgeo7k_v2` may have its own license.

## 🙏 Acknowledgments

- [FormalGeo](https://github.com/FormalGeo) Framework
- FormalGeo Development Team

---

**Note**: This project is for research and educational purposes.
