# -*- coding: UTF-8 -*-
import sys

import cv2
import threading
import os
import io
import queue
import numpy as np
from past.builtins import raw_input

from new_optical_flow import OpticalFlow
from Send_HeartBeat import Send_heatbeat
from rtsp_connection import RtspConnection
from pixel_measure import PixelMeasure
from config import opt
from loguru import logger  # 日志控件
from GuardThread import guardTherad  # 线程守护
from rtsp_frame_tool import RtspFrameTool  # 线程守护

isChangeCF = False

lk_params = dict(winSize=(15, 15),
                 maxLevel=2,
                 criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

feature_params = dict(maxCorners=1000,
                      qualityLevel=0.3,
                      minDistance=7,
                      blockSize=7)
BaseRTSPURL = "rtsp://%s:%s@%s/h265/ch%s/main/av_stream"


def Mkdir(file_path):
    if not os.path.isdir(file_path):
        os.makedirs(file_path)
        logger.info(file_path + '文件夹创建完毕')


def get_input(qr):
    global isChangeCF
    input_Str = raw_input('是否需要修改配置(y/n)?: ')
    if input_Str == 'y' or input_Str == 'Y':
        isChangeCF = True
    qr.put(1)


def wait(qrs):
    try:
        qrs.get(timeout=5)
    except queue.Empty:
        pass


'''
	修改配置文件
'''


def saveChangeConfig(configName, newKey):
    file_data = ""
    with io.open('config.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for sline in lines:
            if sline.startswith('#'):
                pass
            else:
                sname = sline.split('=')[0]
                if configName == sname:
                    skey = sline.split('=')[-1].split('\n')[0]
                    sline = sline.replace(skey, str(newKey))
            file_data += sline
    with io.open('config.txt', "w", encoding="utf-8") as f:
        f.write(file_data)
        f.close()


# 展示视频角点情况
def showTestWindow(srtspThrad):
    track_len = 100
    detect_interval = 5
    tracks = []
    frame_idx = 0
    isShowWindow = True
    while isShowWindow:
        window_frame = srtspThrad.getFrameData()
        frame_gray = srtspThrad.getGrayFrameData()
        if frame_gray is None:
            continue
        if frame_idx % detect_interval == 0:  # 每5帧检测一次特征点:
            mask = np.zeros_like(frame_gray)  # 初始化和视频大小相同的图像
            mask[:] = 255  # 将mask赋值255也就是算全部图像的角点
            for x, y in [np.int32(tr[-1]) for tr in tracks]:  # 跟踪的角点画圆
                cv2.circle(mask, (x, y), 5, 0, -1)
            p = cv2.goodFeaturesToTrack(frame_gray, mask=mask, **feature_params)  # 像素级别角点检测
            if p is not None:
                for x, y in np.float32(p).reshape(-1, 2):
                    tracks.append([(x, y)])  # 将检测到的角点放在待跟踪序列中

        frame_idx += 1
        prev_gray = frame_gray

        if len(tracks) > 0:  # 检测到角点后进行光流跟踪
            img0, img1 = prev_gray, frame_gray
            p0 = np.float32([tr[-1] for tr in tracks]).reshape(-1, 1, 2)
            p1, st, err = cv2.calcOpticalFlowPyrLK(img0, img1, p0, None, **lk_params)  # 前一帧的角点和当前帧的图像作为输入来得到角点在当前帧的位置
            p0r, st, err = cv2.calcOpticalFlowPyrLK(img1, img0, p1, None,
                                                    **lk_params)  # 当前帧跟踪到的角点及图像和前一帧的图像作为输入来找到前一帧的角点位置
            # print(p1)
            # print(p0r)
            d = abs(p0 - p0r).reshape(-1, 2).max(-1)  # 得到角点回溯与前一帧实际角点的位置变化关系

            good = d < 1  # 判断d内的值是否小于1，大于1跟踪被认为是错误的跟踪点
            new_tracks = []
            for tr, (x, y), good_flag in zip(tracks, p1.reshape(-1, 2), good):  # 将跟踪正确的点列入成功跟踪点
                if not good_flag:
                    continue
                tr.append((x, y))
                if len(tr) > track_len:
                    del tr[0]
                new_tracks.append(tr)
                cv2.circle(window_frame, (x, y), 2, (0, 255, 0), -1)
            tracks = new_tracks
            cv2.polylines(window_frame, [np.int32(tr) for tr in tracks], False, (0, 255, 0))  # 以上一振角点为初始点，当前帧跟踪到的点为终点划线
            # draw_str(vis, (20, 20), 'track count: %d' % len(self.tracks))
        cv2.namedWindow('window', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('window', 1500, 800)
        cv2.imshow('window', window_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('\r'):
            isShowWindow = False
            cv2.destroyAllWindows()
            break


if __name__ == '__main__':

    with io.open('config.txt', 'r', encoding='utf-8') as f:  # 读取配置文件内容
        for line in f.readlines():
            if not line.startswith('#'):
                name = line.split('=')[0]
                key = line.split('=')[-1].split('\n')[0]
                item = {name: key}
                opt._parse(item)

    Mkdir(opt.file_path)  # 构建图片存储文件夹
    Mkdir(opt.log_path)  # 构建日志存储文件夹

    # 日志配置
    logger.remove(handler_id=None)  # 清除之前的设置 关闭默认输出的控制台
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(BASE_DIR, opt.log_path + '\\file_{time}.log')
    err_log_file_path = os.path.join(BASE_DIR, opt.log_path + '\\error_file_{time}.log')
    logger.add(sys.stderr, level="WARNING")
    logger.add(log_file_path, rotation="10 MB", compression="zip", encoding='utf-8', enqueue=True, retention="30 days")
    logger.add(
        err_log_file_path,
        rotation="10 MB",
        compression="zip",
        encoding='utf-8',
        level='ERROR',
        enqueue=True,
        retention="2 months")

    ip_camera_url = BaseRTSPURL % (
    opt.__dict__['user'], opt.__dict__['pwd'], opt.__dict__['ip'], opt.__dict__['channel'])
    # ip_camera_url = "C:\\Users\\zzd\\Desktop\\11.3\\video\\d_c_n.mp4"
    # ip_camera_url = "C:\\Users\\zzd\\Desktop\\10.30\\testvideo\\d1.mp4"
    # ip_camera_url = "C:\\Users\\zzd\\Desktop\\11.4\\video\\172.19.152.166_01_20201102174415364.mp4"
    # ip_camera_url = "1cm.mp4"
    logger.warning("启动连接:" + ip_camera_url)
    rtspThrad = RtspConnection(ip_camera_url, np.int(opt.__dict__['narrow']))  # 摄像头数据
    rtspThrad.start()
    initSate = False
    isOpenVideo = False
    left = (0, 0)
    right = (0, 0)
    bbox_M = tuple(eval(opt.__dict__['bbox_lsit']))
    while not initSate:
        frame = rtspThrad.getFrameData()
        if frame is None:
            left = (0, 0)
            right = (0, 0)
            continue
        else:
            q = queue.Queue()
            wait_thread = threading.Thread(target=wait, args=(q,))  # 等候线程
            input_thread = threading.Thread(target=get_input, args=(q,))  # 判断输入线程
            input_thread.daemon = True
            wait_thread.start()
            input_thread.start()
            wait_thread.join()

            # global isChangeCF

            if isChangeCF:
                logger.warning("请确认靶标内角点正常,<<确定焦点在弹出窗口后>>,按回车键结束")
                showTestWindow(rtspThrad)
                inputStr = input('请输入实际距离: ')
                pm = PixelMeasure(rtspThrad)  # 获取像素值
                pN = pm.getpixelNumber() / int(inputStr) * np.int(opt.__dict__['narrow'])  # 计算实际像素值
                opt.__dict__['cm_dis'] = pN
                logger.info('cm_dis' + str(opt.__dict__['cm_dis']))
                saveChangeConfig('cm_dis', pN[0])
                picSize = rtspThrad.getFramepicSize()
                frameROI = cv2.resize(frame.copy(), picSize)
                bbox = cv2.selectROI(frameROI, False)  # 获取框体坐标
                cv2.destroyAllWindows()
                nowBbox = (bbox[0] * np.int(opt.__dict__['narrow']), bbox[1] * np.int(opt.__dict__['narrow']),
                           bbox[2] * np.int(opt.__dict__['narrow']), bbox[3] * np.int(opt.__dict__['narrow']))  # 获取实际框体
                saveChangeConfig('bbox_lsit', nowBbox)
                bbox_M = nowBbox
                # inputStr = raw_input('是否启动视频实时展示,会消耗设备性能,建议正式模式下不要开启(y/n)?: ')
                # if inputStr == 'y' or inputStr == 'Y':
                #     logger.warning("已经启动视频实时展示")
                #     isOpenVideo = True

            (left_x, left_y, w, h) = bbox_M
            left = (left_x, left_y)
            right = (left_x + w, left_y + h)
            if np.int(opt.__dict__['isOpenVideo']) is 1:
                isOpenVideo = True
            else:
                isOpenVideo = False
            logger.warning("检测靶标区域:" + str(bbox_M))
            initSate = True

    th0 = RtspFrameTool(rtspThrad)  # 视频流工具线程可以把耗时操作放在这里面
    th2 = Send_heatbeat(rtspThrad)  # 心跳
    th1 = OpticalFlow(th0, th2, ip_camera_url, left, right, isOpenVideo, bbox_M)  # 算法

    th3 = guardTherad(th1.getName(), th2.getName(), rtspThrad, th2, th0, ip_camera_url, left, right, isOpenVideo,
                      bbox_M)

    th0.start()
    th1.start()
    th2.start()  # 开启两个线程
    th3.start()

    th0.join()
    th1.join()
    th2.join()
    th3.join()
