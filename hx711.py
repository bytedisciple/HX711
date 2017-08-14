import RPi.GPIO as GPIO
import time
import statistics as stat
class HX711:
	def __init__(self, dout_pin, pd_sck_pin, gain_channel_A=128, select_channel='A'):
		if (isinstance(dout_pin, int) and 
			isinstance(pd_sck_pin, int)): 	# just chack of it is integer
			self._pd_sck = pd_sck_pin 	# init pd_sck pin number
			self._dout = dout_pin 		# init data pin number
		else:
			raise TypeError('dout_pin and pd_sck_pin have to be pin numbers.\nI have got dout_pin: '\
					 + str(dout_pin) + \
					' and pd_sck_pin: ' + str(pd_sck_pin) + '\n')
		
		self._gain_channel_A = 0 	# init to 0	
		self._offset_A_128 = 0 		# init offset for channel A and gain 128
		self._offset_A_64 = 0		# init offset for channel A and gain 64
		self._offset_B = 0 		# init offset for channel B
		self._last_data_A_128 = 0	# init last data to 0 for channel A and gain 128
		self._last_data_A_64 = 0 	# init last data to 0 for channelA and gain 64
		self._last_data_B = 0	 	# init last data to 0 for channel B	
		self._wanted_channel = ''	# init to empty string
		self._current_channel = ''	# init to empty string
		self._scale_ratio_A_128 = 1	# init to 1
		self._scale_ratio_A_64 = 1	# init to 1
		self._scale_ratio_B = 1		# init to 1
		self._debug_mode = False	# init debug mode to False

		GPIO.setmode(GPIO.BCM) 			# set GPIO pin mode to BCM numbering
		GPIO.setup(self._pd_sck, GPIO.OUT)	# pin _pd_sck is output only
		GPIO.setup(self._dout, GPIO.IN)		# pin _dout is input only
		self.select_channel(select_channel)	# call select channel function
		self.set_gain_A(gain_channel_A) 	# init gain for channel A
			
	############################################################
	# select_channel function evaluates if the desired channel #
	# is valid and then sets the _wanted_channel.		   #
	# If returns True then OK 				   #
	# INPUTS: channel ('A'|'B') 				   #
	# OUTPUTS: BOOL  					   #
	############################################################
	def select_channel(self, channel):
		if (channel == 'A'):
			self._wanted_channel = 'A'
		elif (channel == 'B'):
			self._wanted_channel = 'B'
		else:
			raise ValueError('channel has to be "A" or "B".\nI have got: '\
						+ str(channel))
		# after changing channel or gain it has to 50 ms to allow adjustment.
		# the data before it is garbage and cannot be used.
		self._read()
		time.sleep(0.5)
		return True
		
	############################################################
	# set_gain_A function sets gain for channel A. 		   #
	# allowed values are 128 or 64. If return True then OK	   #
	# INPUTS: gain (64|128) 				   #
	# OUTPUTS: BOOL 					   #
	############################################################
	def set_gain_A(self, gain):
		if gain == 128:
			self._gain_channel_A = gain
		elif gain == 64:
			self._gain_channel_A = gain
		else:
			raise ValueError('gain has to be 128 or 64.\nI have got: '
						+ str(gain))
		# after changing channel or gain it has to 50 ms to allow adjustment.
		# the data before it is garbage and cannot be used.
		self._read()
		time.sleep(0.5)
		return True
		
	############################################################
	# zero is function which sets the current data as 	   #
	# an offset for particulart channel. It can be used for    #
	# subtracting the weight of the packaging. 		   #
	# max value of times parameter is 99. min 1. Default 10.   #
	# INPUTS: times # how many times do reading and then mean  #
	# OUTPUTS: BOOL 	# if True it is OK		   #
	############################################################
	def zero(self, times=10):
		if times > 0 and times < 100:
			# try 5 more times. if it fails then return False
			for i in range(5):
				result = self.get_raw_data_mean(times)
				if result != False:
					if (self._current_channel == 'A' and 
						self._gain_channel_A == 128):
						self._offset_A_128 = result
						return True
					elif (self._current_channel == 'A' and 
						self._gain_channel_A == 64):
						self._offset_A_64 = result
						return True
					elif (self._current_channel == 'B'):
						self._offset_B = result
						return True
					else:
						if self._debug_mode:
							print('Cannot zero() channel and gain mismatch.\n'\
								+ 'current channel: ' + str(self._current_channel)\
								+ 'gain A: ' + str(self._gain_channel_A) + '\n')
						return False
			if self._debug_mode:
				print('zero() got False back.\n')
			return False
		else:
			raise ValueError('In function "zero" parameter "times" can be in range 1 up to 99. '\
						+ 'I have got: ' + str(times) + '\n')
	
	############################################################
	# set offset function sets desired offset for particular   #
	# channel and gain. By default it sets offset for current  #
	# channel and gain.					   #
	# INPUTS: offset, channel (a|A|b|B), gain (128|64)	   #
	# OUTPUTS: BOOL 	# return true it is ok		   #
	############################################################
	def set_offset(self, offset, channel='', gain_A=128):
		if isinstance(offset, int):
			if channel == 'A' and gain_A == 128: 
				self._offset_A_128 = offset
				return True
			elif channel == 'A' and gain_A == 64:
				self._offset_A_64 = offset
				return True
			elif channel == 'B':
				self._offset_B = offset
				return True
			else:
				if self._current_channel == 'A' and self._gain_channel_A == 128:
					self._offset_A_128 = offset
					return True
				elif self._current_channel == 'A' and self._gain_channel_A == 64:
					self._offset_A_64 = offset
					return True
				else:
					self._offset_B = offset
					return True
		else:
			raise TypeError('function "set_offset" parameter "offset" has to be integer. '\
					+ 'I have got: ' + str(offset) + '\n')
		
	############################################################
	# set_scale_ratio function sets the ratio for calculating  #
	# weight in desired units. In order to find this ratio for #
	# example to grams or kg. You must have known weight. 	   #
	# Function returns True if it is ok. Else raises exception #
	# INPUTS: channel('A'|'B'|empty), gain_A(128|64|empty),	   #
	# 		scale_ratio(0.0..1,..)			   #
	# OUTPUTS: BOOL		# if True it is OK 		   #
	############################################################
	def set_scale_ratio(self, channel='', gain_A=0, scale_ratio=1):
		if (scale_ratio > 0.0):
			if channel == 'A' and gain_A == 128: 
				self._scale_ratio_A_128 = scale_ratio
				return True
			elif channel == 'A' and gain_A == 64:
				self._scale_ratio_A_64 = scale_ratio
				return True
			elif channel == 'B':
				self._scale_ratio_B = scale_ratio
				return True
			else:
				if self._current_channel == 'A' and self._gain_channel_A == 128:
					self._scale_ratio_A_128 = scale_ratio
					return True
				elif self._current_channel == 'A' and self._gain_channel_A == 64:
					self._scale_ratio_A_64 = scale_ratio
					return True
				else:
					self._scale_ratio_B = scale_ratio
					return True
		else:
			raise ValueError('In function "set_scale_ratio" parameter "scale_ratio" has to be '\
					+ 'positive number.\nI have got: ' + str(scale_ratio) + '\n')
	
	############################################################
	# set_debug_mode function is for turning on and off 	   #
	# debug mode.						   #
	# INPUTS: flag(BOOL)					   #
	# OUTPUTS: BOOL 	# if True then it is executed ok   #
	############################################################
	def set_debug_mode(self, flag=False):
		if flag == False:
			self._debug_mode = False
			print('Debug mode DISABLED')
			return True
		elif flag == True:
			self._debug_mode = True
			print('Debug mode ENABLED')
			return True
		else:
			raise ValueError('In function "set_debug_mode" parameter "flag" can be only BOOL value.\n'
					+ 'I have got: ' + str(flag) + '\n' )
	
	############################################################
	# _ready function check if data is prepared for reading.   #
	# It returns Boolean value. True means that data is ready  #
	# INPUTS: none						   #
	# OUTPUTS: BOOL						   #
	############################################################
	def _ready(self):
		if GPIO.input(self._dout) == 0:	# if DOUT pin is low data is ready for reading
			return True
		else:
			return False
	
	############################################################
	# _set_channel_gain is called only from _read function.    #
	# It finished the data transmission for hx711 and set	   #
	# the next required gain and channel.			   #
	# If it return True it is OK. 				   #
	# INPUT: num (1|2|3)	# how many ones it sends	   #
	# OUTPUTS: BOOL 					   #
	############################################################
	def _set_channel_gain(self, num):
			for i in range(num):
				start_counter = time.perf_counter() # start timer now.
				GPIO.output(self._pd_sck, True) # set high
				GPIO.output(self._pd_sck, False) # set low
				end_counter = time.perf_counter() # stop timer
				if end_counter-start_counter >= 0.00006: # check if hx 711 did not turn off...
				# if pd_sck pin is HIGH for 60 us and more than the HX 711 enters power down mode.
					if self._debug_mode:
						print('Not enough fast while setting gain and channel')
						print('Time elapsed: ' + str(end_counter - start_counter))
						#print('Resetting HX711...\n')
					#self.reset() 	# reset hx 711 because it turned off
					return False
			return True
	
	############################################################
	# _read function reads bits from hx711, converts to INT    #
	# and validate the data. 				   #
	# If it return int it is OK. If False something is wrong   #
	# INPUT: none						   #
	# OUTPUTS: BOOL | INT 					   #
	############################################################
	def _read(self):
		GPIO.output(self._pd_sck, False) # start by setting the pd_sck to false
		ready_counter = 0		# init the counter to 0
		while ready_counter <= 40 and not self._ready(): 
			time.sleep(0.05)	# sleep for 50 ms because data is not ready
			ready_counter += 1 	# increment counter
			if ready_counter == 40: # if counter reached max value then return False
				if self._debug_mode:
					print('self._read() not ready after 40 sleeps\n')
				return False
		
		# read first 24 bits of data
		data_in = 0	# 2' complement data from hx 711
		for i in range(24):
			start_counter = time.perf_counter() 	# start timer
			GPIO.output(self._pd_sck, True) 	# request next bit from hx 711
			GPIO.output(self._pd_sck, False)
			end_counter = time.perf_counter()	# stop timer
			if end_counter - start_counter >= 0.00006: # check if the hx 711 did not turn off...
			# if pd_sck pin is HIGH for 60 us and more than the HX 711 enters power down mode.
				if self._debug_mode:
					print('Not enough fast while reading data')
					print ('Time elapsed: ' + str(end_counter - start_counter))
					#print('Resetting HX711...\n')
				#self.reset()
				return False
			# Shift the bits as they come to data_in variable.
			# Left shift by one bit then bitwise OR with the new bit. 
			data_in = (data_in<<1) | GPIO.input(self._dout)
			
		# set gain and channel for the next reading
		backup_current_channel = self._current_channel
		if self._wanted_channel == 'A' and self._gain_channel_A == 128:
			if not self._set_channel_gain(1):	# send only one bit which is 1
				return False			# return False because channel was not set properly
			else:
				self._current_channel = 'A'	# else set current channel variable
		elif self._wanted_channel == 'A' and self._gain_channel_A == 64:
			if not self._set_channel_gain(3):	# send three ones
				return False			# return False because channel was not set properly
			else:
				self._current_channel = 'A'	# else set current channel variable
		else:
			if  not self._set_channel_gain(2): 	# send two ones 
				return False			# return False because channel was not set properly
			else:
				self._current_channel = 'B'	# else set current channel variable
		
		if self._debug_mode:	# print 2's complement value
			print('Binary value as it has come: ' + str(bin(data_in)) + '\n')
		
		#check if data is valid
		if (data_in == 0x7fffff or 		# 0x7fffff is the highest possible value from hx711
			data_in == 0x800000):	# 0x800000 is the lowest possible value from hx711
			if self._debug_mode:
				print('Invalid data detected\n')
			return False			# rturn false because the data is invalid
		
		# calculate int from 2's complement 
		signed_data = 0
		if (data_in & 0x800000): # 0b1000 0000 0000 0000 0000 0000 check if the sign bit is 1. Negative number.
			signed_data = -((data_in ^ 0xffffff) + 1) # convert from 2's complement to int
		else:	# else do not do anything the value is positive number
			signed_data = data_in
		
		if self._debug_mode:
			print('Converted 2\'s complement value: ' + str(signed_data) + '\n')
	
		# signed_data is correct range then save it as a last correct value and return it.
		if backup_current_channel == 'A' and self._gain_channel_A == 128:
			self._last_data_A_128 = signed_data
		elif backup_current_channel == 'A' and self._gain_channel_A == 64:
			self._last_data_A_64 = signed_data
		else:
			self.last_data_B = signed_data
		if self._debug_mode:
			print('Backup current channel vatiable: ' + str(backup_current_channel) + '\n')
		
		return signed_data
	
	############################################################
	# _get_readings function reads data once or several times. #
	# Then results adds up and return. Max number of readings  #
	# is 99.						   #
	# INPUTS: times	# how many times to read data. Default 1   #
	# OUTPUTS: BOOL | INT 					   #
	############################################################
	def _get_readings(self, times=1):
		if times > 0 and times < 100: 
			data = 0
			data_sum = 0
			# check if wanted channel is currently prepared to read from.
			if self._wanted_channel == self._current_channel:
				for i in range(5):	# try multiple times if get False
					for j in range(times):		# for number of times read and add up all readings.
						data = self._read()
						if data != False:
							data_sum += data
							if j == times-1:
								return data_sum
						else:
							if self._debug_mode:
								print('self._get_readings() Cannot calculate average. Got False\n')
							break
				return False
			else:	# else it tries to set the required channel.
				for i in range(3):
					result = self._read()
					if result != False:	# did not get False so the required channel is set.
						return self._get_readings(times) # recursive call because the channel is set.
					if self._debug_mode:
						print('Cannot set the wanted channel')
						print('Resetting HX711...\n')
				self.reset()	# reset because it cannot set the required channel
				return False
		else:
			raise ValueError('function "_get_readings" parameter "times" has to be in range 1 up to 99.\n I have got: '\
						+ str(times))
	
	############################################################
	# get_raw_data_mean returns average value of readings.	   #
	# If return False something is wrong. Try debug mode.	   #
	# INPUTS: times # how many times to read data. Default 1   #
	# OUTPUTS: INT | BOOL					   #
	############################################################
	def get_raw_data_mean(self, times=1):
		result = self._get_readings(times)
		if result != False:
			return result / times
		else:
			return False
	
	############################################################
	# get_data_mean returns average value of readings minus    #
	# offset for the particular channel which was read.	   #
	# If return False something is wrong. Try debug mode.	   #
	# INPUTS: times # how many times to read data. Default 1   #
	# OUTPUTS: INT | BOOL					   #
	############################################################
	def get_data_mean(self, times=1):
		result = self._get_readings(times)
		if result != False:
			if self._current_channel =='A' and self._gain_channel_A == 128:
				return (result / times)- self._offset_A_128
			elif self._current_channel == 'A' and self._gain_channel_A == 64:
				return (result / times) - self._offset_A_64
			else:
				return (result / times) - self._offset_B
		else:
			return False
	
	############################################################
	# get_weight_mean returns average value of readings minus  #
	# offset divided by scale ratio for a particular channel   #
	# and gain.						   #
	# If return False something is wrong. Try debug mode.	   #
	# INPUTS: times # how many times to read data. Default 1   #
	# OUTPUTS: INT | BOOL 					   #
	############################################################
	def get_weight_mean(self, times=1):
		result = self._get_readings(times)
		if result != False:
			if self._current_channel =='A' and self._gain_channel_A == 128:
				return ((result / times)- self._offset_A_128) / self._scale_ratio_A_128
			elif self._current_channel == 'A' and self._gain_channel_A == 64:
				return ((result / times) - self._offset_A_64) / self._scale_ratio_A_64
			else:
				return ((result / times) - self._offset_B) / self._scale_ratio_B
		else:
			return False

	
	############################################################
	# get current gain A return the value of current gain on   #
	# the channel A						   #
	# INPUTS: none						   #
	# OUTPUTS: INT						   #
	############################################################
	def get_current_gain_A(self):
		return self._gain_channel_A

	############################################################
	# power down function turns off the hx711.		   #
	# INPUTS: none						   #
	# OUTPUTS: BOOL		# True then it is executed	   #
	############################################################
	def power_down(self):
		GPIO.output(self._pd_sck, False)
		GPIO.output(self._pd_sck, True)
		time.sleep(0.01)
		return True

	############################################################
	# power up function turns on the hx711.			   #
	# INPUTS: none						   #
	# OUTPUTS: BOOL 	# True then it is executed	   #
	############################################################
	def power_up(self):
		GPIO.output(self._pd_sck, False)
		time.sleep(0.01)
		return True

	############################################################
	# reset function resets the hx711 and prepare it for 	   #
	# the next reading.					   #
	# INPUTS: none						   #
	# OUTPUTS: BOOL 	# True then it is executed	   #
	############################################################
	def reset(self):
		self.power_down()
		self.power_up()
		result = self._get_readings(6)
		if result != False:
			return True
		else:
			return False