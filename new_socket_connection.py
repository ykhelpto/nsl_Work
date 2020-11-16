# -*- coding: UTF-8 -*-
import threading
from socket import *
from config import opt
import struct
import time
import numpy as np
import json
from os import path
from PIL import Image
from loguru import logger  # 日志控件

lock = threading.Lock()


class Socket_Send_Pic(threading.Thread):
    def __init__(self, picSize, host, port, pic_name, seq, time_stamp):
        super(Socket_Send_Pic).__init__()
        self.pic_name = pic_name
        self.host = host
        self.port = port
        self.seq = seq
        self.picSize = picSize
        self.time_stamp = time_stamp
        tcpClient = socket(AF_INET, SOCK_STREAM)  # 创建socket
        tcpClient.connect((self.host, self.port))
        self.tcpClient = tcpClient
        threading.Thread.__init__(self)

    def run(self):
        setdefaulttimeout(10)
        if self.pic_name is not None:
            # try:
            (xSize, ySize) = self.picSize
            newImage = Image.new('RGB', (xSize, ySize * 2))

            picData2 = Image.open(opt.__dict__['file_path'] + '/' + 'rgb_point' + '.jpg')
            newImage.paste(picData2, (0, 0))
            picData = Image.open(self.pic_name)
            newImage.paste(picData, (0, ySize))

            newImage.save(self.pic_name)  # 覆盖原图
            # 图片压缩
            pic_name = self.compress_image(self.pic_name, '', int(opt.__dict__['local_pic_size']) * 1024)

            pic = open(pic_name, 'rb')
            pic_hex = pic.read()
            # logger.info('数据总长度:',len(pic_hex))
            # 总长度要转十六进制
            # logger.info(len(pic_hex), hex(len(pic_hex)), str(hex(len(pic_hex)))[2:])
            hex_len = hex(len(pic_hex))
            hex_len = str(hex_len)[2:]
            for k in range(8 - len(hex_len)):
                hex_len = '0' + hex_len
            # logger.info(hex_len, bytes.fromhex(hex_len))
            total_number = (len(pic_hex) // (int(opt.__dict__['length_send']) - 14)) + 1  # 28是包头的内容
            every_data_len = (int(opt.__dict__['length_send']) - 14)
            logger.info('分%d次完成，每一次发送%d个字符' % (total_number, every_data_len))
            logger.info('-----------------------------------------------------')

            for i in range(int(total_number)):
                data = {'msgType': 2,
                        'sequence': self.seq,
                        'device': '1',
                        'time': self.time_stamp
                        }
                logger.info(data)
                data_send = json.dumps(data)
                self.tcpClient.send(data_send.encode())
                # logger.info('-----------------------------')
                # logger.info(data_send)
                time.sleep(0.5)

                if i < (total_number - 1):
                    # 2.当前包大小
                    # logger.info(int(opt.__dict__['length_send'])-14, hex(int(opt.__dict__['length_send'])-14), str(hex(int(opt.__dict__['length_send'])-14))[2:])
                    len_this_one = str(hex(int(opt.__dict__['length_send']) - 14))[2:]
                    for j in range(8 - len(len_this_one)):
                        len_this_one = '0' + len_this_one
                    # logger.info('当前包大小：', len_this_one, bytes.fromhex(len_this_one))
                    # 3、分包总数
                    if total_number < 10:
                        total_number_str = '0' + str(total_number)
                        id_this_one = '0' + str(i)
                    elif total_number >= 10 and total_number <= 99:
                        total_number_str = str(hex(total_number))[2:]
                        for m in range(2 - len(total_number_str)):
                            total_number_str = '0' + total_number_str
                        id_this_one = str(hex(i))[2:]
                        for n in range(2 - len(id_this_one)):
                            id_this_one = '0' + id_this_one

                    logger.info('当前包：' + str((i + 1)))
                    head = '1ACFFC1D' + hex_len + len_this_one + total_number_str + id_this_one
                    # logger.info('head:', head)
                    head = bytes.fromhex(head)
                    # logger.info('head:', head, len(head))
                    # logger.info('-----------------------------------------------------')
                    send_data = head + pic_hex[i * every_data_len:(i + 1) * every_data_len]

                    send_data = struct.pack('%dB' % (len(send_data)), *send_data)
                    # logger.info('Send_data:', send_data)
                    self.tcpClient.send(send_data)
                    time.sleep(0.5)
                elif i == (total_number - 1):
                    # 2.当前包大小
                    num_of_this_one = len(pic_hex) % (int(opt.__dict__['length_send']) - 14)
                    # logger.info(num_of_this_one, hex(num_of_this_one), str(hex(num_of_this_one)))
                    len_this_one = str(hex(num_of_this_one))[2:]
                    for j in range(8 - len(len_this_one)):
                        len_this_one = '0' + len_this_one
                    # logger.info('当前包大小：' + len_this_one + bytes.fromhex(len_this_one))
                    # 3、分包总数
                    if total_number < 10:
                        total_number_str = '0' + str(total_number)
                        id_this_one = '0' + str(i)
                    elif total_number >= 10 and total_number <= 99:
                        total_number_str = str(hex(total_number))[2:]
                        for m in range(2 - len(total_number_str)):
                            total_number_str = '0' + total_number_str
                        id_this_one = str(hex(i))[2:]
                        for n in range(2 - len(id_this_one)):
                            id_this_one = '0' + id_this_one
                    head = '1ACFFC1D' + hex_len + len_this_one + total_number_str + id_this_one
                    logger.info('当前包：' + str((i + 1)))
                    # logger.info('head:', head)
                    head = bytes.fromhex(head)
                    # logger.info('head:', head, len(head))
                    send_data = head + pic_hex[i * every_data_len:]
                    send_data = struct.pack('%dB' % (len(send_data)), *send_data)
                    # logger.info(send_data)
                    self.tcpClient.send(send_data)
                    time.sleep(0.5)
            logger.warning("图片发送完毕")
            self.tcpClient.close()
        # except Exception as Error:
        #     self.tcpClient.close()
        #     logger.info('上传图片出现问题：:' + str(Error))

    def compress_image(self, infile, outfile='', mb=150, step=10, quality=80):
        """不改变图片尺寸压缩到指定大小
        :param infile: 压缩源文件
        :param outfile: 压缩文件保存地址
        :param mb: 压缩目标，KB
        :param step: 每次调整的压缩比率
        :param quality: 初始压缩比率
        :return: 压缩文件地址，压缩文件大小
        """
        o_size = path.getsize(infile)
        if o_size <= mb:
            return infile
        outfile = self.get_outfile(infile, outfile)
        while o_size > mb:
            im = Image.open(infile)
            im.save(outfile, quality=quality)
            if quality - step < 0:
                break
            quality -= step
            o_size = path.getsize(outfile)
        np.os.remove(infile)  # 删除原图片
        return outfile
        # return outfile, path.getsize(outfile)

    def get_outfile(self, infile, outfile):
        if outfile:
            return outfile
        dir, suffix = path.splitext(infile)
        outfile = '{}-out{}'.format(dir, suffix)
        return outfile


if __name__ == '__main__':
    # with open('config.txt', 'r', encoding='utf-8') as f:
    #     lines = f.readlines()
    #     for line in lines:
    #         if line.startswith('#'):
    #             continue
    #         else:
    #             name = line.split('=')[0]
    #             key = line.split('=')[-1].split('\n')[0]
    #             item = {name: key}
    #             opt._parse(item)
    # now_time = time.time()
    # local_time = time.localtime(now_time)
    # data_head = time.strftime("%Y%m%d%H%M%S", local_time)
    # data_secs = (now_time - np.long(now_time)) * 1000
    # time_stamps = "%s%03d" % (data_head, data_secs)
    # logger.info(time_stamps)
    # time_stamps = int(time_stamps)
    # logger.info(time_stamps)
    # pic_name = 'target.jpg'
    # seq = 0
    # th3 = Socket_Send_Pic(opt.__dict__['host'], int(opt.__dict__['port']), pic_name, 1, time_stamps)
    # th3.start()
    # th3.join()

    # a = '1ACFFC1D'
    # b = bytes.fromhex(a)
    # logger.info(b)
    # a = '256d'
    # logger.info(bytes.fromhex(a))
    newImage = Image.new('RGB', (960, 1080))
    picData = Image.open("C:\\Users\\zzd\\Desktop\\11.5\\2020-11-04-10-22-23_point.jpg").resize(
        (960, 540), Image.ANTIALIAS)
    newImage.paste(picData, (0, 0))
    picData2 = Image.open("C:\\Users\\zzd\\Desktop\\11.5\\20201104174629805-out.jpg").resize(
        (960, 540), Image.ANTIALIAS)
    newImage.paste(picData2, (0, 540))
    newImage.save("C:\\Users\\zzd\\Desktop\\11.5\\save.jpg")
