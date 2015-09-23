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
from numpy import mean
from pylab import ion, ioff, figure, draw, contourf, clf, show, hold, plot
from scipy import diag, arange, meshgrid, where



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
		print self.channels

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

	def training_interface(self, mov_number, reps_per_mov = 4, resting_time = 2, execution_time = 3):
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
			#if mov_type == 0:
			#	mov_type = 1
			#else:
			#	mov_type = 0
			while mov_counter[mov_type] == 0:
				mov_type = random.randint(0, mov_number - 1)
			for i in self.movs:
				if i['ID'] == mov_type:
					# The user prepares to execute the movement, the signal is sampled (it will be classified as no movement)
					print "Prepare ", i['Name'], " movement..."
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
		np.savetxt('net_out.txt', self.out)

	def init_classifier(self, hidden_units = 5):
		# Number of features, change me!
		data = ClassificationDataSet(len(self.channels))
		# Feature preparation, the one to work on!
		for i in range(len(self.classification_proc)):
			data.appendLinked(self.y_proc[i], self.classification_proc[i])
		data.calculateStatistics()
		print data.classHist
		# Make global for test purposes
		self.data = data
		# Prepare training and test data, 75% - 25% proportion
		self.testdata, self.traindata = data.splitWithProportion(0.25)
		# Suggested, check why
		#self.traindata._convertToOneOfMany()
		#self.testdata._convertToOneOfMany()
		# CHECK the number of hidden units
		fnn = buildNetwork(self.traindata.indim, hidden_units, self.traindata.outdim)
		# CHECK meaning of the parameters
		trainer = BackpropTrainer(fnn, dataset=self.traindata, momentum=0.1, verbose=True, weightdecay=0.01)
		print fnn
		return fnn, trainer, data

	def classify(self, net, trainer, num_it = 1):
		# Taken from pybrain wiki, repeats the training of the network num_it times trying to minimize the error
		for i in range(num_it):
			#trainer.trainEpochs(5)
			trainer.trainUntilConvergence(self.traindata, 1000)
			trnresult = percentError( trainer.testOnClassData(), self.traindata['class'] )
			tstresult = percentError( trainer.testOnClassData(dataset=self.testdata), self.testdata['class'] )
			print "epoch: %4d" % trainer.totalepochs, "  train error: %5.2f%%" % trnresult, "  test error: %5.2f%%" % tstresult
		print len(self.t_proc)
		# out = net.activateOnDataset(self.data)
		# figure()
		# tmpx = range(len(out))
		# plt.scatter(tmpx, self.classification)
		# hold(True)
		# plt.scatter(tmpx, out, color='red')
		# print len(out)
		# print len(self.classification)
		# figure(1)
		# ioff()  # interactive graphics off
		# clf()   # clear the plot
		# hold(True) # overplot on
		# for c in [0,1,2]:
		# 	here, _ = where(self.testdata['class']==c)
		# 	#print here
		# 	plot(self.testdata['input'][here,0],self.testdata['input'][here,1],'o')
		# if out.max()!=out.min():  # safety check against flat field
		# 	contourf(X, Y, out)   # plot the contour
		# ion()   # interactive graphics on
		# draw()  # update the plot
		self.out = net.activateOnDataset(self.data)
		# TEMPORARY for just two movements
		#self.out[self.out < 1.4] = 1
		#self.out[self.out > 1.6] = 2
		plt.plot(self.classification_proc,'r')
		plt.hold(True)
		plt.plot(self.out,'b')
		plt.show()
		return trainer, trnresult, tstresult

	def window_rms(self, a, window_size):
  		a2 = np.power(a,2)
  		window = np.ones(window_size)/float(window_size)
  		return np.sqrt(np.convolve(a2, window, 'same'))



	def data_process(self):
		self.factor = 0.01
		for i in range(len(self.channels)):
			tmp = [b[i] for b in self.y]
			print i, mean(tmp)
			tmp = tmp - mean(tmp)
			res = self.window_rms(tmp, 500)
			#[b[i] for b in self.y_proc] = res
			#print res
			cont = 0
			for j in self.y:
				j[i] = res[cont]
				cont = cont + 1
		# Remove the 0 class even though luca thinks it makes no sense
		self.y = self.y[self.classification != 0][:]
		self.t = self.t[self.classification != 0][:]
		self.t = np.linspace(0,len(self.t)*self.dT,len(self.t))
		self.classification = self.classification[self.classification != 0]
		# Rectify the signal
		#self.y = abs(self.y)
		self.y_proc = []
		self.classification_proc = []
		num_samp = self.samplingRate * self.factor
		num_it = int(len(self.classification) / num_samp)
		self.t_proc = []
		for i in range(num_it):
			tmp_row = []

			for col in range(len(self.channels)):
				vect=[int(b[col]) for b in self.y[i*num_samp:(i+1)*num_samp]]
				#print vect
				tmp_row.append(mean(vect))
			#print tmp_row
			self.t_proc.append(i*self.factor)
			self.y_proc.append(tmp_row)
			#print self.y_proc
			self.classification_proc.append(self.classification[i*num_samp])
		#print self.y_proc
		#for i in range(len(self.channels)):
			#print i
		#print len(self.t_proc)
		#print self.y_proc
		#print len(self.y_proc[:][1])
		#print len(self.y_proc[1][:])
		for i in range(len(self.channels)):
			print i
			plt.scatter(self.t_proc, [b[i] for b in self.y_proc])
			plt.hold(True)
			plt.title("Channel " + str(i+1))
			plt.plot(self.t, [b[i] for b in self.y],'r')
			plt.show()
		plt.plot(self.t, [b[0] for b in self.y],'b')
		plt.hold(True)
		plt.plot(self.t, [b[1] for b in self.y],'r')
		plt.plot(self.t, [b[2] for b in self.y],'g')
		plt.plot(self.t, [b[3] for b in self.y],'k')
		#plt.plot(self.t, [b[4] for b in self.y],'m')
		#plt.plot(self.t, [b[5] for b in self.y],'c')
		plt.show()
		# plt.scatter(self.t_proc, [b[2] for b in self.y_proc])
		# plt.hold(True)
		# plt.title("Channel 3")
		# plt.plot(self.t, [b[2] for b in self.y],'r')
		# plt.show()
		# plt.plot(self.t, [b[1] for b in self.y],'b')
		# plt.hold(True)
		# plt.plot(self.t, [b[2] for b in self.y],'r')
		# plt.show()
		print len(self.t_proc)
		return self.t_proc, self.y_proc, self.classification_proc

		def close(self):
			self.board.stop()
			self.board.close()

if __name__ == '__main__':
	bt = bitalino('98:D3:31:80:48:08',1000,[0,2,4,5])
	# Experiments made with parameters 2,3,3,5
	bt.training_interface(5,3,3,2)
	bt.board.close()
	bt.data_process()
	net, trainer, _ = bt.init_classifier()
	trainer = bt.classify(net, trainer)
	bt.save_training()
	bt = bitalino('98:D3:31:80:48:08',1000,[0,2,4,5])
	print "Testing acquisition"
	bt.training_interface(5,1,3,2)
	t,y,classification = bt.data_process()
	_, _, test_data = bt.init_classifier()
	test_out = net.activateOnDataset(test_data)
	plt.plot(classification,'m')
	plt.hold(True)
	plt.plot(test_out,'g')
	plt.show()
	#t, y = bt.sample(10, True)
	#bt.plot(t,y)