# FGPS - FormalGeo Problem Solver

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

FGPS (FormalGeo Problem Solver) 是一个基于 FormalGeo 框架的几何问题自动求解系统。该系统能够对几何问题进行形式化表示，并通过多种搜索策略自动求解几何问题。同时，项目还集成了多个 AI 模型（Gemini、ChatGPT、DeepSeek）用于几何问题的条件描述语言（CDL）生成和评估。

## ✨ 主要特性

- 🔍 **多种搜索策略**：支持前向搜索（Forward）和后向搜索（Backward）
- 🎯 **多种搜索算法**：广度优先搜索（BFS）、深度优先搜索（DFS）、随机搜索（RS）、束搜索（BS）
- 📊 **大规模数据集**：内置 FormalGeo7k_v2 数据集，包含 1810 道几何问题
- 🤖 **AI 模型集成**：支持 Gemini、ChatGPT、DeepSeek 等模型进行 CDL 生成
- 📈 **性能评估**：提供完整的评估工具和性能对比分析
- 🔧 **灵活配置**：支持多进程并行搜索，可配置搜索深度、超时时间等参数

## 📁 项目结构

```
FGPS-main/
├── formalgeo/              # FormalGeo 核心库
│   ├── core/              # 核心引擎
│   ├── data/              # 数据加载模块
│   ├── parse/             # 解析模块
│   ├── problem/           # 问题表示模块
│   ├── reasoning/         # 推理模块
│   ├── solver/            # 求解器模块
│   └── tools/             # 工具函数
│
├── src/fgps/              # FGPS 主程序
│   ├── search.py         # 搜索算法实现
│   ├── run.py            # 运行和自动求解
│   ├── enhanced_search.py # 增强搜索功能
│   └── formalgeo7k_v2/   # FormalGeo7k_v2 数据集
│       ├── problems/     # 问题文件（1810个JSON文件）
│       ├── images/       # 问题图像
│       └── gdl/          # 几何描述语言定义
│
├── gemini/                # AI 模型测试和评估
│   ├── gemini2.5_pro.py  # Gemini 模型实现
│   ├── chatgpt_pro.py    # ChatGPT 模型实现
│   ├── deepseek_pro.py   # DeepSeek 模型实现
│   ├── evaluate_cdl.py   # CDL 评估工具
│   └── run_all_models.py # 统一运行脚本
│
├── data/                  # 数据集和训练数据
├── figures/               # 性能分析图表
└── README.md              # 本文件
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
# 安装所有依赖（推荐）
pip install -r requirements.txt

# 或者单独安装核心依赖
pip install formalgeo psutil func-timeout sympy

# 如果需要使用 AI 模型功能，还需要安装：
pip install google-generativeai openai pillow tqdm pydantic
```

### 基本使用

#### 1. 交互式求解单个问题

```bash
cd src/fgps
python run.py --func run --dataset_name formalgeo7k_v2
```

然后输入问题 ID，例如：
```
<pid>:113
```

#### 2. 自动批量求解

```bash
cd src/fgps
python run.py --func auto_run --dataset_name formalgeo7k_v2
```

#### 3. 使用搜索算法求解

```bash
cd src/fgps
python search.py \
    --dataset_name formalgeo7k_v2 \
    --method fw \
    --strategy bfs \
    --max_depth 1500000 \
    --timeout 3600000
```

**参数说明：**
- `--method`: 搜索方向，`fw`（前向）或 `bw`（后向）
- `--strategy`: 搜索策略，`bfs`（广度优先）、`dfs`（深度优先）、`rs`（随机）、`bs`（束搜索）
- `--max_depth`: 最大搜索深度
- `--timeout`: 超时时间（秒）
- `--beam_size`: 束搜索的束大小（仅当 strategy=bs 时有效）
- `--process_count`: 并行进程数

## 📖 详细文档

### FormalGeo 框架

FormalGeo 是一个用于几何问题形式化表示和求解的框架。更多信息请参考：
- [FormalGeo 官方文档](https://formalgeo.github.io/)
- `formalgeo/` 目录下的代码和注释

### 数据集

项目使用 FormalGeo7k_v2 数据集，包含：
- **1810 道几何问题**：每道问题都有完整的 CDL 表示
- **问题图像**：包含问题的几何图形
- **GDL 定义**：几何描述语言（Geometry Description Language）的谓词和定理定义

数据集位置：`src/fgps/formalgeo7k_v2/`

### AI 模型集成

项目集成了多个 AI 模型用于几何问题的 CDL 生成：

#### 使用 Gemini 模型

```bash
cd gemini
python gemini2.5_pro.py
```

#### 使用 ChatGPT 模型

```bash
cd gemini
python chatgpt_pro.py
```

#### 使用 DeepSeek 模型

```bash
cd gemini
python deepseek_pro.py
```

#### 运行所有模型并对比

```bash
cd gemini
python run_all_models.py --models all
```

更多详细信息请参考 `gemini/` 目录下的文档。

## 🔧 配置说明

### 数据集路径配置

默认数据集路径为 `src/fgps`，可以通过参数修改：

```bash
python run.py --path_datasets /path/to/datasets
```

### 日志路径配置

默认日志保存在 `src/fgps`，可以通过参数修改：

```bash
python search.py --path_logs /path/to/logs
```

### 搜索参数调优

根据问题规模和计算资源调整以下参数：

- **max_depth**: 控制搜索的最大深度，值越大搜索空间越大但耗时更长
- **beam_size**: 束搜索的束大小，影响内存使用和搜索质量
- **timeout**: 单个问题的超时时间，防止无限搜索
- **process_count**: 并行进程数，建议设置为 CPU 核心数的 80%

## 📊 性能评估

项目提供了完整的性能评估工具：

1. **CDL 评估**：评估 AI 模型生成的 CDL 质量
2. **求解率统计**：统计不同搜索策略的求解率
3. **性能对比**：对比不同模型和策略的性能

评估结果保存在 `gemini/evaluation_results/` 目录下。

## 💡 使用示例

### 示例 1：求解单个问题

```python
from formalgeo.data import DatasetLoader
from formalgeo.solver import Interactor
from formalgeo.parse import parse_theorem_seqs

# 加载数据集
dl = DatasetLoader("formalgeo7k_v2", "src/fgps")
solver = Interactor(dl.predicate_GDL, dl.theorem_GDL)

# 加载问题 113
problem_CDL = dl.get_problem(113)
solver.load_problem(problem_CDL)

# 应用定理序列求解
for t_name, t_branch, t_para in parse_theorem_seqs(problem_CDL["theorem_seqs"]):
    solver.apply_theorem(t_name, t_branch, t_para)

# 检查目标是否达成
solver.problem.check_goal()

# 显示求解过程
from formalgeo.tools import show_solution
show_solution(solver.problem)
```

### 示例 2：使用搜索算法

```python
from fgps.search import search_problem

# 使用前向广度优先搜索求解问题 113
result = search_problem(
    dataset_name="formalgeo7k_v2",
    problem_id=113,
    method="fw",
    strategy="bfs",
    max_depth=1000,
    timeout=60
)
```

## ❓ 常见问题

### Q: 如何修改数据集路径？

A: 使用 `--path_datasets` 参数指定数据集路径：
```bash
python run.py --path_datasets /your/path/to/datasets
```

### Q: 搜索算法如何选择？

A: 
- **BFS（广度优先）**：适合寻找最短解路径，内存消耗较大
- **DFS（深度优先）**：内存消耗小，但可能陷入深层搜索
- **RS（随机搜索）**：适合探索性搜索，结果随机
- **BS（束搜索）**：平衡搜索质量和效率，需要设置 beam_size

### Q: 如何提高求解率？

A: 
1. 增加 `max_depth` 参数
2. 增加 `timeout` 时间
3. 尝试不同的搜索策略
4. 使用后向搜索（`--method bw`）

### Q: AI 模型需要 API Key 吗？

A: 是的，使用 AI 模型功能需要配置相应的 API Key。请参考 `gemini/` 目录下的文档进行配置。

## 🔬 开发说明

### 项目结构说明

- `formalgeo/`: FormalGeo 框架的核心实现，包含几何问题的形式化表示、解析、推理和求解功能
- `src/fgps/`: FGPS 主程序，包含搜索算法、运行脚本和数据集
- `gemini/`: AI 模型集成代码，用于 CDL 生成和评估

### 扩展开发

如需添加新的搜索策略或 AI 模型：

1. **添加搜索策略**：在 `src/fgps/search.py` 中实现新的策略函数
2. **添加 AI 模型**：参考 `gemini/` 目录下的模型实现，创建新的模型文件
3. **添加评估指标**：在 `gemini/evaluate_cdl.py` 中添加新的评估函数

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

贡献指南：
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。数据集部分请参考 `src/fgps/formalgeo7k_v2/LICENSE`。

## 🙏 致谢

- [FormalGeo](https://github.com/FormalGeo) - 几何问题形式化框架
- FormalGeo 开发团队
- 所有为本项目做出贡献的开发者

## 📮 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 参考项目文档

## 📚 相关资源

- [FormalGeo 官方网站](https://formalgeo.github.io/)
- [FormalGeo GitHub](https://github.com/FormalGeo)
- [FormalGeo7k 数据集](https://github.com/FormalGeo/Datasets)

---

**注意**：本项目仅供研究和教育用途。

