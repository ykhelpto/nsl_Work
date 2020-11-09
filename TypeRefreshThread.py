# -*- coding: UTF-8 -*-
'''
  状态刷新线程

'''
import time
import threading
from loguru import logger  # 日志控件
from socker import Client_send
import numpy as np
import random
from config import opt
import cv2


class typeRefreshThread(threading.Thread):

    def __init__(self):
        self.refreshNumber = 0
        self.isLoop = False
        threading.Thread.__init__(self)

    def run(self):
        while (True):
            while self.refreshNumber > 0:
                self.isLoop = True
                time.sleep(1)
                self.refreshNumber = self.refreshNumber - 1
            if self.isLoop:
                self.isLoop = False
                logger.info("缓冲完毕,正在启动算法识别...")
            else:
                pass
            pass

    '''
        更新循环状态
    '''

    def refreshLoop(self):
        self.refreshNumber = int(opt.__dict__['change_night_time'])

    '''
        循环是否在进行
    '''
    def getRefreshISLoop(self):
        return self.isLoop
