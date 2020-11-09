# -*- coding: UTF-8 -*-
import json
from socket import *
from socket import socket
from config import opt
from loguru import logger  # 日志控件
def Client_send(data):
    data_send = json.dumps(data)
    setdefaulttimeout(5)  # 设置连接超时时间
    if data_send != None:
        try:
            tcpClient = socket(AF_INET, SOCK_STREAM)  # 创建socket
            tcpClient.connect((opt.__dict__['host'], int(opt.__dict__['port'])))
            tcpClient.send(data_send.encode())
            #tcpClient.close()
        except Exception as Error:
            logger.info(Error)
            logger.info('tcp没有连接上，输出上传失败！！')

import struct
def Client_send_pic_hex(data):
    setdefaulttimeout(3)
    if data != None:
        try:
            tcpClient = socket(AF_INET, SOCK_STREAM)  # 创建socket
            tcpClient.connect((opt.__dict__['host'], int(opt.__dict__['port'])))
            #date = struct.pack("%dB" % (len(data)), *data)
            tcpClient.send(data)
        except Exception as Error:
            logger.info(Error)
            logger.info('tcp没有连接上，输出上传失败！！')

