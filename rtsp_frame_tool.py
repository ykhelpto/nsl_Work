# -*- coding: UTF-8 -*-
'''
 rtsp  视频处理线程
        22帧



'''
import cv2
import threading
from loguru import logger  # 日志控件
import colorList
from TypeRefreshThread import typeRefreshThread
import time


class RtspFrameTool(threading.Thread):
    isRunThread = True

    nowRGBFrame = None
    GrayFrame = None
    # HSVFrame = None
    trackerFrame = None
    picSize = 0
    actualSize = 0
    isNight = False  # 默认是白天数据
    isNightType = -1  # 默认是启动-1状态

    def __init__(self, rtspFrameToolFrame):
        self.rtspFrameToolFrame = rtspFrameToolFrame
        self.lock = threading.Lock()
        self.trt = typeRefreshThread()
        self.trt.start()
        threading.Thread.__init__(self)

    def run(self):
        while self.isRunThread:

            takeHSVFrame = self.rtspFrameToolFrame.gettrackerHSVFrameData()
            if takeHSVFrame is not None:
                self.picSize = self.rtspFrameToolFrame.getFramepicSize()
                self.actualSize = self.rtspFrameToolFrame.getFrameActualpicSize()
                # frame4 = nowFrame.copy()
                if self.findcolor(takeHSVFrame) is 0:
                    if self.isNight:  # 如果是晚上状态 切换到白天
                        self.trt.refreshLoop()
                        self.isNight = False
                        self.isNightType = 1
                        logger.warning("切换监听状态晚上>>>白天,启动视频缓冲请稍后...")

                else:
                    if not self.isNight:  # 如果是白天状态 切换到晚上
                        if self.isNightType is -1:  # 初始化的时候不进行监听
                            logger.warning("正在启动晚上状态请稍后...")
                            self.isNightType = 1
                            self.isNight = True
                            pass
                        else:
                            self.trt.refreshLoop()
                            self.isNight = True
                            self.isNightType = 1
                            logger.info("切换监听状态白天>>>晚上,启动视频缓冲请稍后...")

                if self.trt.getRefreshISLoop():  # 是否在等待视频帧稳定中
                    self.lock.acquire()
                    self.nowRGBFrame = None
                    self.GrayFrame = None
                    self.trackerFrame = None
                    # self.HSVFrame = None
                    self.lock.release()
                    pass
                else:
                    self.lock.acquire()
                    # frame0 = nowFrame.copy()
                    # self.nowRGBFrame=frame0
                    # frame1 = nowFrame.copy()
                    # self.GrayFrame = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                    # # frame2 = nowFrame.copy()
                    # # self.HSVFrame = cv2.cvtColor(frame2, cv2.COLOR_BGR2HSV)
                    # frame3 = nowFrame.copy()
                    # self.trackerFrame = cv2.resize(frame3, self.picSize)

                    # frame0 = nowFrame.copy()
                    self.nowRGBFrame = self.rtspFrameToolFrame.getFrameData()
                    # frame1 = nowFrame.copy()
                    self.GrayFrame = self.rtspFrameToolFrame.getGrayFrameData()
                    # frame2 = nowFrame.copy()
                    # self.HSVFrame = cv2.cvtColor(frame2, cv2.COLOR_BGR2HSV)
                    # frame3 = nowFrame.copy()
                    self.trackerFrame = self.rtspFrameToolFrame.getTrackerFrameData()
                    self.lock.release()

                    pass

                pass
            else:
                self.lock.acquire()
                self.nowRGBFrame = None
                self.GrayFrame = None
                # self.HSVFrame = None
                self.trackerFrame = None
                self.lock.release()
        logger.error('视频流工具帧线程关闭...')

    '''
	    线程控制器
    '''

    def stopThread(self):
        self.isRunThread = False

    '''
	    获取线程缓存的最新的帧RGB图片
    '''

    def getFrameData(self):
        return self.nowRGBFrame

    '''
    获取最新的Gray图片
    '''

    def getGrayFrameData(self):
        return self.GrayFrame

    #
    # def getHSVFrameData(self):
    #     return self.HSVFrame

    def getTrackerFrameData(self):
        return self.trackerFrame

    # 注意这里是建议展示缩放尺寸比例
    def getFramepicSize(self):
        return self.picSize

    # 实际展示尺寸
    def getFrameActualpicSize(self):
        return self.actualSize

    def videoIsNight(self):
        return self.isNight

    # 当前视频状态
    def findcolor(self, takeHSVFrame):

        night = 0
        color_dict = colorList.getColorList()
        # hsv = cv2.cvtColor(cutframe, cv2.COLOR_BGR2HSV)
        maxsum = 0
        color = 'None'
        d = 'red'
        # image = cutframe.copy()
        mask = cv2.inRange(takeHSVFrame, color_dict[d][0], color_dict[d][1])
        # cv2.imwrite(d + '.jpg', mask)
        binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)[1]
        binary = cv2.dilate(binary, None, iterations=2)
        cnts, hiera = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


        # cv2.imshow("lunkuo",aa)
        # cv2.waitKey(1000)

        sum = 0
        for c in cnts:
            sum += cv2.contourArea(c)
        if sum < 100:
            night = 1
        return night
