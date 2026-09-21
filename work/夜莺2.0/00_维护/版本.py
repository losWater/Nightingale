# -*- coding: utf-8 -*-
"""夜莺对外版本号的唯一出处（2026-09-22）。发布目录、Release 标签、附件文件名、官网显示都从这里取。
只改对外显示的版本；方案名 yeying20、码表文件名「夜莺2.0…」是内部标识，为了老用户覆盖安装不改。
发新版时只改 VER 这一行；DATE 取发布当天。"""
import datetime
VER = '2.5'
DATE = datetime.date.today().strftime('%Y%m%d')
TAG = 'v' + VER
RELEASE_DIR = 'D:/nightingale/releases/' + TAG
