#Modified from the code written by Dr.Dutt,Brad and Connor

import numpy as np
from pathlib import Path

class PulseTrain:
    def __init__(self, time_on, width, separation, pulses_in_train, pulse_train_index,channels):


        ns = 1.0
        us = 1000.0
        ms = 1000000.0
        self.channels = channels
        self.time_val = time_on
        self.width_val = width
        self.sep_val = separation
        self.pulse_train_index = pulse_train_index
        self.time_on = float(time_on[:-2]) * eval(time_on[-2:])
        self.width = float(width[:-2]) * eval(width[-2:])
        self.separation = float(separation[:-2]) * eval(separation[-2:])
        self.pulses_in_train = pulses_in_train
        self.pulse_on_times = []
        if self.pulses_in_train == 0:
            self.separation = 0.0
        for i in range(int(pulses_in_train)):
            self.pulse_on_times.append(round(self.time_on + i * (self.width + self.separation), 10))
        self.pulse_widths = [self.width] * int(pulses_in_train)

        self.latest_pulse_train_event = round(np.amax(np.array(self.pulse_on_times)) + self.separation+self.width,10)
        self.first_pulse_train_event = round(np.amin(np.array(self.pulse_on_times)),10)

class PulseSequence:

    def __init__(self):

        self.max_instr_length = 2**(8)*2.5*1.0
        self.num_of_pulse_trains = 0
        self.pulse_train_index = 0
        self.pulse_trains = []
        self.first_sequence_event = 0

    def add_pulse_train(self, time_on='15ns', width='15ns', separation='15ns', pulses_in_train=1, channels = []):
        # add this pulse to the current sequence
        pulse_train = PulseTrain(time_on=time_on, width=width, separation=separation,
                                 pulses_in_train=pulses_in_train,
                                 pulse_train_index=self.pulse_train_index,channels = channels)
        self.pulse_trains.append(pulse_train)
        self.pulse_train_index += 1
        self.num_of_pulse_trains += 1

    def delete_pulse_train(self, pulse_train_index):
        if self.num_of_pulse_trains > 0:
            for pos,pulse_train in enumerate(self.pulse_trains):
                if(pulse_train.pulse_train_index == pulse_train_index):
                    self.pulse_trains.pop(pos)
                    self.num_of_pulse_trains -= 1
                    return True
            return False
        else:
            return False

    def has_coincident_events(self):
        found_coincident_event = False
        pulses = []

        for pulse_train in self.pulse_trains:
            first_event = pulse_train.first_pulse_train_event
            second_event = pulse_train.latest_pulse_train_event
            pulses.append((first_event,second_event))

        sorted_pulses = sorted(pulses,key=lambda j: j[0])

        for k in range(len(sorted_pulses)-1):
            if(sorted_pulses[k][1]>sorted_pulses[k+1][0]):
                found_coincident_event = True
        return found_coincident_event

    def order_events(self):
        pulses = []

        for pulse_train in self.pulse_trains:
            first_event = pulse_train.first_pulse_train_event
            last_event = pulse_train.latest_pulse_train_event
            index = pulse_train.pulse_train_index
            separation = pulse_train.separation
            width = pulse_train.width
            channels = pulse_train.channels
            num_of_pulses = pulse_train.pulses_in_train
            pulses.append((channels,first_event,last_event, index,separation,width,num_of_pulses))

        sorted_pulses = sorted(pulses, key=lambda j: j[1])

        return sorted_pulses


    def set_first_sequence_event(self):
        if self.num_of_pulse_trains > 1:
            self.first_sequence_event = sorted(self.pulse_trains, key=lambda x: x.first_pulse_train_event)[
                0].first_pulse_train_event
        elif self.num_of_pulse_trains == 1:
            self.first_sequence_event = self.pulse_trains[0].first_pulse_train_event
        else:
            self.first_sequence_event = 0

    def small_pulse(self,time,channels):

        ONE_PERIOD = 0x200000
        TWO_PERIOD = 0x400000
        THREE_PERIOD = 0x600000
        FOUR_PERIOD = 0x800000
        FIVE_PERIOD = 0xA00000


        if time == 2.5:
            loc = ONE_PERIOD
        elif time == 5.0:
            loc = TWO_PERIOD
        elif time == 7.5:
            loc = THREE_PERIOD
        elif time == 10.0:
            loc = FOUR_PERIOD
        elif time == 12.5:
            loc = FIVE_PERIOD
        for channel in channels:
            loc |= 2 ** channel
        hex_val = "0x%X" % loc

        return hex_val

    def normal_pulse(self,channels):

        ON = 0xE00000
        loc = ON
        for channel in channels:
            loc |= 2 ** channel
        hex_val = "0x%X" % loc

        return hex_val

    def long_pulse(self,time,channels):

        ON = 0xE00000
        loc = ON
        ns = 1.0

        LONG_DELAY_STEP = 500*ns
        delay_num = int(time/LONG_DELAY_STEP)
        left_over = time - delay_num * LONG_DELAY_STEP

        while left_over <= 12.5:
            LONG_DELAY_STEP = 500 * ns + 5.0
            delay_num = int(time / LONG_DELAY_STEP)
            left_over = time - delay_num * LONG_DELAY_STEP

        for channel in channels:
            loc |= 2 ** channel
        hex_val = "0x%X" % loc

        return  (LONG_DELAY_STEP,delay_num,left_over,hex_val)

    def assertion(self,time):
        assert time in [2.5, 5.0, 7.5, 10.0, 12.5], "Valid small pulse sizes and separations are 2.5ns,5ns,7.5ns," \
                                                              "10ns, problem with pulse size %sns" % time

    def write_instruction_file(self,filename):
        path = str(((Path().resolve()).joinpath(Path("InstructionFiles"))).joinpath(filename))
        q = self.generate_instructions()
        with open(path, 'w') as f:
            for i in q:
                print(i, file=f)

    def generate_instructions_from_file(self,filename):
        path = str(((Path().resolve()).joinpath(Path("InstructionFiles"))).joinpath(filename))
        file = open(path,"r")
        lines = file.readlines()
        instructions = []

        for line in lines:
            instructions.append(line[:-1])

        return instructions


    def generate_instructions(self):

        if (self.has_coincident_events()):
            raise Exception("Overlapping Pulses not allowed")

        instructions = []
        self.set_first_sequence_event()

        if(self.first_sequence_event != 0):
            if(self.first_sequence_event <= 12.5):
                self.assertion(self.first_sequence_event)
                hex_val = self.small_pulse(time=self.first_sequence_event,channels = [])
                instructions.append("%s, CONTINUE, 0, %s" % (hex_val,12.5))

            elif (self.first_sequence_event <= self.max_instr_length):
                instructions.append("0x000000, CONTINUE, 0, %s" % (self.first_sequence_event))

            elif(self.first_sequence_event > self.max_instr_length):
                LONG_DELAY_STEP, loop_num, left_over,_ = self.long_pulse(time=self.first_sequence_event,channels=[])

                instructions.append("0x000000, LONG_DELAY, %s, %s" % (loop_num,LONG_DELAY_STEP))
                instructions.append("0x000000, CONTINUE, 0, %s" % (left_over))



        ordered_pulses = self.order_events()
        counter = 1
        le = 0

        for pulse in ordered_pulses:

            channels, first_event, last_event, index, separation, width, num_of_pulses = pulse


            if(counter!=1):
                off_time = first_event-le
                if(off_time != 0.0):
                    if(off_time <= 12.5):
                        self.assertion(off_time)
                        hex_val = self.small_pulse(time=off_time,channels=[])
                        instructions.append("%s,CONTINUE,0,12.5" % hex_val)
                    elif(off_time <= self.max_instr_length):
                        instructions.append("0x000000, CONTINUE, 0, %s" % (off_time))
                    elif (off_time > self.max_instr_length):
                        LONG_DELAY_STEP, delay_num, left_over,_ = self.long_pulse(time=off_time,channels=[])

                        instructions.append("0x000000, LONG_DELAY, %s, %s" % (delay_num, LONG_DELAY_STEP))
                        instructions.append("0x000000, CONTINUE, 0, %s" % (left_over))


            if(width <=12.5 and separation <= 12.5):
                self.assertion(width)
                self.assertion(separation)

                hex_val_width = self.small_pulse(time=width,channels=channels)
                hex_val_sep = self.small_pulse(time=separation,channels=[])

                instructions.append("%s, LOOP, %s, 12.5" % (hex_val_width,num_of_pulses))
                instructions.append("%s, END_LOOP, loop, 12.5" % (hex_val_sep))

            elif (width <= self.max_instr_length and width>12.5 and separation <= 12.5):
                self.assertion(separation)

                hex_val_width = self.normal_pulse(channels=channels)
                hex_val_sep = self.small_pulse(time=separation, channels=[])

                instructions.append("%s, LOOP, %s, %s" % (hex_val_width, num_of_pulses,width))
                instructions.append("%s, END_LOOP, loop, 12.5" % (hex_val_sep))

            elif (width > self.max_instr_length and separation <= 12.5):
                self.assertion(separation)

                LONG_DELAY_STEP, delay_num, left_over,hex_val_width = self.long_pulse(time=width,channels=channels)
                hex_val_sep = self.small_pulse(time=separation, channels=[])

                instructions.append("%s,LOOP,%s,%s" % (hex_val_width,num_of_pulses,left_over))
                instructions.append("%s,LONG_DELAY,%s,%s" % (hex_val_width, delay_num, LONG_DELAY_STEP))
                instructions.append("%s,END_LOOP,loop,12.5" % (hex_val_sep))

            elif (width <= 12.5 and separation <= self.max_instr_length and separation>12.5):
                self.assertion(width)

                hex_val_width = self.small_pulse(time=width, channels=channels)

                instructions.append("%s, LOOP, %s, 12.5" % (hex_val_width, num_of_pulses))
                instructions.append("0x000000, END_LOOP, loop, %s" % (separation))

            elif (width <= self.max_instr_length and width>12.5 and separation <= self.max_instr_length and separation>12.5):

                hex_val_width = self.normal_pulse(channels=channels)

                instructions.append("%s, LOOP, %s, %s" % (hex_val_width, num_of_pulses,width))
                instructions.append("0x000000, END_LOOP, loop, %s" % (separation))

            elif (width > self.max_instr_length and separation <= self.max_instr_length and separation>12.5):

                LONG_DELAY_STEP, delay_num, left_over,hex_val_width = self.long_pulse(time=width,channels=channels)

                instructions.append("%s,LOOP,%s,%s" % (hex_val_width, num_of_pulses, left_over))
                instructions.append("%s,LONG_DELAY,%s,%s" % (hex_val_width, delay_num, LONG_DELAY_STEP))
                instructions.append("0x000000, END_LOOP, loop, %s" % (separation))

            elif (width <= 12.5 and separation > self.max_instr_length):
                self.assertion(width)

                hex_val_width = self.small_pulse(time=width, channels=channels)
                LONG_DELAY_STEP, delay_num, left_over,_ = self.long_pulse(time=separation,channels=channels)


                instructions.append("%s, LOOP, %s, 12.5" % (hex_val_width, num_of_pulses))
                instructions.append("0x000000, LONG_DELAY, %s,%s" %(delay_num,LONG_DELAY_STEP))
                instructions.append("0x000000, END_LOOP, loop, %s" % (left_over))

            elif (width <= self.max_instr_length and width>12.5 and separation > self.max_instr_length):

                hex_val_width = self.normal_pulse(channels=channels)
                LONG_DELAY_STEP, delay_num, left_over,_ = self.long_pulse(time=separation,channels=channels)


                instructions.append("%s, LOOP, %s, %s" % (hex_val_width, num_of_pulses,width))
                instructions.append("0x000000, LONG_DELAY, %s,%s" %(delay_num,LONG_DELAY_STEP))
                instructions.append("0x000000, END_LOOP, loop, %s" % (left_over))

            elif (width > self.max_instr_length and separation > self.max_instr_length):

                LONG_DELAY_STEP_hi, delay_num_hi, left_over_hi, hex_val_width = self.long_pulse(time=separation, channels=channels)
                LONG_DELAY_STEP_lo, delay_num_lo, left_over_lo,_ = self.long_pulse(time=separation,channels=channels)


                instructions.append("%s, LOOP, %s, %s" % (hex_val_width, num_of_pulses,left_over_hi))
                instructions.append("%s, LONG_DELAY, %s,%s" %(hex_val_width,delay_num_hi,LONG_DELAY_STEP_hi))

                instructions.append("0x000000, LONG_DELAY, %s,%s" %(delay_num_lo,LONG_DELAY_STEP_lo))
                instructions.append("0x000000, END_LOOP, loop, %s" % (left_over_lo))


            le = last_event
            counter = 2
        instructions.append("0x000000, CONTINUE,0,50")
        instructions.append("0x000000, STOP,0,100")
        return instructions



if __name__ == '__main__':
    pass
  #  p = PulseSequence()
  #  p.add_pulse_train(time_on='0ns', width='50ns', separation='50ns', pulses_in_train=2,channels = [0,1,2])
  #  p.add_pulse_train(time_on='202.5ns', width='30ns', separation='5ns', pulses_in_train=4,channels = [0,1,2])
  #  p.add_pulse_train(time_on='200ms', width='300ms', separation='300ms', pulses_in_train=4,channels = [0])
  #  print(p.generate_instructions())
  #  p.write_instruction_file('instruction.txt')
  #  print(p.generate_instructions_from_file('instruction.txt'))



