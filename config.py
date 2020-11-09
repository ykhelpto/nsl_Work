# -*- coding: UTF-8 -*-
from loguru import logger  # 日志控件


class DefaultConfig(object):
    # user, pwd, ip, channel = "admin", "simit123", "172.19.2.12", 1  # 1.摄像机ip
    # #ip_camera_url = "rtsp://%s:%s@%s/h265/ch%s/main/av_stream" % (user, pwd, ip, channel)
    # ip_camera_url = '1cm.mp4'
    # host, port, bufsize = '127.0.0.1', 33808, 40960  # 2.服务器ip
    # cm_dis = 7 #7         # 3.先验值
    # file_path = 'test'  # 4.图片存储地址
    # frame_speed = 1     # 帧率， 每隔几张图片进行检测
    # time_interval = 2
    def _parse(self, kwargs):
        for k, v in kwargs.items():
            # if not hasattr(self, k):  # 判断对象里是否有k属性或方法
            #     warnings.warn('Warning:opt has not attibute %s' %k)
            setattr(self, k, v)  # 给对象属性赋值，若属性不存在，则新创建再赋值

        for k, v in self.__class__.__dict__.items():
            if not k.startswith('_'):
                logger.info(k, getattr(self, k))


opt = DefaultConfig()
