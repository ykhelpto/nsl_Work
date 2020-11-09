# -*- coding: UTF-8 -*-
import cv2
from socket import *
import time
from PIL import Image
import os


# image = cv2.imread('C:\\Users\\zzd\\Desktop\\10.20\\cache\\1603167224560.bmp')
# # cv2.imshow("new window", image)  # 显示图片
# image_info = image.shape
# height = image_info[0]
# width = image_info[1]
# size = (width, height)
# fps = 30
# fourcc = cv2.VideoWriter_fourcc(*"mp4v")
# videowriter = cv2.VideoWriter('C:\\Users\\zzd\\Desktop\\10.20\\ss.mp4', fourcc, fps, size)


def run(n, hexs):
    if n == "t2":
        HOST = '192.168.1.11'  # or 'localhost'
        PORT = 6969
        BUFSIZ = 1024
        ADDR = (HOST, PORT)
        tcpCliSock = socket(AF_INET, SOCK_STREAM)
        tcpCliSock.connect(ADDR)
        package_hex_s = 0
        # isReady = True
        while True:
            data = tcpCliSock.recv(200 * 1024)
            path = "C:\\Users\\zzd\\Desktop\\10.20\\cache\\" + str(data)[2:-1] + ".bmp"
            print(str(data)[2:-1])
            print(data)
            print(os.path.getsize(path))
            if os.path.exists(path):
                # copyfile(path, "C:\\Users\\zzd\\Desktop\\10.20\\cache2\\" + str(data)[2:-1] + ".bmp")
                # if isReady:#过滤非正常数据
                # isReady=False
                # img = cv2.imread(path)
                # videowriter.write(img)
                os.remove(path)
                # isReady = True
    if n == "t3":
        time.sleep(5)
        capture = cv2.VideoCapture('C:\\Users\\zzd\\Desktop\\10.20\\ss.mp4')
        print(capture.isOpened())
        if capture.isOpened():
            while True:
                ret, prev = capture.read()
                print(ret)
                if ret == True:
                    cv2.imshow('video', prev)
                else:
                    break
                if cv2.waitKey(20) == 27:
                    break
        cv2.destroyAllWindows()


def compress_image(infile, outfile='', mb=150, step=10, quality=80):
    """不改变图片尺寸压缩到指定大小
    :param infile: 压缩源文件
    :param outfile: 压缩文件保存地址
    :param mb: 压缩目标，B
    :param step: 每次调整的压缩比率 最小压缩比例要大于0
    :param quality: 初始压缩比率
    :return: 压缩文件地址，压缩文件大小
    """
    o_size = os.path.getsize(infile)
    if o_size <= mb:
        return infile
    outfile = get_outfile(infile, outfile)
    while o_size > mb:
        im = Image.open(infile)
        im.save(outfile, quality=quality)
        if quality - step < 0:
            break
        quality -= step
        o_size = os.path.getsize(outfile)
    return outfile, os.path.getsize(outfile)


def get_outfile(infile, outfile):
    if outfile:
        return outfile
    dir, suffix = os.path.splitext(infile)
    outfile = '{}-out{}'.format(dir, suffix)
    return outfile


if __name__ == '__main__':
    # t2 = threading.Thread(target=run, args=("t2", ""))
    # t2.start()
    # t2 = threading.Thread(target=run, args=("t2", ""))
    # t2.start()

    # index = 0

    # while True:
    #     path = "C:\\Users\\zzd\\Desktop\\10.20\\cache\\1603167221516.bmp"
    #     img = cv2.imread(path)
    #     videowriter.write(img)
    #     if index > 1000000:
    #         break
    #     else:
    #         index = index + 1
    pic_name = compress_image("C:\\Users\\zzd\\Desktop\\10.26\\target.jpg", '',50*1024)
    print(pic_name[0])

