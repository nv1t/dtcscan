 #!/usr/bin/env python
###########################################################################
# dtcScan.py
#
# Copyright 2012 David DiPaola
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###########################################################################

import serial
from obd2_codes import pcodes
import time
import sys

#size of the serial input buffer in bytes/characters
BUFF_SIZE = 100
#things we receive
ELM_NEWLINE = "\r"
ELM_INIT_MSG = "ELM327"
SEARCHING_MSG = "SEARCHING..."
CANT_CONN_MSG = "UNABLE TO CONNECT"
DTC_RESP_CODE = "43"
#things we send
ELM_RESET_MSG = "ATZ"+ELM_NEWLINE
DTC_GET_MSG = "03"+ELM_NEWLINE
RPM_MSG = "01 0C"+ELM_NEWLINE
#DTC processing info
DTC_CODE_LEN = 4
DTC_PCODE_PREFIX = {
	'0': "P0",
	'1': "P1",
	'2': "P2",
	'3': "P3",
	'4': "C0",
	'5': "C1",
	'6': "C2",
	'7': "C3",
	'8': "B0",
	'9': "B1",
	'A': "B2",
	'B': "B3",
	'C': "U0",
	'D': "U1",
	'E': "U2",
	'F': "U3",
}



"""Takes semi-formatted DTCs and prints them in plain English.

Arguments:
dtcLine -- a line of DTCs from the ELM327 with spaces and message ID removed
           for example: 045504550455 is 3 EVAP gross leaks

"""
def printDtcs(dtcLine):
	currDtc = ""
	i=0
	for c in dtcLine:
		#if at the start of a DTC
		if (i % DTC_CODE_LEN) == 0:
			#find the right prefix
			currDtc = DTC_PCODE_PREFIX[c]
		#otherwise, append the next character directly
		else:
			currDtc += c
		#if we're at the start/end of a DTC
		if (i % DTC_CODE_LEN) == (DTC_CODE_LEN-1):
			#if there's a code to print
			if currDtc != "P0000":
				print currDtc + ": " + pcodes[currDtc]
		i = i + 1



"""Returns a list of strings representing lines of text received from the
   ELM327

Arguments:
serial -- a serial object which is connected to the ELM327

"""
def getElmLines(serial):
	elmResponse = serial.read(BUFF_SIZE)
	#result = elmResponse.split("\r")
	result = elmResponse.split(ELM_NEWLINE)
	return result	



"""Returns a pyserial object connected to the ELM327

Arguments:
serial_port -- a string representing the name or location of the serial port
baud -- the baud rate to connect at

Throws:
serial.SerialException -- when the serial port can't be opened

"""
def connectElm(serial_port, baud):
	elmResponse = ""
	foundIt = False

	#open the serial port
	ser = serial.Serial(serial_port, baud, timeout=1)

	#read lines until the ELM says its status message
	time.sleep(2) #sleep just to give the serial port time to init
	ser.write(ELM_RESET_MSG)
	while foundIt == False:
		respList = getElmLines(ser)
		for line in respList:
			if line.startswith(ELM_INIT_MSG):
				foundIt = True
	
	return ser



"""Returns a list of DTC responses from the ELM

Arguments:
serial -- a serial connection to the ELM

"""
def getDtcList(serial):
	foundIt = False
	firstLoop = True
	elmLines = []
	result = []
	
	while foundIt != True:
		#ask for DTCs from the ELM
		serial.write(DTC_GET_MSG)
		#get the response, break up into lines
		elmLines = getElmLines(ser)
		#go through the lines
		for line in elmLines:
			#if it's a DTC response
			if line.startswith(DTC_RESP_CODE):
				#set the flag that ends the loop
				foundIt = True
		#if the loop hasn't ended yet, and it's the first time through
		if (foundIt == False) and (firstLoop == True):
			#tell the user their engine may be off
			print "The engine may be off, please turn it on..."
			firstLoop = False
		#give the ELM some time...
		time.sleep(2)

	#get only the lines we want
	for line in elmLines:
		if line.startswith(DTC_RESP_CODE):
			#remove leading response code and all whitespace
			result = result+[line[len(DTC_RESP_CODE):].replace(" ","")]			
	
	return result



"""Main section of the script"""
serial_port = '/dev/ttyUSB0'
baud = 38400
ser = None

#process command line arguments
if(len(sys.argv) >= 2):
	serial_port = sys.argv[1]
	baud = int(sys.argv[2])

#attempt to connect to the ELM327
print("Connecting on "+serial_port+" at "+str(baud)+"baud..."),
sys.stdout.flush()
try:
	ser = connectElm(serial_port, baud)
except serial.SerialException:
	print "\nCouldn't open serial port. No device connected?"
	exit(-1)
print("Connected!")

#send the message to get all of the Diagnostic Trouble Codes
print "Reading Diagnostic Trouble Codes..."
dtcList = getDtcList(ser)
for dtc in dtcList:
	printDtcs( dtc )
	
#close the serial connection
if ser != None:
	ser.close()
