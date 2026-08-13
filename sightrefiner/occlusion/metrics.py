import os
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


def _compute_roc_curve(labels, scores, pos_label=1):
    """计算 ROC 曲线的 FPR, TPR 和阈值"""
    labels = np.array(labels)
    scores = np.array(scores)

    # 获取所有唯一的阈值（降序）
    thresholds = np.sort(np.unique(scores))[::-1]

    fpr_list = []
    tpr_list = []

    for thresh in thresholds:
        predictions = (scores >= thresh).astype(int) * pos_label

        # 计算 TP, FP, TN, FN
        tp = np.sum((predictions == pos_label) & (labels == pos_label))
        fp = np.sum((predictions == pos_label) & (labels != pos_label))
        tn = np.sum((predictions != pos_label) & (labels != pos_label))
        fn = np.sum((predictions != pos_label) & (labels == pos_label))

        # 计算 FPR 和 TPR
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0

        fpr_list.append(fpr)
        tpr_list.append(tpr)

    return np.array(fpr_list), np.array(tpr_list), thresholds


def _compute_auc(fpr, tpr):
    """使用梯形法则计算 AUC"""
    return np.trapz(tpr, fpr)


def ROCMetrics(
    labelSeries, probSeries, posLabel=1, saving=False, plotSaveName="ROC_Metrics.png", fprThresh=0.05, tprThresh=0.9
):
    fpr, tpr, thresholds = _compute_roc_curve(labelSeries, probSeries, pos_label=posLabel)
    auc_metrics = _compute_auc(fpr, tpr)

    x_f, y_f = 0, 0
    x_t, y_t = 0, 0
    for _idx_f, f in enumerate(fpr):
        if f > fprThresh:
            x_f = fpr[max(0, _idx_f - 1)]
            y_f = tpr[max(0, _idx_f - 1)]
            break
    for _idx_t, t in enumerate(tpr):
        if t >= tprThresh:
            x_t = fpr[_idx_t]
            y_t = tpr[_idx_t]
            break
    line_f = [(x_f, 0), (x_f, y_f)]
    line_t = [(0, y_t), (x_t, y_t)]
    # print(line_f, line_t)
    (linef_xs, linef_ys) = zip(*line_f)
    (linet_xs, linet_ys) = zip(*line_t)

    # depict the ROC metrics
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, label="ROC Curve", linewidth=2)
    ax.plot(fpr, thresholds, label="Thresholds", linewidth=2)
    ax.add_line(Line2D(linef_xs, linef_ys, linewidth=2, color="blue", linestyle=":"))
    ax.add_line(Line2D(linet_xs, linet_ys, linewidth=2, color="red", linestyle=":"))
    ax.legend()
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.xlabel("FPR")
    plt.ylabel("TPR")
    plt.title("ROC Curve | AUC=" + str(round(auc_metrics, 2)))
    if saving:
        os.makedirs("./plots", exist_ok=True)
        plt.savefig(os.path.join("./plots", plotSaveName))
    plt.show()

    return auc_metrics


def HardCaseMining(caseSeries, scoreSeries, flag, topN=10):
    if flag == "pos":
        flag = 1
    else:
        flag = -1
    idx = np.argsort(flag * np.array(scoreSeries))[:topN]
    return np.array(caseSeries)[idx], np.array(scoreSeries)[idx]


if __name__ == "__main__":
    labelSeries = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
    probSeries = np.array([0.1, 0.4, 0.4, 0.3, 0.5, 0.4, 0.6, 0.7, 0.8, 0.5])  # probability of prediction as positive

    ROCMetrics(labelSeries, probSeries)
