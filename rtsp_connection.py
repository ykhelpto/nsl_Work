# -*- coding: UTF-8 -*-
'''
 rtsp  连接线程
'''
import cv2
import threading
import time
import numpy as np
from socker import Client_send
from loguru import logger  # 日志控件


class RtspConnection(threading.Thread):
    isRunThread = True
    nowRGBFrame = None
    # GrayFrame = None
    # trackerFrame = None
    # trackerHSVFrame = None
    picSize = 0
    actualSize = 0
    isNight = 0

    def __init__(self, ip_camera_url, narrow):
        self.ip_camera_url = ip_camera_url
        self.cap = cv2.VideoCapture(ip_camera_url)  # 初始化连接rtsp线程
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # 获取视频的宽度
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # 获取视频的高度
        fps = self.cap.get(cv2.CAP_PROP_FPS)  # 获取视频的帧率
        codec = int(self.cap.get(cv2.CAP_PROP_FOURCC))  # 视频的编码
        self.picSize = (int(width / narrow), int(height / narrow))
        self.actualSize = (int(width), int(height))
        logger.warning("width:%s,height:%s,fps:%s" % (width, height, fps))
        logger.warning('codec is ' + chr(codec & 0xFF) + chr((codec >> 8) & 0xFF) + chr((codec >> 16) & 0xFF) + chr(
            (codec >> 24) & 0xFF))
        self.lock = threading.Lock()
        self.narrow = narrow
        threading.Thread.__init__(self)

    def run(self):
        while self.isRunThread:

            if self.cap.isOpened():  # 判断是否连接
                ret, frame = self.cap.read()
                if ret:  # 将帧数据单独放入队列中的第一位,保证缓存中的帧是最新帧
                    if frame is None:
                        self.nowRGBFrame = None
                        # self.lock.acquire()
                        # self.GrayFrame = None
                        # self.trackerFrame = None
                        # self.trackerHSVFrame = None
                        # self.lock.release()
                        continue
                    self.nowRGBFrame = frame
                    # self.lock.acquire()
                    # self.GrayFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    # self.trackerFrame = cv2.resize(frame, self.picSize)
                    # self.trackerHSVFrame = cv2.cvtColor(self.trackerFrame, cv2.COLOR_BGR2HSV)
                    # self.lock.release()
                else:  # 在内存爆满后,多次溢出状态下会导致rtsp流中断需再次连接
                    logger.error("视频流帧拉取失败,正在重新连接...")
                    self.nowRGBFrame = None
                    # self.lock.acquire()
                    # self.GrayFrame = None
                    # self.trackerFrame = None
                    # self.trackerHSVFrame = None
                    # self.lock.release()
                    time.sleep(3)
                    self.cap = cv2.VideoCapture(self.ip_camera_url)
                    width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # 获取视频的宽度
                    height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # 获取视频的高度
                    fps = self.cap.get(cv2.CAP_PROP_FPS)  # 获取视频的帧率
                    codec = int(self.cap.get(cv2.CAP_PROP_FOURCC))  # 视频的编码
                    self.picSize = (int(width / self.narrow), int(height / self.narrow))
                    self.actualSize = (int(width), int(height))
                    logger.warning("width:%s,height:%s,fps:%s" % (width, height, fps))
                    logger.warning(
                        'codec is ' + chr(codec & 0xFF) + chr((codec >> 8) & 0xFF) + chr((codec >> 16) & 0xFF) + chr(
                            (codec >> 24) & 0xFF))
            else:  # 未启动时1s后再次连接
                logger.error('\033[1;31m请检查IP地址还有端口号，或者查看IP摄像头是否开启\033[0m')
                data = {'msgType': 1,
                        'device': '1',
                        'status': 1,
                        'time': np.long(time.strftime('%Y%m%d%H%M%S')) * 1000}
                try:
                    Client_send(data)
                except Exception as Error:
                    pass
                logger.error("视频流启动失败,正在重新连接...")
                self.nowRGBFrame = None
                # self.lock.acquire()
                # self.GrayFrame = None
                # self.trackerFrame = None
                # self.trackerHSVFrame = None
                # self.lock.release()
                time.sleep(3)

                self.cap = cv2.VideoCapture(self.ip_camera_url)
                width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # 获取视频的宽度
                height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # 获取视频的高度
                fps = self.cap.get(cv2.CAP_PROP_FPS)  # 获取视频的帧率
                codec = int(self.cap.get(cv2.CAP_PROP_FOURCC))  # 视频的编码
                self.picSize = (int(width / self.narrow), int(height / self.narrow))
                self.actualSize = (int(width), int(height))
                logger.warning("width:%s,height:%s,fps:%s" % (width, height, fps))
                logger.warning(
                    'codec is ' + chr(codec & 0xFF) + chr((codec >> 8) & 0xFF) + chr((codec >> 16) & 0xFF) + chr(
                        (codec >> 24) & 0xFF))

        cv2.destroyAllWindows()
        logger.error('视频流连接已经断开...')

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

    # def getGrayFrameData(self):
    #     return self.GrayFrame
    #
    # def getTrackerFrameData(self):
    #     return self.trackerFrame
    #
    # def gettrackerHSVFrameData(self):
    #     return self.trackerHSVFrame

    # 注意这里是建议展示缩放尺寸比例
    def getFramepicSize(self):
        return self.picSize

    # 实际展示尺寸
    def getFrameActualpicSize(self):
        return self.actualSize

    def videoIsNight(self):
        return self.isNight
