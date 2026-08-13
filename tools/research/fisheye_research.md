# 鱼眼矫正方案调研纪要 (边缘端客流统计场景)

> 调研时间:2026-08。场景：顶装 360° 鱼眼 (圆形成像、FOV≈180°+) 为主、少量壁装;
> 约束：无法逐相机棋盘格标定;边缘端逐帧成本必须极低;输出供通用行人检测/计数模型使用。

## 1. 相机模型

| 模型                               | 映射            | 适用性                                                                        |
| ---------------------------------- | --------------- | ----------------------------------------------------------------------------- |
| **等距投影 equidistant (f-theta)** | ρ = f·θ         | **监控鱼眼镜头的事实标准**,DW Spectrum / Nx Witness / NVIDIA VPI 等的默认选项 |
| 等立体角 equisolid                 | ρ = 2f·sin(θ/2) | 摄影镜头常见                                                                  |
| 体视 stereographic                 | ρ = 2f·tan(θ/2) | 保角，CCTV 少见                                                               |
| Kannala-Brandt 多项式              | ρ = k₁θ+k₂θ³+…  | OpenCV `cv2.fisheye` 即此模型，可退化为上述任意一种                           |
| Mei 统一模型 / Scaramuzza          | —               | OpenCV contrib `cv::omnidir`;>180° 或需精细校准时用                           |

**结论：镜头规格未知时，默认 equidistant + FOV=180°**(f = R/(π/2)),误差集中在最终会被丢弃的边缘区;FOV 作为 profile 中的单一可调参数。

## 2. 无标定物自动校准

- **成像圆检测**(圆心 + 半径):最鲁棒、信息量最大的第一步。阈值分割 → 轮廓 → 最小二乘圆拟合 → 非线性精化。业界有专利化的同款流程 (US 11699216“Automatic fisheye camera calibration for video analytics”)。注意：部分相机上下裁切成像圆，要按弧/椭圆拟合。
- **Plumb-line / 直线自校准**(可选精化):优化畸变参数使场景直线 (货架、地砖、门框) 变直。经典:Devernay & Faugeras 2001(有 IPOL 复现);Rosten & Loveland(角向 Hough 直方图熵最小化，单帧自然图像鲁棒);Xue et al. CVPR 2019(CNN 检测畸变直线)。注意 ~180° 视场时直线约束应在视球上表述 (大圆约束)。
- **深度学习单图校准**(离线服务器侧一次性):DeepCalib(2018，老)、GeoCalib(ECCV 2024，维护好)、AnyCalib(2025，闭式拟合多种模型，SOTA)。多以合成畸变训练，对真实顶装鱼眼泛化需验证——**当作初始化/交叉校验，不当作唯一来源**。

## 3. 输出投影 (业界做法)

厂商 (Axis/Hikvision/Hanwha/Vivotek/Milestone/Genetec…) 标准模式：原始鱼眼 O、单全景 1P、双 180° 全景 2P、四分屏 4R(4×~90° 虚拟透视)、ePTZ。要点：

- 厂商自己的**在机分析 (含人数统计) 大多直接跑在原始鱼眼图上**;全景/四分屏主要是给人看的。
- 面向"通用检测模型"的文献结论：**圆柱/全景展开 > 直线透视**(保 FOV，汽车域 +4 mAP 级别);**多路虚拟透视**能让行人外观最接近 COCO 训练分布。
- 全景展开的固有缺陷：天顶 (正下方) 拉丝、0°/360° 接缝会切人 (需重叠边 + 跨缝 NMS)。

## 4. 不矫正、直接在鱼眼上检测的路线

RAPiD(旋转框行人检测，CVPR-W 2020):摆拍数据集 AP50 96%+,但真实场景 WEPDTOF 掉到 ~72%;**许可证禁止商用**、停止维护。后继:LOAF 数据集 + 检测器 (ICCV 2023)、PDAT(2025，先转全景再检测)。
**选择 dewarp 的理由**:现成计数模型即插即用、下游 tracking/ReID 全按直立人设计、固定 LUT 后 dewarp 开销几乎为零、无许可证风险。

## 5. 边缘端运行时

- `cv2.remap` + 预计算 **CV_16SC2 定点 LUT**(`cv2.convertMaps`),把检测器输入分辨率直接折叠进 LUT(remap 成本随小输出、不随大输入)。
- 实测参考:Jetson AGX Orin CPU 1080p remap ≈ 9ms(满频 5ms),CUDA ≈ 2.5ms;RK3588 级 A76 预估 5–15ms@1080p;树莓派 GPU 方案 (remapvid)1080p 25–30fps。
- 硬件 dewarp:Rockchip ISP **FEC** 网格 LUT(RV1126/RK3588,RGA 不能做网格 warp)、NVIDIA **VPI LDC/Remap**(可跑 VIC 定点引擎，零 CPU/GPU 占用)、Ambarella IPC SoC 内置 dewarp 引擎。**先用可移植 remap,profiling 不达标再上平台加速。**

## 6. 可复用开源

GeoCalib(cvg/GeoCalib)、OpenCV fisheye/omnidir、dscamera(双球模型参考实现)、FisheyeWarping / unWrap(顶装全景展开)、fisheye_window(虚拟 PTZ 模板)、RAPiD(仅供基准，禁商用)。**没有现成的端到端"监控鱼眼自动校准+dewarp"开源方案，需自行组装**——本项目即是。

## 关键引用

- OpenCV fisheye (Kannala-Brandt): https://docs.opencv.org/4.x/db/d58/group__calib3d__fisheye.html
- 自动校准专利 (流程参考): https://patents.google.com/patent/US11699216
- Rosten & Loveland plumb-line: https://arxiv.org/abs/0810.4426
- GeoCalib: https://github.com/cvg/GeoCalib · AnyCalib: https://arxiv.org/pdf/2503.12701
- RAPiD: https://arxiv.org/abs/2005.11623 · WEPDTOF: https://vip.bu.edu/projects/vsns/cossy/datasets/wepdtof/
- BU 顶装鱼眼行人检测综述 (2024): https://www.frontiersin.org/journals/imaging/articles/10.3389/fimag.2024.1387543/full
- 圆柱 vs 直线透视 mAP 对比：https://pmc.ncbi.nlm.nih.gov/articles/PMC12196831/
- NVIDIA VPI LDC: https://docs.nvidia.com/vpi/algo_ldc.html · Rockchip RGA 限制：https://github.com/airockchip/librga/blob/main/docs/Rockchip_Developer_Guide_RGA_EN.md
- Axis dewarp 模式：https://developer.axis.com/vapix/network-video/dewarped-views/
