# -*- coding: UTF-8 -*-
'''
修改日期：0721
新增需求：要求多线程读取图片，以防出现实时读取延时问题
'''

import io
import cv2
import threading
import numpy as np
import time
import math
from socker import Client_send
from config import opt
from new_socket_connection import Socket_Send_Pic
from sklearn.cluster import KMeans
from loguru import logger  # 日志控件
from WarningPushThread import warningPushThread
from kcf import Tracker

isAlarm = False  # 算法的报警状态
isArrest = False  # 算法的报警状态
pushNumber = 1  # 报警次数

# 监听框移动状态
'''
                # refer_left, refer_right = Target_tracking(self.tracker, trackerFrame, self.left,
                #                                           self.right)  # 目标追踪放在这里，是为了检测图像中是否存在目标

                # (x1, y1) = refer_left
                # (x2, y2) = refer_right
                # (xS, yS) = self.rtspThrad.getFramepicSize()  # 这里比对的是缩放后的尺寸框
                # maxThis = 0
                # if x1 > x2:
                #     maxThis = x1
                #     x1 = x2
                #     x2 = maxThis
                # if y1 > y2:
                #     maxThis = y1
                #     y1 = y2
                #     y2 = maxThis
                # rectXSize = x2 - x1
                # rectYSize = y2 - y1
                # 设定监控包含框体可以完全移除画面的情况
                # if x1 > - rectXSize and x2 < (xS + rectXSize) and y1 > -rectYSize and y2 < (yS + rectYSize):

'''

trackChang = 0  # 位移量



def Target_tracking(tracker, frame, left, right):
    global trackChang
    item = tracker.track(frame)
    message = item.getMessage()
    [((left_x, left_y), (right_x, right_y))] = message['coord']

    if message['msg'] == "Is tracking":
        (delta_x, delta_y) = (left_x - (left[0] / np.int(opt.__dict__['narrow'])), left_y - (left[1] / np.int(
            opt.__dict__['narrow'])))
        dis_left = np.sqrt(delta_x ** 2 + delta_y ** 2)  # 位移距离
        trackChang = dis_left

        # cv2.rectangle(frame, (left_x, left_y), (right_x, right_y), (255, 0, 0), 1, 1)  # 矩形
        # cv2.imshow('pixel_measure', frame)
        # key = cv2.waitKey(1) & 0xFF
        # if key == ord('\r'):
        #     pass
        return True
    elif message['msg'] == "Not tracking":
        # logger.info('\033[1;31m请检查靶标是否在摄像机视线内\033[0m')
        return False
    # return leftl, rightl


lk_params = dict(winSize=(15, 15), maxLevel=2, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))


def corners_tracking(prev_gray, frame_gray, corners, rtspThrad, left, right):
    bias = []
    Tracking_Ok = []
    distance = []
    try:
        p1, st, err = cv2.calcOpticalFlowPyrLK(prev_gray, frame_gray, corners, None, **lk_params)  # 前一帧的角点在当前帧的位置
        p0, st1, err = cv2.calcOpticalFlowPyrLK(frame_gray, prev_gray, p1, None, **lk_params)  # 当前帧的角点在前一帧的位置
    except Exception as Error:
        logger.info(Error)
        p0 = corners
        p1 = corners
    d = abs(corners - p0).reshape(-1, 2).max(-1)
    good = d < 1
    for (x0, y0), (x, y), True_flag in zip(corners.reshape(-1, 2), p1.reshape(-1, 2), good):
        if not True_flag:
            continue
        bias.append([(x - x0), (y - y0)])
        Tracking_Ok.append([x, y])
    for i in range(0, len(bias)):
        dis = np.sqrt(math.pow(bias[i][0], 2) + math.pow(bias[i][1], 2))
        distance.append(dis)
    center_dis = -1  # 移动的大概中心点
    # logger.info(distance)
    if len(distance) > 0:
        filterDis = []  # 过滤小于1个像素的数据抖动
        for i in range(len(distance)):
            if distance[i] > 1:
                filterDis.append(distance[i])
        # 性能不够直接放弃用这个算法
        # logger.info(filterDis)
        # if len(filterDis) > 0:
        #     kdis = np.array(filterDis).reshape(-1, 1)
        #     km = KMeans(n_clusters=1)  # 一维类聚
        #     km.fit(kdis)
        #     # logger.info(km.cluster_centers_[0])
        #     center_dis = km.cluster_centers_[0][0]  # 获取中心点
    # logger.info(center_dis)
    result = []
    for i in range(len(distance)):
        result.append(distance[i])
        # if center_dis == -1:  # 小距离移动直接取平均值
        #     result.append(distance[i])
        # else:
        #     if distance[i] < center_dis + 1 and distance[i] > center_dis - 1:
        #         result.append(distance[i])
    # logger.info(result)
    if not result:  # 如果没有获取到正常的可追踪点,直接返回-1
        mean_dis = -1
    else:
        mean_dis = np.abs(np.sum(result, axis=0) / len(result))  # 获取平均值
    return mean_dis, Tracking_Ok, bias


class OpticalFlow(threading.Thread):
    seq = 0  # 记录报警次数

    def __init__(self, rThread, hThread, ip_camera_url, left, right, isOpenVideo, bbox_M):
        self.tracker = None
        self.rtspThrad = rThread  # 添加数据处理线程
        self.hThread = hThread  # 心跳的线程对象

        self.ip_camera_url = ip_camera_url
        self.left = left
        self.right = right
        self.isOpenVideo = isOpenVideo

        self.wpt = warningPushThread(self.rtspThrad, hThread)  # 直接创建设备异常报警帧处理线程
        self.wpt.start()

        self.bbox_M = bbox_M
        threading.Thread.__init__(self)

    def run(self):
        while True:  # 最外层死循环,初始化和切换当前时间状态
            frame = self.rtspThrad.getFrameData()
            frame_gray = self.rtspThrad.getGrayFrameData()
            if frame is None or frame_gray is None:
                logger.info("未获取到视频数据")
                time.sleep(3)
                continue
            if not self.rtspThrad.videoIsNight():  # 白天
                logger.info("启动白天状态监听")
                # self.disposeDayEvent()
                pass
            else:  # 晚上
                logger.info("启动晚上状态监听")
                # self.disposeNightEvent()
                # self.disposeDayEvent()
                pass
            # 这里修改的原因是 图片过大会导致跟踪框解析时间过长
            logger.info("开始处理跟踪框...")
            bbox_M = self.bbox_M
            tracker = Tracker(tracker_type='KCF')
            picSize = self.rtspThrad.getFramepicSize()
            trackerFrame = cv2.resize(frame.copy(), picSize)
            narrowBbox = (bbox_M[0] / np.int(opt.__dict__['narrow']),
                          bbox_M[1] / np.int(opt.__dict__['narrow']),
                          bbox_M[2] / np.int(opt.__dict__['narrow']),
                          bbox_M[3] / np.int(opt.__dict__['narrow']))  # 获取实际框体
            tracker.initWorking(trackerFrame, narrowBbox)
            # print(bbox_M)
            self.tracker = tracker
            self.disposeDayEvent()
        logger.error("算法线程异常结束")

    '''
        报警算法
    '''

    def disposeDayEvent(self):
        global isAlarm
        # global pushNumber
        global trackChang
        isInitFirstFrame = False  # 是否初始化了角点
        corners = None
        old_frame_gray = None
        beginLoopType = self.rtspThrad.videoIsNight()
        while beginLoopType is self.rtspThrad.videoIsNight() or isAlarm:  # 如果是初始化的时候的状态或者是报警状态的时候不跳出报警循环
            # while not self.rtspThrad.videoIsNight() or isAlarm:  # 白天状态循环,当是报警状态的时候不跳出循环
            run_time = str(time.strftime('%H%M%S'))
            run_time = int(run_time)
            # 事件可以处理的白天 当时报警状态的时候不处理判断
            # if int(opt.__dict__['start_time']) <= run_time <= int(opt.__dict__['end_time']) or isAlarm:

            frame = self.rtspThrad.getFrameData()  # 正常帧
            frame_gray = self.rtspThrad.getGrayFrameData()  # 灰度图帧
            trackerFrame = self.rtspThrad.getTrackerFrameData()  # 压缩尺寸帧

            if frame is None:
                logger.error("未获取到视频数据,摄像头正在连接中...")
                time.sleep(3)
                continue

            # refer_left, refer_right = Target_tracking(self.tracker, trackerFrame, self.left,
            #                                           self.right)  # 目标追踪放在这里，是为了检测图像中是否存在目标

            # (x1, y1) = refer_left
            # (x2, y2) = refer_right
            # (xS, yS) = self.rtspThrad.getFramepicSize()  # 这里比对的是缩放后的尺寸框
            # maxThis = 0
            # if x1 > x2:
            #     maxThis = x1
            #     x1 = x2
            #     x2 = maxThis
            # if y1 > y2:
            #     maxThis = y1
            #     y1 = y2
            #     y2 = maxThis
            # rectXSize = x2 - x1
            # rectYSize = y2 - y1
            # 设定监控包含框体可以完全移除画面的情况
            # if x1 > - rectXSize and x2 < (xS + rectXSize) and y1 > -rectYSize and y2 < (yS + rectYSize):
            logger.info("检测框移动距离:%s" % trackChang)
            if Target_tracking(self.tracker, trackerFrame, self.left, self.right):  # 是否遮挡 or 靶标完全消失
                self.pushDeviceError(1)  # 靶标未丢失状态,是正常帧
                videoIsNight = self.rtspThrad.videoIsNight()
                if not isInitFirstFrame:
                    logger.info("初始化靶标特征点...")
                    corners, old_frame_gray = self.initialize_first_frame(frame, frame_gray, self.left,
                                                                          self.right, videoIsNight)  # 初始化帧,获取跟踪角点

                if corners is not None:
                    isInitFirstFrame = True
                    if not videoIsNight:
                        frame_gray = cv2.equalizeHist(frame_gray)
                    mean_dis, Tracking_Ok, bias = corners_tracking(old_frame_gray, frame_gray, corners,
                                                                   self.rtspThrad, self.left, self.right)

                    # if (self.isOpenVideo):
                    logger.info("像素移动距离:%s" % mean_dis)
                    move = mean_dis / np.float(opt.__dict__['cm_dis'])  # 移动距离比例
                    if move > 1:
                        logger.error('目标位移超过预定阀值，开始发送报警信息！')
                        logger.error("像素移动距离:" + str(mean_dis))
                        logger.error('位移像素与标定比例:' + str(move))
                        # alarm_num += 1  # 更新参数
                        # old_frame_gray = frame_gray
                        # corners = np.array(Tracking_Ok)
                        # sum_bias = np.sum(bias, axis=0)  # bias里边有正有负
                        # delta_x = sum_bias[0] / len(bias)
                        # delta_y = sum_bias[1] / len(bias)
                        # (left_x, left_y) = self.left
                        # (right_x, right_y) = self.right
                        # # 刷新框体位置
                        # self.left = (left_x + delta_x, left_y + delta_y)
                        # self.right = (right_x + delta_x, right_y + delta_y)
                        # nowBbox = [left_x + delta_x, left_y + delta_y, right_x + delta_x - (left_x + delta_x),
                        #            right_y + delta_y - (left_y + delta_y)]  # box是原生的坐标值
                        # logger.info("新窗体位置:" + str(nowBbox))
                        # saveChangeConfig('bbox_lsit', nowBbox)
                        # 写txt
                        total_dis = np.sum(bias, axis=0)
                        with open('out.txt', 'a') as f:
                            f.write(time.strftime('%Y-%m-%d %H:%M:%S') + ':' + str(total_dis) + '\n')
                        self.pushWarning(frame)
                        isAlarm = True
                    elif mean_dis == -1 or isAlarm:  # 当前设备未检测到可用的正常的角点
                        if isAlarm:  # 如果是报警状态未检测到角点也发送图片
                            logger.error('未检测到靶标,当前是报警状态，开始发送报警信息！')
                            self.pushWarning(frame)
                        # else:
                        # isInitFirstFrame = False
                        # logger.info('靶标特征点不能正常检测,正准备重新检测特征点...')
                else:
                    isInitFirstFrame = False
                    logger.info('未检测到靶标特征点,正准备重新检测特征点...')
            else:
                if not isAlarm and trackChang < int(opt.__dict__['push_move_data']):
                    self.pushDeviceError(0)
                else:  # 如果是报警状态强制转换上报图片
                    if isAlarm:
                        logger.info('未检测到靶标,当前是报警状态，开始发送报警信息！')
                    else:
                        logger.info('未检测到靶标,靶标可能已经倾倒，开始发送报警信息！')
                        logger.info("靶标已经移动距离:" +str(trackChang))
                        isAlarm = True
                    self.pushDeviceError(1)
                    self.pushWarning(frame)
                # time.sleep(1)  # 阻塞线程1s
            # else:  # 停止算法处理--- 事件不处理的白天
            #     self.pushDeviceError(1)
            #     logger.info("当前不在白天算法处理时间段")
            #     time.sleep(60)  # 当不在事件处理时间段,每分钟处理一次
        logger.info("监听到白天和黑夜变化,开始重新启动算法...")
        pass

    '''
         发送报警,处理方法
     '''

    def pushWarning(self, frame):
        global pushNumber
        now_time = time.time()
        local_time = time.localtime(now_time)
        data_head = time.strftime("%Y%m%d%H%M%S", local_time)
        data_secs = (now_time - np.long(now_time)) * 1000
        time_stamp = "%s%03d" % (data_head, data_secs)
        time_stamp = int(time_stamp)

        pic_name = opt.__dict__['file_path'] + '/' + str(time_stamp) + '.jpg'
        imagPic = cv2.resize(frame.copy(), self.rtspThrad.getFramepicSize())
        cv2.imwrite(pic_name, imagPic)
        try:
            self.seq += 1
            th3 = Socket_Send_Pic(self.rtspThrad.getFramepicSize(),
                                  opt.__dict__['host'],
                                  int(opt.__dict__['port']),
                                  pic_name,
                                  self.seq,
                                  time_stamp)
            th3.start()
            th3.join()  # 图片发送的线程必须要等待
            if pushNumber <= 12:
                time.sleep(1)
            elif pushNumber <= 24:
                time.sleep(10 * 60)
            elif pushNumber <= 36:
                time.sleep(1 * 60 * 60)
            else:
                time.sleep(99 * 99 * 99 * 99 * 99 * 60 * 60)  # 相当于强制停止了
            logger.info("第" + str(pushNumber) + "次报警发送完毕")
            pushNumber = pushNumber + 1
        except Exception as Error:
            logger.error('上传图片出现问题：:' + str(Error))
        pass

    '''
        发送设备异常处理方法
    '''

    def pushDeviceError(self, type):
        if type is 0:  # 异常帧
            # if self.wpt is None:
            #     logger.info("检测到设备可能异常遮挡,开始进行区间时间段检测异常量...")
            #     self.wpt = warningPushThread(self.rtspThrad)
            #     self.wpt.addWarning()
            #     self.wpt.start()
            # else:
            #     if self.wpt.isLoopeStop():
            #         self.wpt.addWarning()
            #         pass
            #     else:
            #         logger.info("检测到设备异常,开始进行区间时间段检测异常量...")
            #         self.wpt = warningPushThread(self.rtspThrad)
            #         self.wpt.addWarning()
            #         self.wpt.start()

            self.wpt.addWarning()
            pass
        elif type is 1:  # 正常帧
            # if self.wpt is not None and self.wpt.isLoopeStop():  # 正常帧
            #     self.wpt.addNormal()
            self.wpt.addNormal()
            pass
        pass

    '''
        晚上事件 废弃
    '''

    # lower_white = np.array([0, 0, 221])
    # upper_white = np.array([180, 30, 255])
    #
    # callType = 0  # 0未报警状态  1 进入报警状态  2可以报警
    # hzNumber = 0  # 进入报警状态后的后续帧数
    # hzFalse = 0  # 进入报警状态后错误的帧数

    # def disposeNightEvent(self):
    #     global isAlarm
    #     global pushNumber
    #     # pts = []
    #     initCenter = None  # 监听的第一帧
    #     lastDistance = 0  # 监听的最后一个有效帧位移量
    #     initRadius = 0  # 监听的最大的圆的半径
    #     radiusChange = 0
    #     while self.rtspThrad.videoIsNight() or \
    #             isAlarm:  # 晚上状态循环
    #         frame = self.rtspThrad.getFrameData()
    #         frameHSV = self.rtspThrad.getHSVFrameData()
    #         if frame is None or frameHSV is None:
    #             logger.error("未获取到视频数据,摄像头正在连接中...")
    #             time.sleep(3)
    #
    #             # 还原状态
    #             self.callType = 0
    #             self.hzNumber = 0
    #             self.hzFalse = 0
    #             continue
    #
    #         kernel = np.ones((5, 5), np.uint8)  # 腐蚀所需要的核
    #         mask = cv2.inRange(frameHSV, self.lower_white, self.upper_white)
    #         mask = cv2.erode(mask, kernel, iterations=2)  # 将核传入erode函数,iteration为迭代次数
    #         mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    #         mask = cv2.dilate(mask, kernel, iterations=3)
    #         res = cv2.bitwise_and(frame, frame, mask=mask)
    #         cnts, heir = cv2.findContours(mask.copy(), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)[
    #                      -2:]  # 返回值一个是轮廓本身，另一个是每条轮廓对应得属性
    #         center = None
    #         distance = 0
    #         if len(cnts) == 0:
    #             if not isAlarm:  # 靶标消失状态
    #                 if lastDistance <= np.float(opt.__dict__['Target_size']) / 2:  # 当圆心在靶标范围内
    #                     if radiusChange > np.float(opt.__dict__['Target_change_size']):  # 圆半径变化大于阀值
    #                         # 还原状态
    #                         self.callType = 0
    #                         self.hzNumber = 0
    #                         self.hzFalse = 0
    #                         self.pushDeviceError(0)  # 遮挡
    #                         pass
    #                     else:
    #                         if self.callType == 1:  # 是否在报警状态 直接报警
    #                             logger.error('最后检测靶心在靶标范围内,且靶标距离未超过阀值,未检测到靶标,当前是报警状态，开始发送报警信息！')
    #                             # 还原状态
    #                             self.callType = 0
    #                             self.hzNumber = 0
    #                             self.hzFalse = 0
    #                             # 写txt
    #                             # total_dis = np.sum(bias, axis=0)
    #                             self.pushWarning(frame)
    #                             isAlarm = True
    #                             pass
    #                         else:  # 圆心在靶标内但是不是报警状态不报警
    #                             self.pushDeviceError(0)
    #                             pass
    #                         pass
    #                 else:  # 圆心在靶标外
    #                     if self.callType == 1:  # 是否在报警状态 直接报警
    #                         logger.error('最后检测靶心不在靶标范围内,未检测到靶标,当前是报警状态，开始发送报警信息！')
    #                         # 还原状态
    #                         self.callType = 0
    #                         self.hzNumber = 0
    #                         self.hzFalse = 0
    #                         # 写txt
    #                         # total_dis = np.sum(bias, axis=0)
    #                         self.pushWarning(frame)
    #                         isAlarm = True
    #                         pass
    #                     else:  # 圆心在靶标外但是不是报警状态不报警
    #                         self.pushDeviceError(0)
    #                         pass
    #
    #             else:  # 如果是报警状态强制转换上报图片
    #                 self.pushDeviceError(1)
    #                 self.pushWarning(frame)
    #             time.sleep(1)  # 阻塞线程1s
    #         elif len(cnts) > 0:  # 如果检测出了轮廓
    #             self.pushDeviceError(1)
    #             c = max(cnts, key=cv2.contourArea)  # 以轮廓的面积为条件，找出最大的面积
    #             ((x, y), radius) = cv2.minEnclosingCircle(c)  # 找出最小的圆
    #
    #             M = cv2.moments(c)
    #             # x = M["m10"] / M["m00"]
    #             # y = M["m01"] / M["m00"]
    #             # center = (int(x), int(y))
    #             center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
    #             if center is None:
    #                 continue
    #                 pass
    #             if initCenter is None:  # 初始化赋值
    #                 logger.info("初始化靶标特征点...")
    #                 initCenter = center
    #                 initRadius = radius
    #                 continue
    #                 pass
    #
    #             '''
    #                                 增加需求:
    #                                         当位移距离小于阀值的时候 圆半径变化大于阀值则认为是遮挡变化
    #                                         当位移距离大于阀值的时候,直接认为是移动变化
    #                                 怎么去判断这个过程
    #                                        思路:
    #                                             1:移动限制:
    #                                                     当圆心在靶标范围内
    #                                                                 有位移
    #                                                                     圆变化大于阀值--->限制位移
    #                                                                     圆变化小于阀值-->正常位移
    #                                                                 无位移
    #                                                                     正常处理
    #                                                     当圆心不在靶标范围内:
    #                                                                 正常处理
    #                                             2:消失限制:
    #                                                     当靶标消失
    #                                                             有报警
    #                                                                 直接报警不考虑
    #                                                             无报警
    #                                                                 最后保存的圆心是否在靶标内
    #                                                                     是-->
    #                                                                         圆变化大于阀值
    #                                                                                 是-->遮挡
    #                                                                                 否-->
    #                                                                                     是否在报警状态
    #                                                                                         是-->报警
    #                                                                                         否-->产生了位移但是不够大在可接受范围内遮挡
    #                                                                     否-->
    #                                                                         是否在报警状态
    #                                                                             是-->报警
    #                                                                             否-->产生了位移但是不够大在可接受范围内遮挡
    #
    #
    #             '''
    #
    #             # pts.append(center)
    #             # center0 = pts[0]#圆心
    #             # for i in range(1, len(pts) - 1):
    #             distance = int(
    #                 math.sqrt(math.pow((center[0] - initCenter[0]), 2) + math.pow((center[1] - initCenter[1]), 2)))
    #             lastDistance = distance
    #             radiusChange = initRadius - radius
    #             if self.isOpenVideo:
    #                 logger.info("像素移动距离:%s" % distance)
    #                 # logger.info("当前半径变化大小:%s" % radiusChange)
    #             else:
    #                 print("像素移动距离:%s" % distance)
    #                 # print("当前半径变化大小:%s" % radiusChange)
    #
    #             move = distance / np.float(opt.__dict__['cm_dis'])  # 移动距离比例
    #
    #             if move > 1:
    #                 if distance * 2 <= np.float(opt.__dict__['Target_size']):  # 当圆心在靶标范围内
    #                     if radiusChange > np.float(opt.__dict__['Target_change_size']):  # 圆半径变化大于阀值
    #                         continue  # 跳过处理
    #                         pass
    #                     else:  # 正常位移
    #                         pass
    #                 else:  # 正常位移
    #                     pass
    #
    #                 logger.error("像素移动距离:" + str(distance))
    #                 logger.error('移动距离比例:' + str(move))
    #                 # 报警可靠性
    #                 if self.callType == 0:  # 不在报警状态
    #                     logger.error('进入报警状态...')
    #                     self.callType = 1
    #                     self.hzNumber = self.hzNumber + 1
    #                     self.hzFalse = self.hzFalse + 1
    #                 elif self.callType == 1:
    #                     if self.hzNumber >= int(opt.__dict__['Alarm_sample']):  # 全部样本帧获取完毕
    #                         if self.hzFalse >= int(opt.__dict__['Alarm_reliability']):  # 报警
    #                             logger.error('目标移动距离超过上限值，即将发送报警信息！')
    #                             # 还原状态
    #                             self.callType = 0
    #                             self.hzNumber = 0
    #                             self.hzFalse = 0
    #                             # 写txt
    #                             # total_dis = np.sum(bias, axis=0)
    #                             with open('out.txt', 'a') as f:
    #                                 f.write(time.strftime('%Y-%m-%d %H:%M:%S') + ':' + str(distance) + '\n')
    #
    #                             self.pushWarning(frame)
    #                             isAlarm = True
    #                             pass
    #                         else:  # 解除报警
    #                             self.callType = 0
    #                             self.hzNumber = 0
    #                             self.hzFalse = 0
    #                             logger.info("为达到报警帧阀值,解除夜间报警状态,检测到误报警")
    #                             pass
    #                         pass
    #                     else:  # 继续获取样本帧
    #                         self.hzNumber = self.hzNumber + 1
    #                         self.hzFalse = self.hzFalse + 1
    #                         logger.info("在报警状态,未达到报警容器阀值,报警帧记录")
    #                         pass
    #                     pass
    #             else:
    #                 if not isAlarm:
    #                     if self.callType == 1:
    #                         if int(opt.__dict__['Alarm_sample']) >= self.hzNumber:  # 全部样本帧获取完毕
    #                             if self.hzFalse >= int(opt.__dict__['Alarm_reliability']):  # 报警
    #                                 logger.error('目标移动距离超过上限值，即将发送报警信息！')
    #                                 logger.error('位移距离:' + str(move))
    #                                 # 还原状态
    #                                 self.callType = 0
    #                                 self.hzNumber = 0
    #                                 self.hzFalse = 0
    #                                 # 写txt
    #                                 # total_dis = np.sum(bias, axis=0)
    #                                 with open('out.txt', 'a') as f:
    #                                     f.write(time.strftime('%Y-%m-%d %H:%M:%S') + ':' + str(distance) + '\n')
    #                                 self.pushWarning(frame)
    #                                 isAlarm = True
    #                                 pass
    #                             else:  # 解除报警
    #                                 self.callType = 0
    #                                 self.hzNumber = 0
    #                                 self.hzFalse = 0
    #                                 logger.info("为达到报警帧阀值,解除夜间报警状态,检测到误报警")
    #                                 pass
    #                             pass
    #                         else:  # 继续获取样本帧
    #                             self.hzNumber = self.hzNumber + 1
    #                             logger.info("在报警状态,未达到报警容器阀值,正常帧记录")
    #                 else:  # 是报警状态直接报警
    #                     self.pushWarning(frame)
    #                     pass
    #                 pass
    #         pass
    #     pass

    # def saveChangeConfig(configName, newKey):
    #     file_data = ""
    #     with io.open('config.txt', 'r', encoding='utf-8') as f:
    #         lines = f.readlines()
    #         for line in lines:
    #             if line.startswith('#'):
    #                 pass
    #             else:
    #                 name = line.split('=')[0]
    #                 if configName == name:
    #                     key = line.split('=')[-1].split('\n')[0]
    #                     line = line.replace(key, str(newKey))
    #             file_data += line
    #     with io.open('config.txt', "w", encoding="utf-8") as f:
    #         f.write(file_data)

    # if __name__ == '__main__':
    #     with io.open('config.txt', 'r', encoding='utf-8') as f:
    #         lines = f.readlines()
    #         for line in lines:
    #             if line.startswith('#'):
    #                 continue
    #             else:
    #                 name = line.split('=')[0]
    #                 key = line.split('=')[-1].split('\n')[0]
    #                 item = {name: key}
    #                 opt._parse(item)
    #
    #     tracker = Tracker(tracker_type='KCF')
    #     ip_camera_url = "rtsp://%s:%s@%s/h265/ch%s/main/av_stream" % (
    #         opt.__dict__['user'], opt.__dict__['pwd'], opt.__dict__['ip'], opt.__dict__['channel'])
    #     # ip_camera_url='1cm.mp4'
    #     video = cv2.VideoCapture(ip_camera_url)
    #     if video.isOpened():
    #         ok, frame = video.read()
    #         frame = cv2.resize(frame, (1024, 540))
    #         bbox = cv2.selectROI(frame, False)
    #         (left_x, left_y, w, h) = bbox
    #         left = (left_x, left_y)
    #         right = (left_x + w, left_y + h)
    #         tracker.initWorking(frame, bbox)
    #         cv2.imwrite(opt.__dict__['file_path'] + '/first.jpg', frame)
    #         logger.info('\033[1;34m初始化完成\033[0m')
    #     else:
    #         logger.info('\033[1;31m请检查IP地址还有端口号，或者查看IP摄像头是否开启\033[0m')
    #         left = (0, 0)
    #         right = (0, 0)
    #
    #     lock = threading.Lock()
    #     th1 = OpticalFlow(ip_camera_url, left, right, tracker)
    #     th1.start()
    #     th1.join()
    def Getcorners(self, frame, left, right, p):
        '''
        :param frame: 当前帧图片
        :param left: 目标窗口左上角坐标
        :param right: 目标窗口右下角坐标
        :param p: 当前帧图片的所有角点
        :return: 目标窗口内的角点
        '''
        corners = []
        for i, point in enumerate(p):
            [[x, y]] = point
            if left[0] < x < right[0] and left[1] < y < right[1]:
                corners.append([[np.float32(x), np.float32(y)]])
                cv2.circle(frame, (x, y), 3, (0, 0, 255), 1)

        cv2.rectangle(frame, (int(left[0]), (int(left[1]))), (int(right[0]), int(right[1])), (255, 255, 0), 3)
        imagPic = cv2.resize(frame, self.rtspThrad.getFramepicSize())
        cv2.imwrite(opt.__dict__['file_path'] + '/' + 'rgb_point' + '.jpg', imagPic)
        corners = np.array(corners)
        return corners

    def initialize_first_frame(self, frame, frame_gray, left, right, videoIsNight):
        if frame is not None:
            cv2.imwrite(opt.__dict__['file_path'] + '/' + 'gray_1.jpg', frame_gray)  # 初始化的黑白帧
            if not videoIsNight:
                frame_gray = cv2.equalizeHist(frame_gray)
                cv2.imwrite(opt.__dict__['file_path'] + '/' + 'gray_2.jpg', frame_gray)  # 白天算法对齐后的彩色帧
            feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
            p = cv2.goodFeaturesToTrack(frame_gray, mask=None, **feature_params)
            corners = self.Getcorners(frame, left, right, p)
            if corners.shape == (0,):
                return None, None
            else:
                return corners, frame_gray
        else:
            return None, None
