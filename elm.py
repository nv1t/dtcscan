#!/usr/bin/env python
###########################################################################
# elm.py
#
# Copyright 2012 David DiPaola (dsd3275@rit.edu)
#
# This file is part of dtc_scan.
#
# dtc_scan is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# dtc_scan is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with dtc_scan; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###########################################################################

import serial
from obd2_codes import pcodes, pcode_prefix
import time
import sys


class NoResponseError(Exception):
	"""This is thrown when communication with the ELM module fails"""
	def __init__(self, msg):
		self.msg = msg

class ELM(object):
	"""Interfaces with ELM327-based OBD-II vehicle scanners"""

	"""Constants"""
	#size of the serial input buffer in bytes/characters
	_BUFF_SIZE = 100
	#things we receive
	_ELM_NEWLINE = "\r"
	_ELM_INIT_MSG = "ELM327"
	_SEARCHING_MSG = "SEARCHING..."
	_CANT_CONN_MSG = "UNABLE TO CONNECT"
	_DTC_RESP_CODE = "43"
	#things we send
	_ELM_RESET_MSG = "ATZ"+_ELM_NEWLINE
	_DTC_GET_MSG = "03"+_ELM_NEWLINE
	#DTC processing info
	_DTC_CODE_LEN = 4
	

	"""Local Variables"""
	#current serial connection
	_serialConn = None
	#list of Diagnostic Trouble Codes
	_dtcs = []

	def __init__(self):
		"""Initialization method"""
		pass

	def printDtcs(self):
		"""Takes all read DTCs and prints them in plain English."""
		currDtc = ""
		for dtcLine in self._dtcs:
			i=0
			for c in dtcLine:
				#if at the start of a DTC
				if( (i % self._DTC_CODE_LEN) == 0 ):
					#find the right prefix
					currDtc = pcode_prefix[c]
				#otherwise, append the next character directly
				else:
					currDtc += c
				#if we're at the start/end of a DTC
				if( (i % self._DTC_CODE_LEN) == (self._DTC_CODE_LEN-1) ):
					#if there's a code to print
					if(currDtc != "P0000"):
						if currDtc in pcodes:
							print(currDtc + ": " + pcodes[currDtc])
						else:
							print(currDtc + ": Unknown meaning")
				i = i + 1

	def _getElmLines(self):
		"""Returns a list of strings representing lines of text received from the
		   ELM327

		Raises:
			ValueError -- the serial port is closed

		"""
		elmResponse = self._serialConn.read(self._BUFF_SIZE)
		result = elmResponse.split(self._ELM_NEWLINE)
		return result	

	def connect(self, serial_port, baud, num_retries):
		"""Connects to the ELM327

		Arguments:
			serial_port -- a string representing the name or location of the serial port
			baud -- the baud rate to connect at
			num_retries -- the number of times to retry connecting to the ELM before giving up

		Raises:
			serial.SerialException -- when the serial port can't be opened
			ValueError -- the serial port became closed very soon after being opened
			elm.NoResponseError -- there was no response from the ELM unit

		"""
		elmResponse = ""
		foundIt = False
		retryCount = num_retries

		#open the serial port
		self._serialConn = serial.Serial(serial_port, baud, timeout=1)

		#read lines until the ELM says its status message
		time.sleep(2)  #sleep just to give the serial port time to init
		self._serialConn.write(self._ELM_RESET_MSG)
		while (foundIt == False) and (retryCount > 0):
			respList = self._getElmLines()
			for line in respList:
				if( line.startswith(self._ELM_INIT_MSG) ):
					foundIt = True
			retryCount = retryCount - 1
			#if there's going to be a retry, give the ELM a break
			if(retryCount > 0):
				time.sleep(2)

		if(retryCount == 0):
			raise NoResponseError("Engine may be off")

		return self

	def getDtcs(self):
		"""Retrieves DTC responses from the ELM

		Raises:
			ValueError -- no connection was made prior to calling this method
			elm.NoResponseError -- there was no response from the ELM unit

		"""
		foundIt = False
		elmLines = []
		self._dtcs = []
	
		#ask for DTCs from the ELM
		self._serialConn.write(self._DTC_GET_MSG)
		#get the response, break up into lines
		elmLines = self._getElmLines()
		#go through the lines
		for line in elmLines:
			#if it's a DTC response
			if( line.startswith(self._DTC_RESP_CODE) ):
				#set the flag that ends the loop
				foundIt = True
		if(foundIt == False):
			#tell the user their engine may be off
			raise NoResponseError("Engine may be off")

		#get only the lines we want
		for line in elmLines:
			if( line.startswith(self._DTC_RESP_CODE) ):
				#remove leading response code and all whitespace
				self._dtcs = self._dtcs+[line[len(self._DTC_RESP_CODE):].replace(" ","")]

	def close(self):
		"""Closes the connection to the ELM"""
		#close the serial connection
		if( self._serialConn is not None ):
			self._serialConn.close()
