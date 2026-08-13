# SightRefiner

相机画面问题检测与矫正算法库，为边缘端视频分析提供前处理能力。

## 功能模块

### 1. 遮挡检测 (Occlusion Detection)

检测相机镜头是否被遮挡，支持基于边缘复杂度和纹理片段分布的检测方法。

**主要功能：**

- `ComplexityDetector`: 基于边缘复杂度的遮挡检测
- `FragmentDetector`: 基于纹理片段分布的遮挡检测
- `ROCMetrics` 和 `HardCaseMining`: ROC 指标评估与困难样本挖掘

### 2. 鱼眼矫正 (Fisheye Calibration & Dewarp)

鱼眼相机自动校准和图像矫正 pipeline，面向边缘端实时视频处理。

**主要功能：**

- 自动检测成像圆并生成相机配置文件
- 支持虚拟透视、360 度全景展开、地面正射等输出投影
- 支持 LUT 烘焙，便于边缘端快速处理

### 3. 模糊检测 (Blur Detection)

预留模块，用于后续检测画面模糊、失焦等质量问题。

## 环境要求

- Python >= 3.12.7
- 使用 `uv` 进行依赖管理

## 快速开始

### 安装依赖

```bash
uv sync
```

### 遮挡检测示例

```python
import cv2
from sightrefiner.occlusion import ComplexityDetector

frame = cv2.imread("test_image.jpg")
score = ComplexityDetector(frame, size=(160, 120), super_pixel_set=(12, 9))
print(f"遮挡分数：{score}")
```

### 鱼眼矫正示例

```python
import cv2
from sightrefiner.fisheye import auto_profile, build_maps, save_maps, Dewarper

frame = cv2.imread("fisheye_frame.png")

profile = auto_profile(frame, camera_id="store42_cam01")
profile.to_json("store42_cam01.json")

save_maps(build_maps(profile), "store42_cam01_luts.npz")

dw = Dewarper("store42_cam01_luts.npz")
outputs = dw.process(frame)
```

## 项目结构

远端仓库只跟踪源码、配置、示例和可复用文档。具体样本、测试图片、测试报告、LUT、运行输出和实验性 API 目录属于本地数据或生成物，不进入 Git。

```text
SightRefiner/
├── README.md                       # 项目总 README，必须跟踪
├── pyproject.toml                  # 项目依赖配置
├── uv.lock                         # 依赖锁定
├── doc/                            # 其他无法归入模块的文档，必须跟踪
├── data/
│   ├── fisheye/
│   │   ├── schemas/                # 数据结构定义，允许跟踪
│   │   └── batches/
│   │       └── <batch_id>/
│   │           ├── raw/            # 原始素材，不跟踪
│   │           ├── manifest.json   # 可选：记录脚本入口和期望规模，通常不跟踪
│   │           ├── preprocess.py   # 可选：该批次 raw 到标准输入的适配脚本，可跟踪
│   │           ├── make_report.py  # 可选：该批次报告生成脚本，可跟踪
│   │           ├── images/         # 标准测试输入图片，不跟踪
│   │           └── report/         # 测试报告，不跟踪
│   └── occlusion/
│       └── config.conf             # 可复用配置，允许跟踪
├── sightrefiner/                   # 主代码包
│   ├── occlusion/                  # 遮挡检测模块
│   ├── fisheye/                    # 鱼眼矫正模块
│   │   └── research/               # 模块调研文档，HTML 单文件，必须跟踪
│   ├── blur/                       # 模糊检测模块（待实现）
│   └── utils/                      # 共用工具
├── tools/                          # 按模块放置跨 batch 复用的标准输入 helper，不放 raw 私有适配脚本
└── examples/                       # 示例程序
```

## 文档和数据归档规则

- 项目总 README 放在仓库根目录 `README.md`，需要进入 Git。
- 不同模块的调研文档放在各自模块目录下的 `research/`，例如 `sightrefiner/fisheye/research/`。调研文档必须使用单文件 HTML；如果包含图片，图片必须以 `data:image/...;base64,...` 嵌入 HTML，不提交单独图片文件。
- 不同模块的测试素材和测试报告放在 `data/<module>/batches/<batch_id>/` 下，并按 `raw/`、`images/`、`report/` 三类组织。这三类目录不进入 Git。
- 批次名建议用日期开头并附来源或目的，例如 `2026-08-10_pilot_camera_scrnsht`、`2026-08-20_store_retest_round2`。
- 原始数据不定义公共输入协议。每个 batch 可以自带自己的预处理方式，把任意 `raw/` 形态转换为标准测试输入即可。
- 标准测试流程从 `images/` 开始：`images/*.png` 是算法测试图片，`images/meta.json` 记录每张图片的门店/场地、相机、圆心半径、来源文件或来源区域。公共测试脚本只依赖这个标准输入，不直接读取 `raw/`。
- 标准 meta 需要显式表达 `site.id` 和 `camera.id`；不同 batch 的 raw 可以长得不一样，但进入测试前都要归一到“门店/场地 -> 相机 -> 样本”的结构。
- batch 专用预处理脚本优先放在 `data/<module>/batches/<batch_id>/preprocess.py`。如果逻辑可复用，再抽到 `tools/<module>/`；不要让公共测试脚本感知某批 raw 的私有格式。
- `report/` 是测试流程的输出，包含 `summary.json`、可视化样本和 HTML 报告等批次结果。报告脚本可以 case by case 由 agent 生成，优先放在 batch 根目录，例如 `make_report.py`；如果逻辑稳定复用，再抽到 `tools/<module>/`。
- batch 根目录可以放可选的 `manifest.json`，用于记录 `preprocess.py`、`make_report.py` 等脚本入口和期望的门店/相机/样本数量；manifest 不是 raw 输入协议。
- 测试报告必须是单文件 HTML。报告中使用的图片必须以 `data:image/...;base64,...` 内嵌，不引用本地相对路径或 `data/` 下的图片文件。
- 测试数据的 schema、schemas、ontology、ontologies 等结构定义允许进入 Git；它们只描述数据结构或概念体系，不应包含具体样本、截图、检测结果或运行输出。
- 其他不知道如何归类到具体模块的文档放在 `doc/` 下，需要进入 Git。
- 更详细的 agent 执行协议见 `doc/test_data_protocol.md`。

## 本地忽略内容

- `data/<module>/images/`、`data/<module>/raw/`、`data/<module>/report/`
- `data/<module>/batches/<batch_id>/images/`、`raw/`、`report/`
- `data/*/Exposed/`、`data/*/Occluded/`
- `data/` 下的图片、视频、表格、数组缓存、JSONL/NDJSON/Parquet 等具体数据文件
- `data/**/report/`、`data/**/reports/`、`data/**/screenshots/`
- `plots/`、`output_*.png`
- `REPORT*.html`、`REPORT*.md`
- 运行生成的普通 `*.json`、`*.npz`、`*.xlsx`
- `cpp_api/`、`go_api/`

## 核心依赖

- `numpy >= 2.5.2`
- `opencv-python-headless >= 5.0.0.93`
- `matplotlib >= 3.9.0`
- `openpyxl >= 3.1.5`

## 开发计划

- [x] 遮挡检测模块
- [x] 鱼眼矫正模块
- [ ] 模糊检测模块
- [ ] 畸变矫正模块（非鱼眼）
- [ ] 统一的评估框架

## 许可证

MIT License
