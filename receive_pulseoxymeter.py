import serial
import time
import sys
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import QThread, Qt, QObject, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Create a matplotlib window
class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.subplots_adjust(hspace=1)
        self.axes1 = fig.add_subplot(211)
        self.axes2 = fig.add_subplot(212)
        super(MplCanvas, self).__init__(fig)

# Create a worker class
class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    hr_value = pyqtSignal(str)
    spo2_value = pyqtSignal(str)
    add_spo2_point = pyqtSignal(float)
    add_hr_point = pyqtSignal(float)

    def recieve_message(self):
    # read data comming from microcontroller
        no_activity = 0
        self.progress.emit("Recieving!")

        try:
            channel = serial.Serial(port, baudrate = 115200, bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE,timeout=None)
        except serial.serialutil.SerialException:
            self.progress.emit(f"ERROR: CANNOT OPEN SERIAL PORT {port}!")
            self.finished.emit()
            return

        while(1):
            if (channel.inWaiting() > 0):
                no_activity = 0
                data_str = channel.readline().decode('utf-8')

                # We can also print every message in terminal for debuggin purposes,
                # uncomment if necessary

                # print("************")
                # print(data_str)
                # print("************")

                if "hr" in data_str:
                    self.hr_value.emit(data_str)
                    hr = float(data_str[2:])
                    self.add_hr_point.emit(hr)
                elif "spo2" in data_str:
                    self.spo2_value.emit(data_str)
                    spo2 = float(data_str[4:])
                    self.add_spo2_point.emit(spo2)
                else:
                    self.progress.emit("Unexpected message:" + data_str)
                    self.finished.emit()

            elif no_activity == 500:
                self.progress.emit(f"5 seconds of no messages, recieveing stopped!")
                break
            else:
                no_activity += 1
                time.sleep(0.01)
                
        self.finished.emit()
    

class Window(QMainWindow):
    '''
        Main window of the GUI
    '''
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()

    def setupUi(self):
        self.setWindowTitle("HR AND SPO2 PLOTTER")
        self.resize(1000, 600)
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self.receive_label = QLabel("Run recieving!")
        self.receive_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.receive_label.setFont(QFont('Ubuntu',20))
        self.spo2_label = QLabel("prediction:", self)
        self.spo2_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.spo2_label.setFont(QFont('Ubuntu',16))
        self.hr_params_label = QLabel("HR: , MEAN_RR_INT: , SDNN: , RMSSD: ", self)
        self.hr_params_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.hr_params_label.setFont(QFont('Ubuntu',16))
        self.recieve_button = QPushButton("Recieve data", self)
        self.recieve_button.clicked.connect(self.recieve_thread)
        self.recieve_button.setFont(QFont('Ubuntu',12))

        self.canvas = MplCanvas(self, width=5, height=10, dpi=100)
        n_data = 20
        self.xdata1 = list(range(n_data))
        self.ydata1 = [-0.2]*n_data
        self.canvas.axes1.set_title("SPO2")
        self.canvas.axes1.set_ylim((0,101))
        self.canvas.axes1.set_ylabel('Spo2')
        self.canvas.axes1.set_xlabel('Percentage')

        self.xdata2 = list(range(n_data))
        self.ydata2 = [-0.2]*n_data
        self.canvas.axes2.set_ylim((40,150))
        self.canvas.axes2.set_title("Heart rate")
        self.canvas.axes2.set_ylabel('bpm')
        self.canvas.axes2.set_xlabel('Samples')

        self._plot_ref1 = None
        self.update_spo2_plot(0)
        self._plot_ref2 = None
        self.update_hr_plot(35)
        self.show()

        # Set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.receive_label)
        layout.addStretch(1)
        layout.addWidget(self.spo2_label)
        layout.addStretch(1)
        layout.addWidget(self.hr_params_label)
        layout.addStretch(1)
        layout.addWidget(self.recieve_button)
        self.centralWidget.setLayout(layout)


    # functions for displaying output
    def report_progress(self, message):
        self.receive_label.setText(message)


    def update_hr(self, message):
        self.hr_params_label.setText(message.strip() + "bpm")


    def updade_spo2(self, message):
        self.spo2_label.setText(message.strip() + "%")


    def update_hr_plot(self,hr):
        # Drop off the first y element, append a new one.
        self.ydata2 = self.ydata2[1:] + [hr]
        # self.xdata += 1
        # Note: we no longer need to clear the axis.
        if self._plot_ref2 is None:
            # First time we have no plot reference, so do a normal plot.
            # .plot returns a list of line <reference>s, as we're
            # only getting one we can take the first element.
            plot_refs2 = self.canvas.axes2.plot(self.xdata2, self.ydata2, color='r',linestyle='--', marker='o')
            self._plot_ref2 = plot_refs2[0]
        else:
            # We have a reference, we can use it to update the data for that line.
            self._plot_ref2.set_ydata(self.ydata2)
        # Trigger the canvas to update and redraw.
        self.canvas.draw()


    def update_spo2_plot(self,spo2):
        # Drop off the first y element, append a new one.
        self.ydata1 = self.ydata1[1:] + [spo2]
        # self.xdata += 1
        # Note: we no longer need to clear the axis.
        if self._plot_ref1 is None:
            # First time we have no plot reference, so do a normal plot.
            # .plot returns a list of line <reference>s, as we're
            # only getting one we can take the first element.
            plot_refs1 = self.canvas.axes1.plot(self.xdata1, self.ydata1, color='b',linestyle='--', marker='o')
            self._plot_ref1 = plot_refs1[0]
        else:
            # We have a reference, we can use it to update the data for that line.
            self._plot_ref1.set_ydata(self.ydata1)
        # Trigger the canvas to update and redraw.
        self.canvas.draw()


    def recieve_thread(self):
        """Long-running task in 5 steps."""
        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = Worker()
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.recieve_message)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.report_progress)
        self.worker.hr_value.connect(self.update_hr)
        self.worker.spo2_value.connect(self.updade_spo2)
        self.worker.add_spo2_point.connect(self.update_spo2_plot)
        self.worker.add_hr_point.connect(self.update_hr_plot)
        # Step 6: Start the thread
        self.thread.start()

        # Final resets
        self.recieve_button.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.recieve_button.setEnabled(True)
        )

        self.thread.exit()


if __name__ == '__main__':
    '''
        channel settings, 
        the port has to be set here
    '''
    port = '/dev/ttyUSB0'

    for i in sys.argv:
        if "--port=" in i:
            port = port = i[7:]

    app = QApplication(sys.argv)

    main = Window()
    main.show()

    sys.exit(app.exec_())
