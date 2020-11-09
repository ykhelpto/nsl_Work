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
import colorList


class RtspConnection(threading.Thread):
    isRunThread = True
    nowRGBFrame = None
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
        logger.info("width:%s,height:%s,fps:%s" % (width, height, fps))
        logger.info('codec is ' + chr(codec & 0xFF) + chr((codec >> 8) & 0xFF) + chr((codec >> 16) & 0xFF) + chr(
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
                        continue
                    self.lock.acquire()
                    self.nowRGBFrame = frame
                    self.lock.release()
                else:  # 在内存爆满后,多次溢出状态下会导致rtsp流中断需再次连接
                    logger.info("视频流帧拉取失败,正在重新连接...")
                    self.lock.acquire()
                    self.nowRGBFrame = None
                    self.lock.release()
                    time.sleep(3)
                    self.cap = cv2.VideoCapture(self.ip_camera_url)
                    width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # 获取视频的宽度
                    height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # 获取视频的高度
                    fps = self.cap.get(cv2.CAP_PROP_FPS)  # 获取视频的帧率
                    codec = int(self.cap.get(cv2.CAP_PROP_FOURCC))  # 视频的编码
                    self.picSize = (int(width / self.narrow), int(height / self.narrow))
                    self.actualSize = (int(width), int(height))
                    logger.info("width:%s,height:%s,fps:%s" % (width, height, fps))
                    logger.info(
                        'codec is ' + chr(codec & 0xFF) + chr((codec >> 8) & 0xFF) + chr((codec >> 16) & 0xFF) + chr(
                            (codec >> 24) & 0xFF))
            else:  # 未启动时1s后再次连接
                logger.info('\033[1;31m请检查IP地址还有端口号，或者查看IP摄像头是否开启\033[0m')
                data = {'msgType': 1,
                        'device': '1',
                        'status': 1,
                        'time': np.long(time.strftime('%Y%m%d%H%M%S')) * 1000}
                try:
                    Client_send(data)
                except Exception as Error:
                    pass
                logger.info("视频流启动失败,正在重新连接...")
                self.lock.acquire()
                self.nowRGBFrame = None
                self.lock.release()
                time.sleep(3)
                self.cap = cv2.VideoCapture(self.ip_camera_url)
                width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # 获取视频的宽度
                height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # 获取视频的高度
                fps = self.cap.get(cv2.CAP_PROP_FPS)  # 获取视频的帧率
                codec = int(self.cap.get(cv2.CAP_PROP_FOURCC))  # 视频的编码
                self.picSize = (int(width / self.narrow), int(height / self.narrow))
                self.actualSize = (int(width), int(height))
                logger.info("width:%s,height:%s,fps:%s" % (width, height, fps))
                logger.info(
                    'codec is ' + chr(codec & 0xFF) + chr((codec >> 8) & 0xFF) + chr((codec >> 16) & 0xFF) + chr(
                        (codec >> 24) & 0xFF))
        cv2.destroyAllWindows()
        logger.info('视频流连接已经断开...')

    '''
	    线程控制器
    '''

    def stopThread(self):
        self.isRunThread = False

    '''
	    获取线程缓存的最新的帧RGB图片
    '''

    def getFrameData(self):
        self.lock.acquire()
        if self.nowRGBFrame is not None:
            # frame = cv2.resize(self.nowRGBFrame.copy(), self.picSize)
            frame = self.nowRGBFrame.copy()
            self.lock.release()
            return frame
        else:
            self.lock.release()
            return None

    '''
    获取最新的Gray图片
    '''

    def getGrayFrameData(self):
        self.lock.acquire()
        if self.nowRGBFrame is not None:
            # frame = cv2.resize(self.nowRGBFrame.copy(), self.picSize)
            frame = self.nowRGBFrame.copy()
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.lock.release()
            return gray_frame
        else:
            self.lock.release()
            return None

    def getHSVFrameData(self):
        self.lock.acquire()
        if self.nowRGBFrame is not None:

            # frame = cv2.resize(self.nowRGBFrame.copy(), self.picSize)
            frame = self.nowRGBFrame.copy()
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            self.lock.release()
            return gray_frame
        else:
            self.lock.release()
            return None

    # 注意这里是建议展示缩放尺寸比例
    def getFramepicSize(self):
        return self.picSize

    # 实际展示尺寸
    def getFrameActualpicSize(self):
        return self.actualSize

    def videoIsNight(self):
        return self.isNight
