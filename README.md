<p align="center">
  <h1 style="display: inline;">
    <img src="./logo.png" alt="Logo" style="width: 50px; vertical-align: middle; margin-right: 10px;">
    Hilbert-Geo: Solving Solid Geometric Problems by Neural-Symbolic Reasoning
  </h1>
</p>

<p align="center">
  <a href="https://github.com/CHYYYYYYYY/SolidGeoSolver">🌐 Homepage</a> •
  <a href="https://github.com/CHYYYYYYYY/SolidGeoSolver">🥇 Leaderboard</a> •
  <a href="https://github.com/CHYYYYYYYY/SolidGeoSolver">📖 Paper</a> •
  <a href="https://github.com/CHYYYYYYYY/SolidGeoSolver">🤗 Data</a>
</p>


# 🔥 News

<div style="max-height: 350px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px 15px; background-color: #fafafa;" markdown="1">
- *2026.02*: &nbsp;🎉🎉 Our paper "Hilbert-Geo: Solving Solid Geometric Problems by Neural-Symbolic Reasoning" was accepted by CVPR2026.
</div>

## Structure

```text
SolidGeoSolver/
├── api/
│   ├── base.py
│   ├── claude_api.py
│   ├── gemini_api.py
│   └── openai_api.py
├── core/
│   ├── fgps/
│   ├── gdl/
│   ├── files/
│   └── hilbert_geo/
└── data/
    └── hilbert_geo7k_v2/
```

- `api/` contains prompt-and-call helpers for model APIs.
- `core/hilbert_geo/` is the renamed FormalGeo package.
- `core/gdl/` and `core/files/t_info.json` keep the predicate bank, theorem bank, and theorem metadata with the core code.
- `data/hilbert_geo7k_v2/` contains a 1k sample subset for repository display and quick testing.

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the interactive solver:

```bash
python core/fgps/run.py --func run
```

Run search:

```bash
python core/fgps/search.py --func search --method fw --strategy bfs
```

By default:

- datasets are loaded from `data/`
- logs are written to `core/fgps/`
- GDL and theorem metadata are loaded from `core/` when they are not present in the dataset folder

## Notes

- The Python package name is now `hilbert_geo`.
- The repository display name used in docs is `Hilbert-Geo`.
- The sample dataset folder is renamed to `hilbert_geo7k_v2` and only includes the first 1000 problems.
