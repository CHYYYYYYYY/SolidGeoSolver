# Hilbert-Geo: Solving Solid Geometric Problems by Neural-Symbolic Reasoning
![logo](logo.png)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

"Arithmetical symbols are written figures, and geometrical figures are painted formulas." — David Hilbert

**Hilbert-Geo** is a unified formal language framework designed to solve both plane and solid geometric problems through neural-symbolic reasoning. To bridge the gap in solid geometry reasoning, which involves complex 3D spatial diagrams, we introduce the **Parse2Reason** method.

This repository contains the implementation of the Hilbert-Geo framework, including the reasoning engine, formal language definitions, and evaluation tools.

## 📄 Abstract

Geometric problem solving is a typical multimodal reasoning challenge. While significant progress has been made in plane geometry, solid geometry remains difficult due to 3D spatial diagrams and complex reasoning requirements. 

**Hilbert-Geo** addresses this by:
1.  **Unified Framework**: The first unified formal language framework for solid geometry, featuring an extensive predicate library and a dedicated theorem bank.
2.  **Parse2Reason Method**:
    *   **Parsing Step**: Utilizes **Conditional Description Language (CDL)** to formally represent both problem descriptions (natural text) and diagrams (visual images).
    *   **Reasoning Step**: Leverages formal CDL and the theorem bank to perform relational inference and algebraic computation, generating strictly correct, verifiable, and human-readable reasoning processes.
3.  **Generalizability**: Applicable to both plane and solid geometry.

## ✨ Key Features

*   **Neural-Symbolic Reasoning**: Combines the perceptual power of neural models (for parsing) with the rigorous logic of symbolic engines (for reasoning).
*   **Parse2Reason Pipeline**: A two-step approach ensuring high accuracy and interpretability.
*   **Extensive Datasets**:
    *   **SolidFGeo2k**: A curated dataset of solid geometry problems with formal annotations.
    *   **MathVerse-solid**: A subset of MathVerse with formal annotations.
    *   **PlaneFGeo3k**: A dataset of plane geometry problems with formal annotations.
*   **SOTA Performance**:
    *   **77.3%** accuracy on SolidFGeo2k.
    *   **84.1%** on MathVerse-Solid (subset), significantly outperforming leading MLLMs like Gemini-2.5-pro (54.2%) and GPT-5 (62.9%).
    *   **80.2%** accuracy on PlaneFGeo3k.

## 📁 Project Structure

The core implementation is located in the `src/` directory.

```
Hilbert-Geo/
├── src/fgps/              # Main Package (Solver Implementation)
│   ├── search.py         # Search Algorithms (Forward/Backward, BFS/DFS/Beam)
│   ├── run.py            # Execution & Auto-Solver Scripts
│   ├── enhanced_search.py # Enhanced Search Capabilities
│   ├── utils.py          # Utility Functions
│   └── Hilbert-Geo/   # Dataset Directory (Legacy naming, includes new datasets)
│       ├── problems/     # Problem Files (JSON format with CDL)
│       ├── images/       # Problem Diagrams
│       └── gdl/          # GDL Definitions (Predicates & Theorems)
│
├── formalgeo/             # FormalGeo Core Library (Engine, Parser, Solver)
└── gemini/                # AI Model Evaluation & Parsing Tools
```

## 🚀 Quick Start

### Prerequisites
*   Python 3.8+
*   pip

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
python run.py --func run --dataset_name 
```
*Example input:* `<pid>: 113`

#### 2. Batch Solver (Evaluation)
Automatically attempt to solve all problems in the dataset to reproduce results.

```bash
cd src/fgps
python run.py --func auto_run --dataset_name 
```

#### 3. Advanced Search Configuration
Use `search.py` to customize search algorithms and parameters (e.g., for ablation studies).

```bash
cd src/fgps
python search.py \
    --dataset_name  \
    --method fw \
    --strategy bfs \
    --max_depth 150000 \
    --timeout 6000
```

**Arguments:**
*   `--method`: Search direction.
*   `--strategy`: Search algorithm.
*   `--max_depth`: Maximum search depth.
*   `--timeout`: Timeout in seconds per problem.
*   `--beam_size`: Beam size (for Beam Search).
*   `--process_count`: Number of parallel processes.

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

## 📄 Citation

If you find this work useful in your research, please cite our paper:

```bibtex
@article{xu2025hilbert,
  title={Hilbert-Geo: Solving Solid Geometric Problems by Neural-Symbolic Reasoning},
  author={Xu, Ruoran and Cheng, Haoyu and Dong, Bin and Wang, Qiufeng},
  journal={CVPR Conference Submission},
  year={2026}
}
```

