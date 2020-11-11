# -*- coding: UTF-8 -*-
import threading
import time
import os
from socker import Client_send
from config import opt
import numpy as np
from loguru import logger  # 日志控件

lock = threading.Lock()


# 移除近一个月的图片数据：
def remove_jpgs():
    if str(time.strftime('%d-%H-%M-%S')) == '01-00-00-01':
        logger.warning('\033[1;31m一个月已到，正在删除文件夹中的文件....\033[0m')
        for i in os.listdir(opt.__dict__['file_path']):
            jpg_file = os.path.join(opt.__dict__['file_path'], i)
            if os.path.isfile(jpg_file):
                os.remove(jpg_file)
        logger.warning('\033[1;31m 删除完毕！\033[0m')
    else:
        pass


class Send_heatbeat(threading.Thread):
    def __init__(self, rtspConnect):
        self.isThread = True
        self.rtspConnect = rtspConnect
        self.heartType = 0
        threading.Thread.__init__(self)

    def run(self):
        while (self.isThread):
            # 发送心跳信息
            time.sleep(60)
            videoFrame = self.rtspConnect.getFrameData()  # 获取视频流工具类中的视频帧状态,如果视频帧为null 那么就认为是设备离线状态
            data = None
            if videoFrame is None:  # 断网心跳 这个断网心跳可能包含 切换黑白天状态的时候的心跳
                data = {'msgType': 1,
                        'device': '1',
                        'status': 1,
                        'time': np.long(time.strftime('%Y%m%d%H%M%S')) * 1000}
                logger.warning('------上传断网心跳-------')
            else:
                if self.heartType is 0:  # 正常心跳
                    data = {'msgType': 1,
                            'device': '1',
                            'status': 0,
                            'time': np.long(time.strftime('%Y%m%d%H%M%S')) * 1000}
                    logger.warning('------上传正常心跳-------')
                elif self.heartType is 1:  # 设备异常(遮挡)心跳

                    data = {'msgType': 1,
                            'device': '1',
                            'status': 2,
                            'time': np.long(time.strftime('%Y%m%d%H%M%S')) * 1000}
                    logger.warning('------上传异常(遮挡)心跳-------')
                else:  # 默认正常心跳
                    data = {'msgType': 1,
                            'device': '1',
                            'status': 0,
                            'time': np.long(time.strftime('%Y%m%d%H%M%S')) * 1000}
                    logger.warning('------上传正常心跳-------')
            try:
                Client_send(data)
            except Exception as Error:
                logger.error(Error)

            try:
                remove_jpgs()
            except Exception as Error:
                logger.error(Error)
        logger.error('心跳线程异常结束....')

    def stopThread(self):
        self.isThread = False

    def changHeartType(self, heartType):
        self.heartType = heartType


if __name__ == '__main__':
    lock = threading.Lock()
    th2 = Send_heatbeat(None)
    th2.start()  # 开启两个线程
    th2.join()
