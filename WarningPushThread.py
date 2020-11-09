# -*- coding: UTF-8 -*-
'''
  警告抓捕线程
'''
import time
import threading
from loguru import logger  # 日志控件
from socker import Client_send
import numpy as np
import random
from config import opt
import cv2
from new_socket_connection import Socket_Send_Pic
from Send_HeartBeat import Send_heatbeat
import io


class warningPushThread(threading.Thread):
    def __init__(self, rtspThread, hThread):
        self.rtspThread = rtspThread
        self.hThread = hThread  # 心跳线程
        # self.isLoop = False
        self.normalNumber = 0
        self.warningNumber = 0
        self.pushPicNumber = 0
        threading.Thread.__init__(self)

    def run(self):
        while True:  # 直接开始处理
            # self.isLoop = True
            count = 0
            self.normalNumber = 0
            self.warningNumber = 0

            while count < int(opt.__dict__['push_time']) * 60:
                time.sleep(1)
                count += 1
            # logger.info(self.warningNumber)
            # logger.info(self.normalNumber)
            allNumber = self.warningNumber + self.normalNumber
            if allNumber > int(opt.__dict__['Alarm_All_Tag_number']):  # 一分钟内如果样本帧少于60帧说明视频出现了问题,不考虑遮挡效果
                if self.warningNumber * 100 / allNumber > int(opt.__dict__['proportion']):
                    if self.pushPicNumber >= int(opt.__dict__['Alarm_Push_Time']):  # 如果报警大于半个小时
                        self.pushWarning()
                        pass
                    if self.pushPicNumber is 0:  # 第一次报警
                        self.pushWarning()
                    self.pushPicNumber = self.pushPicNumber + 1
                    self.hThread.changHeartType(1)
                    logger.info('靶标不在摄像机视线内，请检查！')
                    # data = {'msgType': 1,
                    #         'device': '1',
                    #         'status': 2,
                    #         'time': np.long(time.strftime('%Y%m%d%H%M%S')) * 1000}
                    # try:
                    #     Client_send(data)
                    # except Exception as Error:
                    #     logger.info('Error:' + str(Error))
                else:
                    if self.pushPicNumber is not 0:  # 还原报警
                        logger.info("靶标已经还原...")
                        self.pushWarning()
                        pass
                    self.pushPicNumber = 0
                    self.hThread.changHeartType(0)
            else:
                if self.pushPicNumber is not 0:  # 还原报警
                    logger.info("靶标已经还原...")
                    self.pushWarning()
                    pass
                self.pushPicNumber = 0
                self.hThread.changHeartType(0)

            # self.isLoop = False
            pass

    def pushWarning(self):
        now_time = time.time()
        local_time = time.localtime(now_time)
        frame = self.rtspThread.getFrameData()
        if frame is not None:
            data_head = time.strftime("%Y%m%d%H%M%S", local_time)
            data_secs = (now_time - np.long(now_time)) * 1000
            time_stamp = "%s%03d" % (data_head, data_secs)
            time_stamp = int(time_stamp)

            pic_name = opt.__dict__['file_path'] + '/' + str(time_stamp) + '_error.jpg'
            imagPic = cv2.resize(frame.copy(), self.rtspThread.getFramepicSize())
            cv2.imwrite(pic_name, imagPic)

            try:
                th3 = Socket_Send_Pic(self.rtspThread.getFramepicSize(), opt.__dict__['host'],
                                      int(opt.__dict__['port']), pic_name,
                                      -1,
                                      time_stamp)
                th3.start()
                th3.join()  # 图片发送的线程必须要等待

            except Exception as Error:
                logger.error('上传图片出现问题：:' + str(Error))
        else:
            logger.info('未获取到报警帧,未保存图片数据...')

    # 添加正常数
    def addNormal(self):
        # if self.isLoop:
        self.normalNumber = self.normalNumber + 1

    pass

    # 添加警告数
    def addWarning(self):
        # if self.isLoop:
        self.warningNumber = self.warningNumber + 1
    pass

    # def isLoopeStop(self):
    #     return self.isLoop


if __name__ == '__main__':
    with io.open('config.txt', 'r', encoding='utf-8') as f:  # 读取配置文件内容
        for line in f.readlines():
            if not line.startswith('#'):
                name = line.split('=')[0]
                key = line.split('=')[-1].split('\n')[0]
                item = {name: key}
                opt._parse(item)

    th2 = Send_heatbeat(None)  # 心跳
    wpt = warningPushThread(None, th2)
    th2.start()
    wpt.start()

    i = 0
    while i < 100:
        wpt.addWarning()
        i = i + 1
        pass

    pass
