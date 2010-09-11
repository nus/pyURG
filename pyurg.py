#!/usr/bin/env python
# -*- coding:utf-8 -*-

# The MIT License
#
# Copyright (c) 2010 Yota Ichino
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import serial
import re
import math

class UrgDevice(object):
    def __del__(self):
        self.laser_off()
        if not self.is_open():
            self.SerUrg.close()

    def connect(self, dev_name = '/dev/ttyACM0', band_rate = 115200, time_out = 0.1):
        '''
        URGデバイスに接続
        dev_name : デバイス名又はポート番号 例:/dev/ttyACM0, COM1, 他...
        band_rate: ボーレートの設定 例: 9600, 38400, 他...
        time_out : タイムアウト[s]の設定

        
        Connecting to URG device
        dev_name  : Device name or port number. ex:/dev/ttyACM0, COM1, etc...
        band_rate : Set band rate. ex: 9600, 38400, etc...
        time_out  : Set timeout[s]
        '''
        self.SerUrg = serial.Serial(dev_name, band_rate, timeout = time_out)
        if not self.is_open():
            return False
        self.set_SCIP2()
        self.get_parameter()
        return True

    def is_open(self):
        return self.SerUrg.isOpen()

    def flush_buf(self):
        self.SerUrg.flushInput()

    def send_cmd(self, cmd):
        if not self.is_open():
            return False
        self.flush_buf()
        self.SerUrg.write(cmd)
        return True

    def __receive_data(self):
        return self.SerUrg.readlines()
        
    def set_SCIP2(self):
        '''
        SCIP2.0プロトコルに設定
        Setting SCIP2.0 protcol
        '''
        self.send_cmd('SCIP2.0\n')
        self.__receive_data()

    def get_version(self):
        '''
        バージョン情報を取得
        Get version information
        '''
        if not self.is_open():
            return False
        self.send_cmd('VV\n')
        get = self.__receive_data()
        return get

    def get_parameter(self):
        '''
        デバイスパラメータの取得
        Get device parameter
        '''
        if not self.is_open():
            return False
        self.send_cmd('PP\n')
        get = self.__receive_data()
        # check expected value
        if not (get[:2] == ['PP\n', '00P\n']):
            return False
        # pick received data out of parameters
        self.pp_params = {}
        for item in get[2:10]:
            tmp = re.split(r':|;', item)[:2]
            self.pp_params[tmp[0]] = tmp[1]
        return self.pp_params

    def laser_on(self):
        '''
        レーザを点灯させる
        Tuning on the laser
        '''
        if not self.is_open():
            return False
        self.send_cmd('BM\n')
        get = self.__receive_data()
        if not(get == ['BM\n', '00P\n', '\n']):
            return False
        return True
        
    def laser_off(self):
        '''
        レーザを消灯させる。距離データを取得中でも。
        Turning on the laser regardless of getting length data
        '''
        if not self.is_open():
            return False
        self.send_cmd('QT\n')
        get = self.__receive_data()
        if not(get == ['QT\n', '00P\n', '\n']):
            return False
        return True
    
    def __decode(self, encode_str):
        '''
        エンコードされた文字列を数値に変換し返却
        Return a numeric which converted encoded string from numeric
        '''
        decode = 0
        for c in encode_str:
            decode <<= 6
            decode &= ~0x3f
            decode |= ord(c) - 0x30
        return decode

    def __decode_length(self, encode_str, byte):
        '''
        距離データをデコードしリストで返却
        Return leght data as list
        '''
        data = []
        for i in range(0, len(encode_str), byte):
            split_str = encode_str[i : i+byte]
            data.append(self.__decode(split_str))
        return data

    def index2rad(self, index):
        '''
        インデックスからラジアンに変換して返却
        Convert index to radian and reurun.
        '''
        rad = (2.0 * math.pi) * (index - int(self.pp_params['AFRT'])) / int(self.pp_params['ARES'])
        return rad
    
    def capture(self):
        if not self.laser_on():
            return [], -1

        # 送信コマンドの作成
        # make a send command
        cmd = 'GD' + self.pp_params['AMIN'].zfill(4) + self.pp_params['AMAX'].zfill(4) + '01\n'
        self.send_cmd(cmd)
        get = self.__receive_data()
        
        # 返答結果をチェック
        # checking the answer
        if not (get[:2] == [cmd, '00P\n']):
            return [], -1

        # タイムスタンプをデコード
        # decode the timestamp
        tm_str = get[2][:-1]
        timestamp = self.__decode(tm_str)
        
        # 距離データのデコード
        # decode length data
        length_byte = 0
        line_decode_str = ''
        if cmd[:2] == ('GS' or 'MS'):
            length_byte = 2
        elif cmd[:2] == ('GD' or 'MD'):
            length_byte = 3
        # 複数行の距離データ文字列を1行の距離データ文字列に結合する
        # Combine different lines which mean length data
        NUM_OF_CHECKSUM = -2
        for line in get[3:]:
            line_decode_str += line[:NUM_OF_CHECKSUM]

        # 開始インデックスまでダミーデータを入れておく
        # Set dummy data by begin index.
        self.length_data = [-1 for i in range(int(self.pp_params['AMIN']))]
        self.length_data += self.__decode_length(line_decode_str, length_byte)
        return (self.length_data, timestamp)
        

def main():
    urg = UrgDevice()
    if not urg.connect():
        print 'Connect error'
        exit()
    data, tm = urg.capture()
    print data

if __name__ == '__main__':
    main()
