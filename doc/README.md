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

远端仓库只跟踪源码、配置、示例和文档。样本图像、报告输出、LUT、JSON 配置和实验性 API 目录属于本地数据或生成物，不进入 Git。

```
SightRefiner/
├── pyproject.toml          # 项目依赖配置
├── uv.lock                 # 依赖锁定
├── doc/
│   └── README.md           # 项目说明
├── data/
│   └── occlusion/
│       └── config.conf     # 遮挡检测示例配置
├── sightrefiner/           # 主代码包
│   ├── occlusion/          # 遮挡检测模块
│   ├── fisheye/            # 鱼眼矫正模块
│   ├── blur/               # 模糊检测模块（待实现）
│   └── utils/              # 共用工具
├── tools/                  # 工具脚本和调研材料
│   └── research/
│       └── fisheye_research.md
└── examples/               # 示例程序
```

## 文档和报告规则

- 项目说明类文档放在 `doc/`。
- 纯调研类材料和报告生成脚本放在 `tools/`，例如 `tools/research/` 和 `tools/make_report.py`。
- 本次重构相关的临时汇报文件不保留。
- 如果调研材料需要展示测试数据图片，提交物必须是自包含 HTML，并把图片以 `data:image/...;base64,...` 形式内嵌；不要引用 `data/` 下的本地图片路径。外部论文、文档、项目主页等参考链接可以保留 URL。
- 测试报告输出跟随数据目录，例如 `data/report/` 或 `data/<dataset>/report/`，并且不提交。

## 本地忽略内容

- `data/` 下的测试图片、`data/*/Exposed/`、`data/*/Occluded/`
- `data/**/report/`、`data/**/reports/`
- `plots/`、`output_*.png`
- `REPORT*.html`、`REPORT*.md`
- `*.json`、`*.npz`、`*.xlsx`
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
