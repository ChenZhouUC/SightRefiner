"""遮挡检测示例程序"""

import os
import cv2
import numpy as np
import configparser
from sightrefiner.utils import ConfigLoader, TopicValueExtractor
from sightrefiner.occlusion import ComplexityDetector, ROCMetrics, HardCaseMining


def load_config(config_root="./data/occlusion/", config_file="config.conf"):
    """加载配置文件"""
    config_parser = configparser.ConfigParser()
    config_parser = ConfigLoader(config_root, config_file, config_parser)

    print(
        "ProblemSummary",
        "Description",
        TopicValueExtractor(config_parser, "ProblemSummary", "Description"),
        sep=" ==> ",
    )

    # 定义数据和标签
    labeled_dict = {}
    label_exposed = int(TopicValueExtractor(config_parser, "LabelDefinition", "Exposed"))
    repo_exposed = TopicValueExtractor(config_parser, "DataLoader", "ExposedRepo")
    label_occluded = int(TopicValueExtractor(config_parser, "LabelDefinition", "Occluded"))
    repo_occluded = TopicValueExtractor(config_parser, "DataLoader", "OccludedRepo")

    labeled_dict[label_exposed] = [
        os.path.join(config_root, repo_exposed, d) for d in os.listdir(os.path.join(config_root, repo_exposed))
    ]
    labeled_dict[label_occluded] = [
        os.path.join(config_root, repo_occluded, d) for d in os.listdir(os.path.join(config_root, repo_occluded))
    ]

    return labeled_dict


def evaluation_process(
    labeled_dict,
    size=(150, 100),
    super_pixel_set=(15, 10),
    pos_label=1,
    saving_output=True,
    hard_case_top_n=10,
    plot_save_name="ROC_Metrics.png",
):
    """评估过程"""
    label_series = []
    prob_series = []
    case_series = {}

    for label in labeled_dict.keys():
        print(f"...处理标签: {label} ...")
        tmp_label = []
        tmp_prob = []

        for data in labeled_dict[label]:
            tmp_label.append(label)
            frame = cv2.imread(data)
            tmp_prob.append(ComplexityDetector(frame, size, super_pixel_set))

        label_series.extend(tmp_label)
        prob_series.extend(tmp_prob)

        if label == pos_label:
            case_series["pos"] = {"case": labeled_dict[label], "prob": tmp_prob}
        else:
            case_series["neg"] = {"case": labeled_dict[label], "prob": tmp_prob}

    # 困难样本挖掘和 ROC 指标计算
    pos_hc = HardCaseMining(case_series["pos"]["case"], case_series["pos"]["prob"], "pos", topN=hard_case_top_n)
    neg_hc = HardCaseMining(case_series["neg"]["case"], case_series["neg"]["prob"], "neg", topN=hard_case_top_n)
    auc_metrics = ROCMetrics(
        label_series, prob_series, posLabel=pos_label, saving=saving_output, plotSaveName=plot_save_name
    )

    return auc_metrics, pos_hc, neg_hc


def show_hard_cases(hc_result, hc_type, show_size=(600, 400)):
    """显示困难样本"""
    hc_list, hc_score = hc_result
    text_color = (0, 255, 0) if hc_type == "NEGATIVE" else (0, 0, 255)

    for idx, hc in enumerate(hc_list):
        hc_frame = cv2.imread(hc)
        hc_frame = cv2.resize(hc_frame, show_size)
        cv2.putText(hc_frame, str(round(hc_score[idx], 2)), (0, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)
        cv2.imshow(hc_type, hc_frame)
        cv2.waitKey(0)

    print(f"{len(hc_list)} 个困难样本（{hc_type}）已显示...")
    cv2.destroyWindow(hc_type)


if __name__ == "__main__":
    # 加载配置
    labeled_dict = load_config()

    # 执行评估
    auc_metrics, pos_hc, neg_hc = evaluation_process(
        labeled_dict, hard_case_top_n=20, size=(160, 120), super_pixel_set=(12, 9), plot_save_name="ROC_Metrics.png"
    )

    # 输出结果
    print("=" * 60)
    print(f"|    AUC Metrics 得到: {round(auc_metrics, 5)}    |")
    print("=" * 60)

    # 显示困难样本
    show_hard_cases(pos_hc, "POSITIVE")
    show_hard_cases(neg_hc, "NEGATIVE")
