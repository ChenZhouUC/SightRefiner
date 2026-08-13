"""鱼眼矫正示例程序"""

import cv2
from sightrefiner.fisheye import auto_profile, build_maps, save_maps, Dewarper


def demo_calibration(image_path, camera_id="demo_cam"):
    """演示自动校准流程"""
    print(f"正在处理图像: {image_path}")

    # 读取鱼眼图像
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"错误: 无法读取图像 {image_path}")
        return None

    print("开始自动校准...")
    # 自动检测成像圆并生成配置文件
    profile = auto_profile(frame, camera_id=camera_id)

    # 保存配置文件（JSON 格式，人类可读）
    profile_path = f"{camera_id}_profile.json"
    profile.to_json(profile_path)
    print(f"配置文件已保存: {profile_path}")

    # 烘焙查找表（LUT）用于边缘端快速处理
    lut_path = f"{camera_id}_luts.npz"
    save_maps(build_maps(profile), lut_path)
    print(f"LUT 文件已保存: {lut_path}")

    return profile, lut_path


def demo_dewarp(image_path, lut_path):
    """演示图像矫正流程"""
    print(f"\n正在使用 LUT 矫正图像: {image_path}")

    # 读取图像
    frame = cv2.imread(image_path)
    if frame is None:
        print(f"错误: 无法读取图像 {image_path}")
        return

    # 加载 Dewarper（边缘端只需这一步）
    dw = Dewarper(lut_path)

    # 处理图像
    outputs = dw.process(frame)

    # 保存结果
    for view_name, output_img in outputs.items():
        output_path = f"output_{view_name}.png"
        cv2.imwrite(output_path, output_img)
        print(f"矫正结果已保存: {output_path} (尺寸: {output_img.shape})")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python fisheye_demo.py <鱼眼图像路径>")
        print(
            "示例: python fisheye_demo.py ../data/fisheye/batches/2026-08-10_pilot_camera_scrnsht/images/310_34th_St_cam01.png"
        )
        sys.exit(1)

    image_path = sys.argv[1]
    camera_id = "demo_camera"

    # 步骤 1: 自动校准
    print("=" * 60)
    print("步骤 1: 自动校准")
    print("=" * 60)
    profile, lut_path = demo_calibration(image_path, camera_id)

    if profile is None:
        sys.exit(1)

    # 步骤 2: 图像矫正
    print("\n" + "=" * 60)
    print("步骤 2: 图像矫正")
    print("=" * 60)
    demo_dewarp(image_path, lut_path)

    print("\n完成！")
