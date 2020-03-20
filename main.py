#sudo chmod 666 /dev/ttyUSB0
from ui import *
import sys

import time
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage 
from PyQt5.QtCore import  QObject, QThread, pyqtSignal, Qt, QMutex

#import qrcode


try:
    from pydobot import Dobot
except Exception as e:
    print(e)
import cv2
import pyrealsense2 as rs
import numpy as np

#import yolov3
#import darknet

class MySignal(QObject):  # global signal 
    sig = QtCore.pyqtSignal()


signal = MySignal()

class suck_thread(QThread):
    def set_device(self, device):
        self.device = device

    def suck_run(self, bool):
        while(bool):
            self.device.suck(True)    


class Thread(QThread):
    changePixmap = pyqtSignal(QtGui.QImage)

    def run(self):
        global signal
        self.i = 0
        signal.sig.connect(self.save_img)
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        #config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)
        self.pipeline.start(self.config)
        
        while True:
            frames = self.pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if  not color_frame:
                continue

            self.color_image = np.asanyarray(color_frame.get_data())
            self.img = self.color_image
            h, w, ch = self.color_image.shape
            bytesPerLine = ch * w
           
            
            cv2.cvtColor(self.color_image, cv2.COLOR_RGB2BGR, self.color_image)
            #cv2.COLOR_RGB2BGR

            try:    
                convertToQtFormat = QtGui.QImage(self.color_image.data, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)
                p = convertToQtFormat.scaled(1280, 720, Qt.KeepAspectRatio)
                self.changePixmap.emit(p)
            except Exception as e:
                print("stop after detect")
                print(e)


        
    def save_img(self):
        cv2.cvtColor(self.img, cv2.COLOR_RGB2BGR, self.img)
        cv2.imwrite(str(self.i)+'.jpg', self.img)
        self.i +=1
        print("save: "+str(self.i)+"\n")

    def stop(self):
        self.pipeline.stop()
        self.quit()

    

class MainWindow(QtWidgets.QMainWindow, Ui_Form):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent=parent)
        self.setupUi(self)

        self.user_set_pos = (0 ,0 ,0, 0)
        
        print("開始自動尋找dobot所在的port\n")
        self._connect_dobot(0)
        self._init_ui_connect()
        try :
            self.get_pos()
        except Exception as e:
            pass     
        self.waitTime=2
    
    def _connect_dobot(self,i):
        try:
            portArray=["/dev/ttyUSB0","/dev/ttyUSB01","/dev/ttyUSB2","/dev/ttyUSB3","/dev/ttyUSB4","/dev/ttyUSB5","/dev/ttyS0","/dev/ttyS1","/dev/ttyS2","/dev/ttyS3","/dev/ttyS4","/dev/ttyS5"]
            self.device=Dobot(port=portArray[i],verbose=False)
            print("連接成功")
        except Exception as e:
            print("無法在"+portArray[i]+"連接Dobot\n原因:"+str(e))
	
            if(i<len(portArray)-1):
                print("沒關係的別驚慌,我會嘗試連接下一個port\n")
                self._connect_dobot(i+1)
            else:
                print("連接失敗，請檢查是否有將dobot接上USB")

    def suck_enable(self):
        while(1):
            self.device.suck(True)
    def suck_free(self):
        self.device.suck(False)


    def _init_ui_connect(self):
        _translate = QtCore.QCoreApplication.translate


        self.label.resize(1280,720)
        self.label.move(0,0)


        self.btn_suck.clicked.connect(self.suck_enable)
        self.btn_suck.clicked.connect(self.suck_free)

    
        self.interval = 1
        self.input_interval.textEdited.connect(self.set_inputinterval)
        self.btn_x_increase.clicked.connect(lambda: self.move_xyz(self.interval, 0, 0))
        self.btn_x_reduce.clicked.connect(lambda: self.move_xyz(-self.interval, 0, 0))
        self.btn_y_increase.clicked.connect(lambda: self.move_xyz(0, self.interval, 0))
        self.btn_y_reduce.clicked.connect(lambda: self.move_xyz(0, -self.interval, 0))
        self.btn_z_increase.clicked.connect(lambda: self.move_xyz(0, 0, self.interval))
        self.btn_z_reduce.clicked.connect(lambda: self.move_xyz(0, 0, -self.interval))

        self.stream_thread = Thread(self)
        self.stream_thread.changePixmap.connect(self.setImage)
        self.stream_thread.start()



    @QtCore.pyqtSlot(QtGui.QImage) 
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))
        self.update()

        
    def mousePressEvent(self, event):
        x = event.x()
        y = event.y()
        if x <= 1280 and y <= 720:
            #print (x,y)
            self.label_X.setText(str(x))
            self.label_Y.setText(str(y))
            self.update()

    def set_inputinterval(self, content):
        
        self.interval = float(content)
      
    def closeEvent(self, event):
        self.stream_thread.stop()



    def save_img(self):
        global signal
        signal.sig.emit()

    def set_pos():
        x = float(self.X_edit.text())
        y = float(self.Y_edit.text())
        z = float(self.Z_edit.text())
        r = float(self.R_edit.text())
        self.user_set_pos = (x, y, z, r)
        try:
            self.device.move_to(x, y, z, r, wait=True)
        except Exception as e:
                print("輸入格式錯誤")
                print("錯誤訊息： "+str(e))    

    def get_pos():
        _translate = QtCore.QCoreApplication.translate
        try:
            (x,y,z,r,j1,j2,j3,j4)=self.device.pose()

        except Exception as e:
            pass

          
        self.X_output.setText(_translate("Form", str(round(x))))
        self.Y_output.setText(_translate("Form", str(round(y))))
        self.Z_output.setText(_translate("Form", str(round(z))))
        self.R_output.setText(_translate("Form", str(round(r))))

        self.X_edit.setText(_translate("Form", str(round(x)) ) )
        self.Y_edit.setText(_translate("Form", str(round(y)) ) )
        self.Z_edit.setText(_translate("Form", str(round(z)) ) )
        self.R_edit.setText(_translate("Form", str(round(r)) ) )

        return (x, y ,z)    
    


    def move_xyz(self, x_, y_, z_):
        (x,y,z) = self.get_pos()   
        self.device.move_to(x+ x_, y +y_, z+z_, 0) 

    


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    #w = MyPopup()
    w.show()
    sys.exit(app.exec_())
