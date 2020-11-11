# -*- coding: UTF-8 -*-
import threading
import time
from loguru import logger  # 日志控件
from new_optical_flow import OpticalFlow
from Send_HeartBeat import Send_heatbeat

'''
守护线程  定期检测线程是否还在正常运行
'''


class guardTherad(threading.Thread):
    def __init__(self,
                 opticalFlowThreadName,
                 SendHeatbeatThreadName,
                 rtspThrad,
                 SendHeatbeatThread,
                 rtspToolThrad,
                 ip_camera_url,
                 left,
                 right,
                 isOpenVideo,
                 bbox_M):
        self.OTN = opticalFlowThreadName
        self.SHTN = SendHeatbeatThreadName
        self.th2 = SendHeatbeatThread
        self.rtspToolThrad = rtspToolThrad
        self.rtspThrad = rtspThrad  # 添加数据处理线程
        self.ip_camera_url = ip_camera_url
        self.left = left
        self.right = right
        self.bbox_M = bbox_M
        self.isOpenVideo = isOpenVideo
        threading.Thread.__init__(self)

    def run(self):
        while True:
            isOTN = False
            isSHTN = False
            time.sleep(60 * 30)  # 每半个小时检测一次当前线程是否正常
            threads = threading.enumerate()
            for thread in threads:
                # print("\nThread ID: %s, Name: %s\n" % (thread.ident,thread.name))
                if thread.name is self.OTN:
                    isOTN = True
                    pass
                if thread.name is self.SHTN:
                    isSHTN = True
                    pass
            if not isOTN:  # 线程 opticalFlowThread停止运行了
                logger.error("算法线程停止运行了,正在准备恢复")
                th1 = OpticalFlow(self.rtspToolThrad,
                                  self.th2,
                                  self.ip_camera_url,
                                  self.left,
                                  self.right,
                                  self.isOpenVideo,
                                  self.bbox_M)  # 算法
                th1.start()
                self.OTN = th1.getName()
                pass
            if not isSHTN:  # 线程 SendHeatbeat
                logger.error("心跳线程停止运行了,正在准备恢复")
                th2 = Send_heatbeat(self.rtspThrad)  # 心跳
                th2.start()
                self.SHTN = th2.getName()
                self.th2 = th2
                pass
        pass
