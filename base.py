import time
import numpy as np
import matplotlib.pyplot as plt
import bitalino as BT
import random
import csv
from pybrain.datasets import ClassificationDataSet
from pybrain.tools.shortcuts import buildNetwork
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.utilities import percentError



class bitalino(object):


	def __init__(self, macAddress = '98:D3:31:80:48:08', samplingRate = 1000, channels = [0,1,2,3,4,5]):


		self.board = BT.BITalino(macAddress)

		# Sampling Rate (Hz)
		self.dT = 1.0 / float(samplingRate)
		self.samplingRate = samplingRate

		# Number of samples acquired before transmission is made
		# This is a parameter, it influences the board to PC delay
		# and the power consumption of the board
		self.nSamp = 200

		# Initialize the board
		self.channels = channels


	def initialize_time_series(self, total_time):
		# Declare the time stamp and output lists
		self.cont = 0
		totSamp = int(total_time * self.samplingRate)
		self.y = np.zeros((totSamp, len(self.channels)))
		self.t = np.zeros(totSamp)
		self.classification = np.zeros(totSamp)
		
	def sample(self, sampTime, reset = False):
		# Initialize variables to sample the correct amount of samples
		# Two loops are needed, every transmission sends self.nSamp samples
		# Thus, the number of transmissions is given by the total samples needed
		# (found using the total time) divided by the samples per transmission
		if reset == True:
			self.initialize_time_series(sampTime)
		Sampnum = int(sampTime * self.samplingRate)
		transNum = int(Sampnum / self.nSamp)
		#print "Start sampling..."
		for n in range(transNum):
			samples = self.board.read(self.nSamp)
			#print samples
			for sample in samples:
				self.y[self.cont,:] = sample[5:]
				#print self.y
				self.t[self.cont] = self.dT * self.cont
		   		self.cont = self.cont + 1
		#print "Finished sampling"
		return self.t, self.y

	def plot(self, t, y, plotChan = 'all'):
		pass
		if plotChan == 'all':
			plotChan = self.channels
		cont = 0
		for chan in plotChan:
			plt.figure()
			# Prepare the y by transforming it into a list
			ytmp = [i[cont] for i in  y]
			plt.plot(t,ytmp)
			plt.title("EMG Signal - Analog Channel " + str(chan))
			plt.xlabel("Time (s)")
			plt.ylabel("EMG Amplitude (AU)")
			plt.show()
			cont = cont + 1

	def training_interface(self, mov_number, reps_per_mov = 2, resting_time = 1, execution_time = 1):
		''' This function serves as an interactive interface for executing
		the signal acquisition for the neural network. As such, it will ask
		the user to input several parameters and it will execute the training routine
		and it will prepare the data to train the neural network
		
		movs will be a list of dictionaries in which every entry contains the name of the
		movement and the classification (binary, true or false). The classification is just
		a list, the time will be given by a shared time variable, as well as the EMG signal
		'''
		self.movs = []
		# Slightly cryptic: The total duration of the time series will be given by the number of
		# movements time the number of repetitions time the resting time (between movements) + execution time
		self.initialize_time_series(mov_number * reps_per_mov * (resting_time + execution_time))
		for i in range(mov_number):
			st = raw_input("Insert the name of the movement: ")
			self.movs.append({'ID' : i, 'Name' : st, 'Classification': np.zeros(len(self.t))})
		print self.movs
		# Start the real training algorithm, the user will be told to do random movements
		mov_counter = np.ones(mov_number) * reps_per_mov
		print "Starting the training algorithm... Relax your muscles"
		self.wait(resting_time)
		self.board.start(self.samplingRate, self.channels)
		for i in range(mov_number * reps_per_mov):
			random.seed()
			mov_type = random.randint(0, mov_number - 1)
			while mov_counter[mov_type] == 0:
				mov_type = random.randint(0, mov_number - 1)
			for i in self.movs:
				if i['ID'] == mov_type:
					# The user prepares to execute the movement, the signal is sampled (it will be classified as no movement)
					print "Prepare to execute ", i['Name'], " movement..."
					self.sample(resting_time)
					# Save the counter to update the class correctly
					tmpcont = self.cont
					print "Execute ", i['Name'], " movement NOW!"
					self.sample(execution_time)
					i['Classification'][tmpcont:self.cont] = 1
					print "Stop!"
			mov_counter[mov_type] = mov_counter[mov_type] - 1
		for i in self.movs:
			self.classification = self.classification + (i['ID'] + 1) * i['Classification']
			# plt.figure()
			# plt.plot(self.t, i['Classification'])
			# plt.show()
		return self.t, self.y, self.classification


	def wait(self, dt):
		t0 = time.time()
		for i in range(dt):
			print dt-i, "..."
			while time.time() - t0 < (i+1):
				pass

	def save_training(self):
		# writedict={'Time':self.t}
		# cont = 0
		# for channel in self.channels:
		# 	tmpst = 'Channel' + str(channel)
		# 	writedict[tmpst] = self.y[:,cont]
		# writedict['Classification'] = self.classification
		# #print writedict
		# with open('output.csv', 'w') as csvfile:
		# 	fields = writedict.keys()
		# 	writer = csv.DictWriter(csvfile,fieldnames = fields)
		# 	writer.writeheader()
		# 	for r in writedict:
		# 		print r
		# 		writer.writerow(r)
		np.savetxt('emg.txt', self.y)
		np.savetxt('time.txt', self.t)
		np.savetxt('class.txt', self.classification)

	def init_classifier(self, hidden_units = 5):
		# Number of features, change me!
		data = ClassificationDataSet(len(self.channels))
		# Feature preparation, the one to work on!
		for i in range(len(self.t)):
			data.appendLinked(self.y[i], self.classification[i])
		data.calculateStatistics()
		print data.classHist
		# Prepare training and test data, 75% - 25% proportion
		self.testdata, self.traindata = data.splitWithProportion(0.25)
		# Suggested, check why
		self.traindata._convertToOneOfMany()
		self.testdata._convertToOneOfMany()
		# CHECK the number of hidden units
		fnn = buildNetwork(self.traindata.indim, hidden_units, self.traindata.outdim)
		# CHECK meaning of the parameters
		trainer = BackpropTrainer(fnn, dataset=self.traindata, momentum=0.1, verbose=True, weightdecay=0.01)
		return fnn, trainer

	def classify(self, net, trainer, num_it = 10):
		# Taken from pybrain wiki, repeats the training of the network num_it times trying to minimize the error
		for i in range(num_it):
			trainer.trainEpochs(1)
			trnresult = percentError( trainer.testOnClassData(), self.traindata['class'] )
			tstresult = percentError( trainer.testOnClassData(dataset=self.testdata), self.testdata['class'] )
			print "epoch: %4d" % trainer.totalepochs, "  train error: %5.2f%%" % trnresult, "  test error: %5.2f%%" % tstresult


if __name__ == '__main__':
	bt = bitalino('98:D3:31:80:48:08',1000,[0,1,2,3,4,5])
	bt.training_interface(2)
	net, trainer = bt.init_classifier()
	bt.classify(net, trainer)
	bt.save_training()
	#t, y = bt.sample(10, True)
	#bt.plot(t,y)