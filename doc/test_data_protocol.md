# Test Data Protocol

本文档约束从“标准测试输入”到“测试报告输出”的公共流程，同时说明 agent 应该如何为每个 batch 编写 raw 适配逻辑。

## 核心边界

项目不定义原始数据的统一输入协议。`raw/` 可以是 Excel、截图目录、视频、压缩包、第三方导出、设置页截图或其他临时材料。

公共测试流程只从标准测试输入开始：

```text
data/<module>/batches/<batch_id>/
├── raw/                 # 原始材料，本地保留，不跟踪
├── manifest.json        # 可选，记录本 batch 的脚本入口和期望规模，通常不跟踪
├── preprocess.py        # 可选，batch 专用 raw 适配脚本，可跟踪
├── make_report.py       # 可选，batch 专用报告脚本，可跟踪
├── images/              # 标准测试输入，本地保留，不跟踪
│   ├── <sample>.png
│   └── meta.json
└── report/              # 测试输出，本地保留，不跟踪
```

`raw/` 到 `images/` 的转换是 batch-local preprocessing。它可以由 agent 根据当批 raw 的实际组成临时编写，不需要形成长期公共接口。

## 脚本放置规则

优先把 batch 专用预处理脚本放在：

```text
data/<module>/batches/<batch_id>/preprocess.py
```

这个脚本只负责当前 batch 的 raw 解析和标准化输出。它可以被跟踪提交，前提是脚本本身不包含敏感路径、客户秘密、token 或具体大样本内容。

如果某段预处理逻辑已经被多个 batch 复用，再抽到对应模块的工具目录：

```text
tools/<module>/
```

公共测试脚本不得依赖某个 batch 的 raw 私有格式。公共脚本只能读取标准测试输入，例如 `images/*.png`、`images/meta.json`。

报告生成脚本也可以是 batch-local：

```text
data/<module>/batches/<batch_id>/make_report.py
```

如果报告叙事、截图选取、指标解释、客户展示方式只适用于当前 batch，就让 agent 为当前 batch 生成脚本。只有当报告逻辑稳定复用时，才抽到 `tools/<module>/`。

不要把脚本放到 `report/` 目录下；`report/` 是输出目录，默认不跟踪。

可选的 `manifest.json` 放在 batch 根目录，用于记录脚本入口和期望规模：

```json
{
  "batch_id": "2026-08-13_fisheye_setting_snapshots",
  "module": "fisheye",
  "paths": {
    "raw": "raw",
    "images": "images",
    "report": "report"
  },
  "scripts": {
    "preprocess": "preprocess.py",
    "report": "make_report.py"
  },
  "expected": {
    "sites": 5,
    "cameras": 6,
    "samples": 6
  }
}
```

manifest 是辅助索引，不是 raw 输入协议。它不需要描述 raw 的内部结构。

## Agent 工作流

当用户给出一个新 batch 时，agent 应按以下顺序处理：

1. 检查 `data/<module>/batches/<batch_id>/raw/` 的文件类型、目录结构和样例尺寸。
2. 判断 raw 组成，例如 Excel 内嵌截图、单相机图片目录、视频帧、设置截图混合目录等。
3. 编写或更新 `preprocess.py`，只处理当前 batch 的 raw 到标准输入转换。
4. 运行 `preprocess.py`，生成 `images/*.png` 和 `images/meta.json`。
5. 校验标准输入，而不是校验 raw 协议。
6. 运行算法测试，生成必要的结构化结果，例如 `report/summary.json` 和可视化样本。
7. 按当前 case 编写或复用报告脚本，生成单文件 HTML 报告。
8. 确认 `raw/`、`images/`、`report/` 都被 `.gitignore` 忽略；只提交协议、schema、公共脚本、可复用文档和安全的 batch 脚本。

## 标准输入协议

`images/` 下只放算法实际消费的标准测试图片。对图像类模块，推荐统一为 PNG。

`images/meta.json` 是一个对象，key 必须等于 `images/` 下的文件名：

```json
{
  "sample_name.png": {
    "site": {
      "id": "store_or_site_id",
      "label": "optional_display_name"
    },
    "camera": {
      "id": "camera_id",
      "label": "optional_display_name"
    },
    "source": {
      "file": "raw/path/to/source.ext",
      "bbox": [0, 0, 1920, 1920]
    }
  }
}
```

`site` 和 `camera` 是标准层级。不同数据集的原始组织方式可以不同，但标准测试输入必须能回答“这个样本来自哪个门店/场地、哪台相机”。模块可以扩展 meta 字段，但公共测试脚本必须明确声明自己需要的字段。

### Fisheye 必需字段

fisheye 测试流程需要每个样本包含：

```json
{
  "sample_name.png": {
    "site": {
      "id": "store_or_site_id"
    },
    "camera": {
      "id": "camera_id"
    },
    "circle": {
      "cx": 960.0,
      "cy": 960.0,
      "r": 930.0
    },
    "source": {
      "file": "raw/path/to/source.ext",
      "bbox": [0, 0, 1920, 1920]
    }
  }
}
```

`circle` 使用标准测试图片坐标系。若样本来自原图裁剪，`source.bbox` 记录裁剪区域；若样本就是完整 raw 图片，`source.bbox` 使用完整图像范围。
历史 batch 里可能仍有 `store`、`source_file`、`source_bbox` 这类扁平字段；新脚本应写入标准对象字段，公共工具可以短期兼容旧字段。

## Raw 适配原则

- 保留 raw 的原始形态，不为了公共流程强行改造 raw。
- 适配脚本可以跳过非测试图片，例如 `specs.jpg`、设置页截图、说明图、下载链接等。
- 标准测试图片命名应稳定、可读、可排序，避免空格和特殊字符。
- 每个样本必须显式写出 `site.id` 和 `camera.id`；不要只把门店/相机信息藏在文件名里。
- `meta.json` 必须能把标准测试图片追溯回 raw 来源。
- 预处理脚本应可重复运行；重复运行不应依赖手工清理。
- 如果 raw 包含敏感信息，脚本里不要写死敏感名称；用相对路径和可解释的过滤规则。

## 测试与报告流程

标准测试从这里开始：

```text
data/<module>/batches/<batch_id>/images/
```

测试和报告输出到：

```text
data/<module>/batches/<batch_id>/report/
```

报告输出可以包含结构化结果、可视化汇总图和中间可读图片。以 fisheye 当前流程为例：

```text
report/
├── summary.json
├── samples/             # 拼接后的可视化总览图
├── views/               # 每个样本拼接前的独立输出图
│   └── <sample>/
│       ├── source.png
│       ├── panorama.png
│       ├── view0.png
│       ├── view1.png
│       ├── view2.png
│       └── view3.png
└── REPORT_EN.html
```

公共工具可以存在，但不是协议本身。以 fisheye 当前 helper 为例：

```bash
uv run python tools/fisheye/make_report.py <batch_id>
uv run python tools/fisheye/make_html_report.py <batch_id>
```

这些 helper 不应读取 `raw/`，也不应知道某个 batch 是 Excel、截图目录还是其他来源。

如果当前 batch 的报告需要特殊说明、特殊筛图、特殊指标或客户化叙事，agent 可以改用：

```bash
uv run python data/<module>/batches/<batch_id>/make_report.py
```

无论脚本放在哪里，最终报告必须满足：

- 输出为一个 `.html` 文件。
- HTML 自包含，不依赖本地图片、CSS、JS 或 `data/` 下的相对路径。
- 图片必须以 `data:image/...;base64,...` 形式内嵌。
- 报告文件放在 `data/<module>/batches/<batch_id>/report/` 下，不跟踪提交。

## Schema 和跟踪规则

schema、ontology、公共协议文档需要跟踪提交：

```text
data/<module>/schemas/
data/<module>/ontology/
doc/
README.md
```

fisheye 当前标准输入 schema 位于：

```text
data/fisheye/schemas/image_meta.schema.json
data/fisheye/schemas/batch_manifest.schema.json
data/fisheye/schemas/report_summary.schema.json
```

具体数据和产物不跟踪：

```text
data/<module>/batches/<batch_id>/raw/
data/<module>/batches/<batch_id>/images/
data/<module>/batches/<batch_id>/report/
```

batch-local `preprocess.py` 可以跟踪；如果只是临时、敏感或不可复用，也可以只留本地。

batch-local `make_report.py` 同样可以跟踪；报告产物本身不跟踪。
