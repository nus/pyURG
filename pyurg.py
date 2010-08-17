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

class UrgDevice(object):
    def __del__(self):
        self.laser_off()
        if not self.is_open():
            self.SerUrg.close()

    def connect(self, dev_name = '/dev/ttyACM0', band_rate = 115200, time_out = 0.1):
        '''
        URGデバイスに接続
        dev_name  : デバイス名またはポート番号
                    (Device name or port number. ex:/dev/ttyACM0 or COM1)
        band_rate : ボーレートの設定
                    (Set band rate. ex: 9600, 38400, etc.)
        time_out  : タイムアウト[s]の設定
                    (Set timeout[s])
        '''
        self.SerUrg = serial.Serial(dev_name, band_rate, timeout = time_out)
        if not self.is_open():
            return False
        # SCIP2.0プロトコルに設定
        self.set_SCIP2()
        # 測定パラメータの取得
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
        '''
        self.send_cmd('SCIP2.0\n')
        self.__receive_data()

    def get_version(self):
        '''
        バージョン情報を取得
        '''
        if not self.is_open():
            return False
        self.send_cmd('VV\n')
        get = self.__receive_data()
        return get

    def get_parameter(self):
        '''
        デバイスパラメータを取得
        '''
        if not self.is_open():
            return False
        self.send_cmd('PP\n')
        get = self.__receive_data()
        # 期待した値かどうかをチェック
        if not (get[:2] == ['PP\n', '00P\n']):
            return False
        # 必要な情報を抜き取る
        self.pp_params = {}
        for item in get[2:10]:
            tmp = re.split(r':|;', item)[:2]
            self.pp_params[tmp[0]] = tmp[1]
        return self.pp_params

    def laser_on(self):
        '''
        レーザを点灯させる。
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
        レーザの消灯をさせる。距離データを取得中でも消灯させる。
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
        '''
        data = []
        for i in range(0, len(encode_str), byte):
            split_str = encode_str[i : i+byte]
            data.append(self.__decode(split_str))
        return data
    
    def capture(self):
        if not self.laser_on():
            return False
        
        # 送信コマンドの作成
        cmd = 'GD' + self.pp_params['AMIN'].zfill(4) + self.pp_params['AMAX'].zfill(4) + '01\n'
        self.send_cmd(cmd)
        get = self.__receive_data()
        
        # 返答結果をチェック
        if not (get[:2] == [cmd, '00P\n']):
            return False
        
        # タイムスタンプのデコード
        tm_str = get[2][:-1]
        timestamp = self.__decode(tm_str)
        
        # 距離データのデコード
        length_byte = 0
        line_decode_str = ''
        if cmd[:2] == ('GS' or 'MS'):
            length_byte = 2
        elif cmd[:2] == ('GD' or 'MD'):
            length_byte = 3
        # 複数行の距離データ文字列を1行の距離データ文字列に結合する
        for line in get[3:]:
            if len(line) == 66:
                line_decode_str += line[:-2]
            elif len(line) > 2:
                line_decode_str += line[:-2]
        
        length_datas = self.__decode_length(line_decode_str, length_byte)
        return (length_datas, timestamp)
        

def main():
    urg = UrgDevice()
    if not urg.connect():
        print 'Connect error'
        exit()
    data, tm = urg.capture()
    print data

if __name__ == '__main__':
    main()
