#!/usr/bin/python3

# from msvcrt import locking
import os
import socket
import time
import random
import subprocess
from subprocess import Popen, PIPE, STDOUT
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

# execute bash script named dingtalkcheckin.sh
# subprocess.call(["./dingtalkcheckin.sh"])


# the location of android adb
adbHome = '/opt/adb/'

# define tmp xml file for adb ui dump
tmpXmlFile = '/tmp/adb_ui_dump.xml'

# define screenshot directory
screenShotFile = '/tmp/adb_screenshot_{}.png'.format(random.randint(1000, 9999))

def getDevList():
    devList = []
    cmdStr = adbHome + "adb devices -l | sed 1d | awk '{print $1}'"
    for line in Popen(cmdStr, shell=True, stdout=PIPE, stderr=STDOUT).stdout.readlines():
        tmpStr = line.decode().strip('\n')
        if not tmpStr:
            continue
        devList.append(tmpStr)
    return devList



class androidConsole(object):
    def __init__(self, devID, appName, appActvName, appRunningKeyword='"通讯录"'):
        # Change devices ID to Serial No., in case of wrong value.
        self.devID = devID
        self.appName = appName
        self.appActvName = appActvName
        self.appRunningKeyword = appRunningKeyword
        self.screenshotName = screenShotFile
        self.tmpFile = tmpXmlFile
        self.adbHome = adbHome
        self.screenShotPhoneFile = '/sdcard/screen_{}.png'.format(random.randint(1000, 9999))
        self.screenShotLocalFile = screenShotFile
        self.midPoint = self.getMidOfScreen()

    def sendCommand(self, cmdStr):
        # Light on the screen, send keyevent 224
        os.system(self.adbHome + 'adb -s {} shell input keyevent 224'.format(self.devID))

        cmdStr = self.adbHome + 'adb -s ' + self.devID + ' ' + cmdStr
        if not os.system(cmdStr):
            return True
        else:
            return False

    def getIconOrTextPointer(self, textString):
        """
        os.system(adbHome + 'adb shell am force-stop com.android.ddmlib' + '&>/dev/null')
        cmdStr = adbHome + "adb pull `" + adbHome + "adb shell uiautomator dump | awk -F': ' '{print $0}'` " + tmpDir
        """
        if not textString or textString == '""':
            return []
        cmdStr = 'exec-out uiautomator dump /dev/tty > ' + self.tmpFile
        if not self.sendCommand(cmdStr):
            return []
        uiData = ''
        if not os.path.isfile(self.tmpFile):
            return []
        try:
            with open(self.tmpFile, 'r') as f:
                uiData += f.readline()
            f.close()
        except FileNotFoundError:
            print('Read Temp XML File Error.')
            return []
        os.system('rm -rf ' + self.tmpFile)
        uiData = uiData.split('<')
        for line in uiData:
            if textString in line:
                """
                pointer = line.split()[-2]
                pointer = pointer.split('=')[-1].strip('"').strip('[').strip(']').split('][')[0].split(',')
                return [str(int(pointer[0]) + xOffset), str(int(pointer[1]) + yOffset)]
                """
                # get bounds point of the icon, return the intermediate value.
                point0 = line.split()[-2].strip('bounds=').strip('"').strip(']').strip('[').split('][')[0].split(',')
                point1 = line.split()[-2].strip('bounds=').strip('"').strip(']').strip('[').split('][')[-1].split(',')
                return [str((int(point0[0]) + int(point1[0])) // 2), str((int(point0[1]) + int(point1[1])) // 2)]
        return []

    def launchApp(self):
        return self.sendCommand('shell am start -n ' + self.appActvName + '&>/dev/null')

    def shutdownApp(self):
        return self.sendCommand('shell am force-stop ' + self.appName)

    def isAppInstalled(self):
        return self.sendCommand('shell pm list packages | grep ' + self.appName + '&>/dev/null')

    def isAppLaunched(self):
        if self.getIconOrTextPointer('text="权限申请"'):
            self.tapScreen(self.getIconOrTextPointer('text="取消"'))
        # return sendCommand(adbHome + 'adb shell ps | grep ' + appName + '&>/dev/null')
        return self.getIconOrTextPointer(self.appRunningKeyword)

    def returnBack(self):
        return self.sendCommand('shell input keyevent KEYCODE_BACK')

    def returnHome(self):
        return self.sendCommand('shell input keyevent KEYCODE_HOME')

    def powerOn(self):
        return self.sendCommand('shell input keyevent POWER')

    def screenOff(self):
        return self.sendCommand('shell input keyevent 223')

    def tapScreen(self, pointer):
        if len(pointer) != 2:
            return False
        return self.sendCommand('shell input tap ' + pointer[0] + ' ' + pointer[1])

    def swapUpQuarterScreen(self):
        xPoint = self.midPoint[0]
        yPoint = self.midPoint[-1]
        try:
            toYPoint = str(int(yPoint) // 1)
        except ValueError:
            return False
        return self.sendCommand('shell input swipe ' + xPoint + ' ' + yPoint + ' ' + xPoint + ' ' + toYPoint)

    def swapDownQuarterScreen(self):
        xPoint = self.midPoint[0]
        yPoint = self.midPoint[-1]
        try:
            toYPoint = str(int(yPoint) // 1)
        except ValueError:
            return False
        return self.sendCommand('shell input swipe ' + xPoint + ' ' + toYPoint + ' ' + xPoint + ' ' + yPoint)

    def screenShot(self):
        if self.sendCommand('shell screencap {}'.format(self.screenShotPhoneFile)):
            return self.sendCommand('pull {} {}'.format(self.screenShotPhoneFile, self.screenShotLocalFile) + ' &>/dev/null')
        else:
            return False

    def setScreenOnSecs(self, sec):
        try:
            int(sec)
        except ValueError:
            return False
        return self.sendCommand('shell settings put system screen_off_timeout ' + str(int(sec * 59998)))

    def lightOnScreenAndWait(self, times=0):
        count = 0
        if not times:
            times = 1
        else:
            times *= 2
        while True:
            count += 1
            self.sendCommand('shell input keyevent 224')
            # time.sleep(0.5)
            if count >= times:
                return True

    def getMidOfScreen(self):
        cmdStr = self.adbHome + "adb -s {} shell wm size".format(self.devID)
        wmSize = Popen(cmdStr, shell=True, stdout=PIPE, stderr=STDOUT).stdout.read().decode()
        if 'size:' in wmSize:
            fullSize = wmSize.split('size:')[-1].strip().split('x')
            return [str(int(fullSize[0]) // 2), str(int(fullSize[1]) * 3 // 5)]
        else:
            return []
class dingdingConsole(androidConsole):
    def __init__(self, devID, coName, waitSecs=random.randint(60, 600)):
        self.devID = devID
        self.coName = coName
        self.appName = 'com.alibaba.android.rimet'
        self.appActvName = 'com.alibaba.android.rimet/.biz.LaunchHomeActivity'
        self.waitSecs = waitSecs
        androidConsole.__init__(self, self.devID, self.appName, self.appActvName)

    def getCurrentCompany(self):
        cmdStr = 'exec-out uiautomator dump /dev/tty > ' + self.tmpFile
        if not self.sendCommand(cmdStr):
            return ''
        uiData = ''
        try:
            with open(self.tmpFile, 'r') as f:
                uiData += f.readline()
            f.close()
        except FileNotFoundError:
            print('Temp File Not Found.')
            return ''
        os.system('rm -rf ' + self.tmpFile)
        for line in uiData.split('<'):
            keyword = 'com.alibaba.android.rimet:id/menu_current_company'
            keyword = 'com.alibaba.android.rimet:id/tv_org_name'
            if keyword in line:
                for statement in line.split():
                    if 'text' in statement:
                        return statement.strip().split('"')[-2]
        return ''

    def changeCurrCo(self, currCoName, toCoName):
        if not currCoName or not toCoName:
            return False
        try:
            self.tapScreen(self.getIconOrTextPointer(currCoName))
        except ValueError:
            return False
        try:
            self.tapScreen(self.getIconOrTextPointer(toCoName))
        except ValueError:
            return False
        # add method to verify if changed successfully.
        if self.getCurrentCompany() == toCoName:
            return True
        else:
            return False

    def getWorkConsoleIcon(self):
        xPointer = ''
        yPointer = ''
        try:
            leftPointer = self.getIconOrTextPointer('"协作"')
            rightPointer = self.getIconOrTextPointer('"通讯录"')
            yPointer = leftPointer[1]
            xPointer = str((int(rightPointer[0]) - int(leftPointer[0])) // 2 + int(leftPointer[0]))
        except IndexError:
            return []
        pointer = [xPointer, yPointer]
        return pointer

    def launchDingDing(self):
        return self.launchApp()

    def isDingDingRunning(self):
        return self.isAppLaunched()

    def shutdownDingDing(self):
        return self.shutdownApp()

    def checkIn(self, wechatUser=''):
        print('-'*20 + 'Check in start' + '-'*20)
        # os.system('date "+%y/%m/%d %H:%M:%S" | ' + "awk '{print \"Started at: \"$1\" \"$2}'")
        print('Started at: ', time.strftime('%Y/%m/%d %A %H:%M:%S'))
        screen_off_time = 1800
        print('Set system screen off timeout {}s: '.format(screen_off_time), end='', flush=True)
        if self.setScreenOnSecs(1800):
            print('Passed')
        else:
            print('Failed')

        print('Check Android devices list: ', end='', flush=True)
        # if sendCommand('devices -l | grep -v "List of devices attached" | grep -v "^$" &>/dev/null'):
        if self.sendCommand('devices -l | grep "{}" &>/dev/null'.format(self.devID)):
            print('Passed')
        else:
            print('Failed, connect Android device to this computer.')
            return False

        print('Generate random seconds for waiting: ', end='', flush=True)
        print(str(self.waitSecs) + 's')
        time.sleep(self.waitSecs)

        print('Shutdown DingTalk: ', end='', flush=True)
        self.shutdownDingDing()
        self.shutdownDingDing()
        while True:
            if self.isDingDingRunning():
                self.shutdownDingDing()
                self.lightOnScreenAndWait(1)
            else:
                print('Passed')
                break

        print('Launch DingTalk: ', end='', flush=True)
        self.launchDingDing()
        self.lightOnScreenAndWait(3)
        while True:
            if self.isDingDingRunning():
                print('Passed')
                break
            else:
                self.lightOnScreenAndWait(1)
                self.launchDingDing()

                # modify
        print('Tap work console icon: ', end='', flush=True)
        # tapScreen(getIconOrTextPointer('工作台'))
        # tapScreen(getIconOrTextPointer('home_bottom_tab_text'))
        self.tapScreen(self.getWorkConsoleIcon())
        while True:
            currentCoName = self.getCurrentCompany()
            if currentCoName:
                print('Passed')
                break
            else:
                self.lightOnScreenAndWait()
                self.tapScreen(self.getWorkConsoleIcon())

        print('Verify if the current company is {}: '.format(self.coName), end='', flush=True)
        if currentCoName == self.coName:
            print('Passed')
        else:
            print('Failed')
            print('Change to company {}: '.format(self.coName), end='', flush=True)
            while True:
                if self.changeCurrCo(currentCoName, self.coName):
                    print('Passed')
                    break
                else:
                    self.lightOnScreenAndWait(1)

        print('Tap check in icon: ', end='', flush=True)
        while True:
            checkInIcon = self.getIconOrTextPointer('"考勤打卡"')
            if not checkInIcon:
                self.lightOnScreenAndWait(1)
            else:
                if checkInIcon[1] <= '194':
                    self.swapDownQuarterScreen()
                if checkInIcon[1] >= '1700':
                    self.swapUpQuarterScreen()
                checkInIcon = self.getIconOrTextPointer('考勤打卡')
                self.tapScreen(checkInIcon)
                print('Passed')
                break

        """# add method to verify if the big icon is exit.
        print('Verify if the current page is the one we wanted: ', end='', flush=True)
        # This page return 'ERROR: could not get idle state.'
        while True:
            if not self.getIconOrTextPointer(self.coName):
                print('Passed')
                break
            else:
                self.lightOnScreenAndWait(1)"""
        self.lightOnScreenAndWait(5)

        print('Finally, check in: ', end='', flush=True)
        self.tapScreen(self.midPoint)
        self.lightOnScreenAndWait(1)
        self.tapScreen(self.midPoint)
        self.lightOnScreenAndWait(1)

        # continueIcon = ['818', '1114']
        continueIcon = self.getIconOrTextPointer('text="继续打卡"')
        if continueIcon:
            continueIcon = self.getIconOrTextPointer('text="继续打卡"')
            print('ORG changed before, continue check in.')
            self.tapScreen(continueIcon)
            self.lightOnScreenAndWait(1)
            self.tapScreen(continueIcon)
        else:
            print('Passed')

        print('Take screenshot & return home screen: ', end='', flush=True)
        self.lightOnScreenAndWait(1)
        self.screenShot()
        self.lightOnScreenAndWait(1)
        if self.returnHome():
            print('Passed')
        else:
            print('Failed')

        # sendMail(self.coName, subject='通知：{}打卡记录自动发送'.format(self.coName), image=self.screenShotLocalFile)
        # wechatCon = wechatConsole(self.devID)
        # coNameEng = pinyin.get(self.coName, format='strip', delimiter='')
        # Capitalize the first letter of the string
        coNameEng = coNameEng.replace(coNameEng[0], coNameEng[0].upper(), 1)
        # wechatCon.sendMsg2one(wechatUser, '{} checked in at: {}.'
        #                       .format(coNameEng, time.strftime("%m/%d %a %H:%M")), lastPic=True)
        self.returnHome()
        self.screenOff()
        print('-'*20 + 'Check in done' + '-'*20)


def isWorkday(date8bits=''):
    # nothing input, TODAY default.
    thisDay = time.strftime('%Y%m%d')
    # week number from '0' -- '6'
    thisWeekNum = time.strftime('%w')

    if date8bits:
        thisDay = date8bits
        from datetime import datetime
        try:
            thisWeekNum = datetime.strptime(date8bits, '%Y%m%d').strftime('%w')
        except ValueError:
            return 'Error'

    holidays = ['20210919', '20210920', '20210921',  # Mid-Autumn Festival
                '20211001', '20211002', '20211003', '20211004', '20211005', '20211006', '20211007',  # National Day
                '20220101', '20220102', '20220103',  # The New Year
                '20220131', '20220201', '20220202', '20220203', '20220204', '20220205', '20220206',  # The Spring Festival
                '20220403', '20220404', '20220405',  # The Tomb-sweeping Day
                '20220502', '20220503', '20220504',  # The International Labor Day
                '20220603',  # The Dragon Boot Festival
                '20220912',  # The Mid-Autumn Festival
                '20221003', '20221004', '20221005', '20221006', '20221007'  # the National Day
                ]

    workdayInWeekend = ['20210918',  # Mid-Autumn Festival
                        '20210926', '20211009',  # National Day
                        '20220129', '20220130',  # The Spring Festival
                        '20220402',  # The Tomb-sweeping Day
                        '20220424',  # The International Labor Day
                        '20220507',  # The International Labor Day
                        '20221008', '20221009'  # The National Day
                        ]

    # return 'holiday' or 'workday'
    if thisDay in workdayInWeekend:
        return True
    elif thisDay in holidays or thisWeekNum in ['6', '0']:
        return False
    return True


if __name__ == '__main__':
    devid = getDevList()[0]

    # wechat_user = '微信接受人'
    compName = '企业全称（钉钉显示为准）'

    # will not be executed while TODAY is holiday or weekend.
    if not isWorkday():
        print('Today "{}" is not workday.'.format(time.strftime('%Y/%m/%d')))
        exit(-1)

    ddConsole = dingdingConsole(devid, compName, waitSecs=1)
    # ddConsole.checkIn(wechatUser=wechat_user)