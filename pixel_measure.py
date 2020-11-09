#-*- coding: UTF-8 -*-
import cv2
import numpy as np
from loguru import logger  # 日志控件
class PixelMeasure():
    last_measurement = current_measurement = np.array((2, 1), np.float32)#移动坐标存储容器
    isOneClick=True#事件控制器
    pixelNumber=0#像素值



    '''
        测量计算
    '''
    def saveMark(self,saveType,x, y):
        self.last_measurement = self.current_measurement# 把当前测量存储为上一次测量
        self.current_measurement = np.array([[np.float32(x)], [np.float32(y)]])# 当前测量
        self.kalman.correct(self.current_measurement)# 用当前测量来校正卡尔曼滤波器
        lmx, lmy = self.last_measurement[0], self.last_measurement[1]# 上一次测量坐标
        cmx, cmy = self.current_measurement[0], self.current_measurement[1]# 当前测量坐标
        if saveType==1:
            cv2.line(self.frame, (lmx, lmy), (cmx, cmy), (255, 0, 0),1,cv2.LINE_AA) # 绘制
            self.pixelNumber=((lmx-cmx)**2+(lmy-cmy)**2)**0.5#计算像素值
        elif saveType==2:
            cv2.line(self.frame, (lmx, lmy), (cmx, cmy), (255, 0, 0),1,cv2.LINE_AA)

    '''
	    定义鼠标回调函数，用来绘制跟踪结果
    '''
    def mousemove(self,event, x, y, s, p):
        if (event == cv2.EVENT_LBUTTONDOWN):
            self.isOneClick=False
            self.saveMark(1,x, y)
        elif (event == cv2.EVENT_LBUTTONUP):
            self.saveMark(2,x, y)
        elif (event == cv2.EVENT_RBUTTONDOWN):
            pass
        elif (event == cv2.EVENT_RBUTTONUP):
            logger.info("clean frame")
            self.isOneClick=True
            # picSize=self.rtspThrad.getFramepicSize()
            # frame=self.rtspThrad.getFrameData()

            # frame=cv2.resize(frame,picSize)
            # frame=cv2.resize(frame,picSize)
            try:
                frame = cv2.resize(self.rtspThrad.getFrameData(), self.rtspThrad.getFramepicSize())
                self.frame=frame#取新的一帧来展示
            except BaseException as ex:
                pass
        elif  (event == cv2.EVENT_MOUSEMOVE):
            if self.isOneClick:
                self.saveMark(0,x, y)

    def __init__(self,rtspThrad):
        picSize=rtspThrad.getFramepicSize()
        self.frame = cv2.resize(rtspThrad.getFrameData(), picSize)
        # self.frame = rtspThrad.getFrameData()
        self.rtspThrad = rtspThrad
        cv2.namedWindow("pixel_measure")# 窗口初始化
        cv2.setMouseCallback("pixel_measure", self.mousemove)#鼠标事件
        self.kalman = cv2.KalmanFilter(4, 2) # 4：状态数，包括（x，y，dx，dy）坐标及速度（每次移动的距离）；2：观测量，能看到的是坐标值
        self.kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32) # 系统测量矩阵
        self.kalman.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32) # 状态转移矩阵
        self.kalman.processNoiseCov = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)*0.03 # 系统过程噪声协方差
        while True:
            cv2.imshow("pixel_measure", self.frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('\r'):
                break
        cv2.destroyAllWindows()

    def getpixelNumber(self):
        return self.pixelNumber
