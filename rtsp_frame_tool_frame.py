# -*- coding: UTF-8 -*-
'''
 rtsp  帧处理线程
        22帧



'''
import cv2
import threading
from loguru import logger  # 日志控件
import colorList
from TypeRefreshThread import typeRefreshThread
import time


class RtspFrameToolFrame(threading.Thread):
    isRunThread = True
    nowRGBFrame = None
    GrayFrame = None
    trackerFrame = None
    trackerHSVFrame = None
    picSize = 0
    actualSize = 0
    isNight = 0

    def __init__(self, rtspConnectionThrad):
        self.tct = rtspConnectionThrad
        self.lock = threading.Lock()
        threading.Thread.__init__(self)

    def run(self):
        while self.isRunThread:
            frame = self.tct.getFrameData()
            self.picSize = self.tct.getFramepicSize()
            self.actualSize = self.tct.getFrameActualpicSize()
            if frame is None:
                self.lock.acquire()
                self.nowRGBFrame = None
                self.GrayFrame = None
                self.trackerFrame = None
                self.trackerHSVFrame = None
                self.lock.release()
            else:
                self.lock.acquire()
                disposeFrame = frame.copy()
                self.nowRGBFrame = disposeFrame
                self.GrayFrame = cv2.cvtColor(disposeFrame, cv2.COLOR_BGR2GRAY)
                self.trackerFrame = cv2.resize(disposeFrame, self.picSize)
                self.trackerHSVFrame = cv2.cvtColor(self.trackerFrame, cv2.COLOR_BGR2HSV)
                self.lock.release()
            pass
        logger.error('视频流帧处理线程关闭...')

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

    def getTrackerFrameData(self):
        return self.trackerFrame

    def gettrackerHSVFrameData(self):
        return self.trackerHSVFrame

    # 注意这里是建议展示缩放尺寸比例
    def getFramepicSize(self):
        return self.picSize

    # 实际展示尺寸
    def getFrameActualpicSize(self):
        return self.actualSize

    def videoIsNight(self):
        return self.isNight
