from appgui import Ui_MainWindow
from spincore_wrapper import *
from PulseSequence import PulseSequence
from PyQt5 import  QtWidgets,QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication
import sys
import qdarkstyle


class PB_app(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        # create and setup the UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #Instantiate required classes, start threads, and create required instruction list which will be filled later
        self.pulse_sequence = PulseSequence()
        self.instructions = []
        self.pb_thread = CommunicateWithPB()

        #Connect PB_app GUI buttons for pulse train generator tab
        self.ui.add_pulse_train.clicked.connect(self.add_pulse_train)
        self.ui.delete_pulse_train.clicked.connect(self.delete_pulse_train)
        self.ui.generate_instr.clicked.connect(self.generate_instructions)
        self.ui.load_instr.clicked.connect(self.generate_instructions_from_file)
        self.ui.save_instr.clicked.connect(self.write_instructions)
        self.ui.clear.clicked.connect(self.clear_status)

        #Connect PB_app GUI buttons for pulse blaster control tab
        self.ui.get_pb_status.clicked.connect(self.pb_thread.get_pb_status)
        self.ui.init_pb.clicked.connect(self.pb_thread.init_pb)
        self.ui.close_pb.clicked.connect(self.pb_thread.close_pb)
        self.ui.send_pb_instructions.clicked.connect(self.pb_thread.send_pb_instructions)
        self.ui.start_pulse_sequence.clicked.connect(self.pb_thread.start_pulse_sequence)
        self.ui.stop_pulse_sequence.clicked.connect(self.pb_thread.stop_pulse_sequence)
        self.ui.clear_messages.clicked.connect(self.clear_messages)

        #Connect message signal coming from pulseblaster class
        self.pb_thread.message.connect(self.message)




    def add_pulse_train(self):
        try:
            time_on = self.ui.on_time.text()
            width = self.ui.width.text()
            separation = self.ui.separation.text()
            num_of_pulses = int(self.ui.num_of_pulses.text())
            channels = [int(x) for x in ((self.ui.channels).text()).split(',')]

            self.pulse_sequence.add_pulse_train(time_on= time_on, width=width,separation=separation,
                                                pulses_in_train=num_of_pulses,channels=channels)

            self.pulse_sequence.set_first_sequence_event()
            if(self.pulse_sequence.first_sequence_event <= 12.5 and self.pulse_sequence.first_sequence_event != 0):
                try:
                    self.pulse_sequence.assertion(self.pulse_sequence.first_sequence_event)
                except:
                    self.pulse_sequence.delete_pulse_train(
                    pulse_train_index=self.pulse_sequence.pulse_trains[-1].pulse_train_index)
                    self.pulse_sequence.pulse_train_index -= 1
                    self.ui.status.append("First event has to start at 0ns or after 2.5ns")
                    raise Exception("First event has to start at 0ns or after 2.5ns")



            if(self.pulse_sequence.has_coincident_events()):
                self.pulse_sequence.delete_pulse_train(pulse_train_index=self.pulse_sequence.pulse_trains[-1].pulse_train_index)
                self.pulse_sequence.pulse_train_index -= 1
                self.ui.status.append("Overlapping Pulses not allowed")
                raise Exception("Overlapping Pulses not allowed")

            self.ui.status.append("Pulse %s succesfully added" % str(int(self.pulse_sequence.pulse_train_index)-1))
            self.ui.Num_of_pulse_trains.display(self.pulse_sequence.num_of_pulse_trains)
        except:
            self.ui.status.append("Pulse not added")

        self.display_pulse_sequence()




    def delete_pulse_train(self):
        try:
            pulse_index = int(self.ui.pulse_index.text())
            if not(self.pulse_sequence.delete_pulse_train(pulse_train_index=pulse_index)):
                raise Exception("Invalid Pulse Index")
            self.ui.status.append("Pulse %s succesfully deleted" % pulse_index)
            self.ui.Num_of_pulse_trains.display(self.pulse_sequence.num_of_pulse_trains)
        except:
            self.ui.status.append("Invalid Pulse Index")

        self.display_pulse_sequence()

    def display_pulse_sequence(self):
        self.ui.pulses_in_sequence.setPlainText("")
        for pulse in self.pulse_sequence.pulse_trains:
            display_width = pulse.width_val
            display_time_on = pulse.time_val
            display_sep_val = pulse.sep_val
            display_channels = str(pulse.channels)
            display_num_of_pulses = pulse.pulses_in_train
            display_pulse_index = pulse.pulse_train_index

            self.ui.pulses_in_sequence.append("Pulse: [index: %s, On: %s, width: %s, "
                                              "separation: %s, num_of_pulses: %s, channels: "
                                              "%s]" % (display_pulse_index, display_time_on, display_width,
                                                       display_sep_val, display_num_of_pulses, display_channels))



    def generate_instructions(self):
        try:
            self.instructions = self.pulse_sequence.generate_instructions()
            self.ui.status.append("Instructions generated succesfully")
            self.pb_thread.instructions = self.instructions
        except:
            self.ui.status.append("Instructions not generated")

    def write_instructions(self):
        file_name = self.ui.filename.text()
        try:
            self.pulse_sequence.write_instruction_file(filename=file_name)
            self.ui.status.append("Instruction file written succesfully")
        except:
            self.ui.status.append("Instruction file not generated")

    def generate_instructions_from_file(self):
        file_name = self.ui.filename.text()
        try:
            self.instructions = self.pulse_sequence.generate_instructions_from_file(filename=file_name)
            self.ui.status.append("Instructions generated succesfully")
            self.pb_thread.instructions = self.instructions
        except:
            self.ui.status.append("Instructions not generated")

    def clear_status(self):
        self.ui.status.clear()

    def message(self,text):
        self.ui.messages.append(text)

    def clear_messages(self):
        self.ui.messages.clear()



class CommunicateWithPB(QtCore.QThread):

    message = QtCore.pyqtSignal(str)

    def __init__(self,parent = None,instructions=None):
        super().__init__(parent)
        self.instructions = instructions


    def init_pb(self):
        self.message.emit("Copyright (c) 2015 SpinCore Technologies, Inc.")
        self.message.emit("Using SpinAPI Library version %s" % pb_get_version())
        self.message.emit("Found %d boards in the system.\n" % pb_count_boards())

        if(pb_init()==0):
            self.message.emit("PulseBlaster successfully Initialized")
        else:
            error = pb_get_error()
            self.message.emit(error)


    def get_pb_status(self):
        status = pb_status()
        self.message.emit(status)


    def close_pb(self):
        if (pb_close() == 0):
            self.message.emit("PulseBlaster successfully closed")
        else:
            error = pb_get_error()
            self.message.emit(error)


    def send_pb_instructions(self):
        try:
            pb_start_programming(PULSE_PROGRAM)

            for instruction in self.instructions:
                instr_type = instruction[1]

                if(instr_type=='LOOP'):
                    flag = eval(instruction[0])
                    instr = eval(instruction[1])
                    instr_data = int(instruction[2])
                    time = float(instruction[3])
                    loop = pb_inst_pbonly(flag,instr,instr_data,time)

                elif(instr_type=='END_LOOP'):
                    flag = eval(instruction[0])
                    instr = eval(instruction[1])
                    instr_data = loop
                    time = float(instruction[3])
                    pb_inst_pbonly(flag,instr,instr_data,time)

                else:
                    flag = eval(instruction[0])
                    instr = eval(instruction[1])
                    instr_data = int(instruction[2])
                    time = float(instruction[3])
                    pb_inst_pbonly(flag,instr,instr_data,time)

            pb_stop_programming()

            self.message.emit("PulseBlaster successfully programmed")

        except:
            self.message.emit("PulseBlaster not programmed")
            error = pb_get_error()
            self.message.emit(error)


    def start_pulse_sequence(self):
        pb_reset()
        if (pb_start() == 0):
            self.message.emit("Pulse sequence started")
        else:
            error = pb_get_error()
            self.message.emit(error)


    def stop_pulse_sequence(self):
        if (pb_stop() == 0):
            self.message.emit("Pulse sequence stopped, Don't forget to close the board!")
        else:
            error = pb_get_error()
            self.message.emit(error)






if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
    app.setStyleSheet(dark_stylesheet)
    myapp = PB_app()
    myapp.show()
    sys.exit(app.exec_())