# -*- coding: UTF-8 -*-
'''
帧角点获取
'''
import threading
import cv2
from config import opt
import time
import numpy as np
from loguru import logger  # 日志控件

class FrameCornersObtain(threading.Thread):
    corners = None

    def __init__(self, rtspThrad, left, right):
        self.rtspThrad = rtspThrad
        self.left = left
        self.right = right
        threading.Thread.__init__(self)

    def run(self):
        self.initGetCorners()

    '''
        思路:初始化的时候就直接循环同步获取角点情况
            微弱抖动矫正
    '''

    def initGetCorners(self):
        while True:
            frame = self.rtspThrad.getFrameData()
            gray_frame = self.rtspThrad.getGrayFrameData()
            if frame is not None and gray_frame is not None:
                feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
                p = cv2.goodFeaturesToTrack(gray_frame, mask=None, **feature_params)
                nowCorners = []
                for i, point in enumerate(p):
                    [[x, y]] = point
                    if self.left[0] < x < self.right[0] and self.left[1] < y < self.right[1]:
                        nowCorners.append([[np.float32(x), np.float32(y)]])
                nowCorners = np.array(nowCorners)
                if nowCorners.shape == (0,):
                    logger.info('请重新标定靶标！')
                    time.sleep(5)
                else:
                    if self.corners is not None:
                        if (self.corners == nowCorners).all():
                            pass
                        else:
                            self.corners = nowCorners
                            point_frame = cv2.circle(frame, (x, y), 3, (0, 0, 255), 1)
                            cv2.rectangle(point_frame, (int(self.left[0]), (int(self.left[1]))),
                                          (int(self.right[0]), int(self.right[1])), (255, 255, 0), 3)
                            cv2.imwrite(opt.__dict__['file_path'] + '/' + str(
                                time.strftime('%Y-%m-%d-%H-%M-%S')) + '_point' + '.jpg', point_frame)
                    else:
                        self.corners = nowCorners
                        point_frame = cv2.circle(frame, (x, y), 3, (0, 0, 255), 1)
                        cv2.rectangle(point_frame, (int(self.left[0]), (int(self.left[1]))),
                                      (int(self.right[0]), int(self.right[1])), (255, 255, 0), 3)
                        cv2.imwrite(opt.__dict__['file_path'] + '/' + str(
                            time.strftime('%Y-%m-%d-%H-%M-%S')) + '_point' + '.jpg', point_frame)

