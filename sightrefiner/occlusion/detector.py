import cv2
import numpy as np
import matplotlib.pyplot as plt


def ComplexityDetector(frame, size=(160, 120), super_pixel_set=(12, 9)):
    """ComplexityDetector
    Input:
        Required:(but you do not necessarily need to use)
            frame
            size
            super_pixel_set
        Optinal: (please set a default value)
            ...
    Output:
        score within 0 and 1
    """

    # resize
    frame = cv2.resize(frame, size)

    # channel extraction
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    ch1, ch2, ch3 = cv2.split(frame)
    # ch3 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame = cv2.GaussianBlur(ch3, (5, 5), 0)

    # edge detection
    sobelX = cv2.Sobel(frame, cv2.CV_16S, 1, 0, ksize=3)
    sobelY = cv2.Sobel(frame, cv2.CV_16S, 0, 1, ksize=3)
    absX = cv2.convertScaleAbs(sobelX)  # 转回uint8
    absY = cv2.convertScaleAbs(sobelY)
    dst = cv2.addWeighted(absX, 0.5, absY, 0.5, 0)

    # print(dst)
    # thresholding
    ret, thresh = cv2.threshold(dst, 50, 1, cv2.THRESH_BINARY)
    # cv2.imshow("thresh",thresh)
    # cv2.waitKey(-1)

    # super pixel setting
    w_num_pixel = size[0] / super_pixel_set[0]
    h_num_pixel = size[1] / super_pixel_set[1]
    score_mat = np.zeros(super_pixel_set[::-1])
    for w in range(super_pixel_set[0]):
        for h in range(super_pixel_set[1]):
            score = np.mean(
                thresh[
                    round(h_num_pixel * h) : round(h_num_pixel * (h + 1)),
                    round(w_num_pixel * w) : round(w_num_pixel * (w + 1)),
                ]
            )
            score_mat[h, w] = score
    # print(score_mat)
    # divider = np.std(score_mat) * 6
    # score = (np.max(score_mat)-np.min(score_mat))/divider if divider > 0 else 1
    divider = np.mean(score_mat) * 2
    score = np.std(score_mat) / divider if divider > 0 else 1
    # print(score)
    return min(1, score)


def DistEntropy(data, bins=8, data_range=(0, 128), penalty_func=np.sqrt):
    _range = max(data) - min(data)
    _cnt = len(data)
    bin_width = (_range + 1) / bins
    bin_cnt = [0] * bins
    for d in data:
        bin_cnt[min(bins - 1, int((d - min(data)) / bin_width))] += 1
    penalty = min(1, penalty_func(_range / (data_range[1] - data_range[0])))
    print(bin_cnt, penalty)
    dist_entro = 0
    for _this in range(len(bin_cnt) - 1):
        for _that in range(_this + 1, len(bin_cnt)):
            dist_entro += abs(bin_cnt[_this] - bin_cnt[_that]) / _cnt * (_that - _this)
    dist_entro /= bins - 1
    dist_entro *= penalty
    return dist_entro


def FragmentDetector(frame, size=(160, 120), super_pixel_set=(8, 6)):
    # resize
    frame = cv2.resize(frame, size)

    # channel extraction
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    ch1, ch2, ch3 = cv2.split(frame)
    frame = cv2.GaussianBlur(ch3, (5, 5), 0)

    # edge detection
    sobelX = cv2.Sobel(frame, cv2.CV_16S, 1, 0, ksize=3)
    sobelY = cv2.Sobel(frame, cv2.CV_16S, 0, 1, ksize=3)
    absX = cv2.convertScaleAbs(sobelX)  # 转回uint8
    absY = cv2.convertScaleAbs(sobelY)
    dst = cv2.addWeighted(absX, 0.5, absY, 0.5, 0)

    # thresholding
    ret, thresh = cv2.threshold(dst, 50, 255, cv2.THRESH_BINARY)
    # cv2.imshow("thresh", thresh)

    # super pixel setting
    w_num_pixel = size[0] / super_pixel_set[0]
    h_num_pixel = size[1] / super_pixel_set[1]
    score_mat = np.zeros(super_pixel_set[::-1])
    for w in range(super_pixel_set[0]):
        for h in range(super_pixel_set[1]):
            score = np.max(
                thresh[
                    round(h_num_pixel * h) : round(h_num_pixel * (h + 1)),
                    round(w_num_pixel * w) : round(w_num_pixel * (w + 1)),
                ]
            )
            score_mat[h, w] = score
    score_mat = score_mat.astype(np.uint8)

    vert_feature = np.mean(score_mat, axis=0)
    hori_feature = np.mean(score_mat, axis=1)
    radius_feature = []
    for r in range(int(min(super_pixel_set) / 2)):
        top = score_mat[r, r : (-1 - r)].tolist()
        right = score_mat[r : (-1 - r), -1 - r].tolist()
        down = score_mat[-1 - r][::-1][r : (-1 - r)].tolist()
        left = score_mat[:, r][::-1][r : (-1 - r)].tolist()
        radius_feature.append(np.mean(top + right + left))
        radius_feature.append(np.mean(down + right + left))

    print(DistEntropy(vert_feature), DistEntropy(hori_feature), DistEntropy(radius_feature))
    print(DistEntropy(vert_feature) + DistEntropy(hori_feature) + DistEntropy(radius_feature))

    cv2.imshow("blur", score_mat)
    cv2.waitKey(0)
    plt.subplot(1, 3, 1)
    plt.hist(vert_feature, bins=8)
    plt.ylim(0, 8)
    plt.subplot(1, 3, 2)
    plt.hist(hori_feature, bins=8)
    plt.ylim(0, 8)
    plt.subplot(1, 3, 3)
    plt.hist(radius_feature, bins=8)
    plt.ylim(0, 8)
    plt.show()
    print(vert_feature, hori_feature, radius_feature, sep="\n")

    # vert_score = abs(vert_feature[0]-vert_feature[-1])/np.max(vert_feature) \
    #     if np.max(vert_feature) > 0 else 1
    # hori_score = abs(hori_feature[0]-hori_feature[-1])/np.max(hori_feature) \
    #     if np.max(hori_feature) > 0 else 1
    # radius_score = abs(radius_feature[0]-radius_feature[-1])/np.max(radius_feature) \
    #     if np.max(radius_feature) > 0 else 1

    vert_score = Entropy(vert_binning)
    hori_score = Entropy(hori_binning)
    radius_score = Entropy(radius_binning)
    score_list = [vert_score, hori_score, radius_score]
    score = (max(score_list) / min(score_list) - 1 if min(score_list) > 0 else 1) * complex_flag
    print(score_list)
    # print(score)

    return min(1, score)


if __name__ == "__main__":
    frame = cv2.imread("../data/Occluded/648.jpg")
    # frame = cv2.imread('../data/Exposed/793.jpg')
    # score = FragmentDetector(frame)
    score = ComplexityDetector(frame)
    print(score)
