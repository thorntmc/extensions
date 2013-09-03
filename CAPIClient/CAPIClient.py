#!/usr/bin/env python 
#
# Copyright (c) 2013, Arista Networks, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#  - Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#  - Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#  - Neither the name of Arista Networks nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARISTA NETWORKS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Command API Client
#
#    Version 1.0 10/9/2013
#    Written by: 
#       Andrei Dvornic, Arista Networks
#
#    Revision history:
#       1.0 - initial release

'''
   DESCRIPTION 
      Client library for Command API.

   INSTALLATION
      Requirements:                                     
         - Python 2.6 or later: http://www.python.org
         - jsonrpclib: https://github.com/joshmarshall/jsonrpclib

      Simply add CAPIClient.py to the Python path.

      Usage example:

         import CAPIClient

         client = CAPIClient.CommandApiClient( <hostname>, <username>, <password> )
         res = client.runEnableCmds( [ 'show version', 
                                       'show interfaces' ] )
         print 'TotalMemory: %d' % res[ 0 ][ 'memTotal' ]
         print 'Interfaces: %s' % res[ 1 ][ 'interfaces' ].keys()

         et1 = client.interface( 'Ethernet1' )
         et1.runConfigCmds( 'description This is Ethernet1')
         print et1.status()[ 'description' ]

         vlan1 = client.vlan( 1234 )
         print vlan1.status()

   COMPATIBILITY 
      Version 1.0 has been developed and tested using Python 2.7,
      but should work on any system supporting Python 2.6 or
      later. Please reach out to support@aristanetworks.com for
      assistance if needed.

   LIMITATIONS
      Command API is only available starting EOS-4.12.0.
'''

import jsonrpclib
import socket

class Error( Exception ):
   pass

class InvalidInterfaceError( Error ):
   '''
   Raised when an InterfaceClient object is being created
   for an invalid interface.
   '''
   pass

class InvalidVlanError( Error ):
   '''
   Raised when a VlanClient object is being created
   for an invalid vlan.
   '''
   pass

class ConnectionError( Error ):
   '''
   Raised when connection to a Command API server cannot
   be established.
   '''
   pass

class InterfaceClient( object ):
   '''
   A Command API interface client.

   This object can be used in order to configure and retrieve the
   status of a network interface.
   '''

   def __init__( self, name, client ):
      '''
      Keyword arguments:
         name   -- interface name
         client -- CommandApiClient object 

      Raises InvalidInterfaceError if the name of the interface 
      is invalid.

         > InterfaceClient( 'Etthernet1', client )
         *** InvalidInterfaceError: Etthernet1
      '''
      self.name = name.strip()
      self.client = client

      # Check interface name
      try:
         self.client.runIntfConfigCmds( self.name, [] )
      except jsonrpclib.jsonrpc.ProtocolError:
         raise InvalidInterfaceError( self.name )
      
   def runConfigCmds( self, cmds ):
      '''
      Runs commands in interface-config mode and returns a list of
      Command API results.

         > et1.runConfigCmds( [ 'description 1', 'description 2' ] )
         [{}, {}]

      Keyword arguments:
         cmds -- list of interface-config mode commands

      Raises ProtocolError if any of the input commands is not valid.

         > et1.runConfigCmds( [ 'descriptionn 1' ] )
         *** ProtocolError: (1002, u"CLI command 4 of 4 'descriptionn 1' failed: 
         invalid command")
      '''
      return self.client.runIntfConfigCmds( self.name, cmds )

   def status( self ):
      '''
      Returns the Command API status of the interface.
      '''
      result = self.client.runEnableCmds( [ 'show interfaces %s status' % 
                                            self.name ] )
      return result[ 0 ][ 'interfaceStatuses' ].values()

class VlanClient( object ):
   '''
   A Command API vlan client.

   This object can be used in order to configure and retrieve the
   status of a vlan.
   '''

   def __init__( self, vlan, client ):
      '''
      Keyword arguments:
         vlan   -- vlan number
         client -- CommandApiClient object 

      Raises InvalidVlanError if the vlan is outside the valid range.

         > VlanClient( 5000, conn )
         *** InvalidVlanError: 5000
      '''
      self.vlan = vlan
      self.client = client

      # Check vlan
      try:
         self.client.runVlanConfigCmds( self.vlan, [] )
      except jsonrpclib.jsonrpc.ProtocolError:
         raise InvalidVlanError( self.vlan )
      
   def runConfigCmds( self, cmds ):
      '''
      Runs commands in vlan-config mode and returns a list of Command
      API results.

         > vlan10.runConfigCmds( [ 'name 1', 'name 2' ] )
         [{}, {}]

      Keyword arguments:
         cmds -- list of vlan-config mode commands

      Raises ProtocolError if any of the input commands is invalid.

         > vlan10.runConfigCmds( [ 'nname 1' ] )
         *** ProtocolError: (1002, u"CLI command 4 of 4 'nname 1' failed: 
         invalid command")
      '''
      return self.client.runVlanConfigCmds( self.vlan, cmds )

   def status( self ):
      '''
      Returns the Command API status of the vlan.
      '''
      result = self.client.runEnableCmds( [ 'show vlan %s' % self.vlan ] ) 
      return result[ 0 ][ 'vlans' ][ str( self.vlan ) ]

class CommandApiClient( object ):

   def __init__( self, mgmtIpOrHostname, username, password, 
                 enablePassword='' ):
      '''
      Keyword arguments:
         mgmtIpOrHostname -- IP address or hostname of Command API server
         username         -- username
         password         -- password corresponding to username
         enablePassword   -- enable mode password

      Raises ConnectionError if connection to Command API server cannot
      be established:

         > CommandApiClient( '1.3.4.5', 'usr', 'pass')
         *** ConnectionError: https://usr:pass@1.2.3.4/command-api
      '''
      self.host = mgmtIpOrHostname
      self.username = username
      self.password = password
      self.enablePassword = enablePassword
      url = 'https://%s:%s@%s/command-api' % ( username, password,
                                               mgmtIpOrHostname )
      self.client = jsonrpclib.Server( url  )

      try:
         self.runEnableCmds( [] )
      except socket.error:
         raise ConnectionError( url )

   def runEnableCmds( self, cmds ):
      '''
      Runs commands in enable mode and returns a list of Command API
      results.

         > client.runEnableCmds( [ 'show version' ] )
         [{u'memTotal': 997796, u'internalVersion': u'4.12.0', ...}]

      Keyword arguments:
         cmds -- list of enable mode commands

      Raises ProtocolError if any of the input commands is invalid.

         > client.runEnableCmds( [ 'showz version' ] )
         *** ProtocolError: (1002, u"CLI command 4 of 4 'showz version' failed: 
         invalid command")
      '''
      return self.client.runCmds( 1, [ { 'cmd': 'enable', 
                                         'input': self.enablePassword } ] +
                                  cmds )[ 1: ]

   def runConfigCmds( self, cmds ):
      '''
      Runs commands in config mode and returns a list of Command API
      results.

         > client.runConfigCmds( [ 'hostname veos1', 'lldp run' ] )
         [{},{}]

      Keyword arguments:
         cmds -- list of config mode commands

      Raises ProtocolError if any of the input commands is invalid.

         > client.runConfigCmds( [ 'hostname' ] )
         *** ProtocolError: (1002, u"CLI command 4 of 4 'hostname' failed: 
         invalid command")
      '''
      return self.runEnableCmds( [ 'configure' ] + cmds )[ 1: ]
   
   def runIntfConfigCmds( self, intf, cmds ):
      '''
      Runs commands in interface-config mode and returns a list of
      Command API results.

         > client.runIntfConfigCmds( 'Ethernet1', [ 'description 1', 
           'description 2' ] )
         [{}, {}]

      Keyword arguments:
         intf -- interface name
         cmds -- list of interface-config mode commands

      Raises ProtocolError if any of the input commands is not valid.

         > client.runIntfConfigCmds( 'Ethernet1', [ 'descriptionn 1' ] )
         *** ProtocolError: (1002, u"CLI command 4 of 4 'descriptionn 1' failed:
         invalid command")
      '''
      return self.runConfigCmds( [ 'interface %s' % intf ] + cmds )[ 1: ]
   
   def runVlanConfigCmds( self, vlan, cmds ):
      '''
      Runs configuration commands in vlan-config mode and returns a
      list of Command API results.

         > client.runVlanConfigCmds( 10, [ 'name 1', 'name 2' ] )
         [{}, {}]

      Keyword arguments:
         vlan -- vlan number
         cmds -- list of vlan-config mode commands

      Raises ProtocolError if any of the input commands is invalid.

         > client.runVlanConfigCmds( 10, [ 'nname 1' ] )
         *** ProtocolError: (1002, u"CLI command 4 of 4 'nname 1' failed: 
         invalid command")
      '''
      return self.runConfigCmds( [ 'vlan %s' % vlan ] + cmds )[ 1: ]
   
   def runMlagConfigCmds( self, cmds ):
      '''
      Runs configuration commands in mlag-config mode and returns a
      list of Command API results.

         > client.runMlagConfigCmds( [ 'reload-delay 60' ] )
         [{}]

      Keyword arguments:
         cmds -- list of mlag-config mode commands

      Raises ProtocolError if any of the input commands is invalid.

         > client.runMlagConfigCmds( [ 'reloaddelay 60' ] )
         *** ProtocolError: (1002, u"CLI command 4 of 4 'reloaddelay 60' failed: 
         invalid command")
      '''
      return self.runConfigCmds( [ 'mlag configuration' ] + cmds )[ 1: ]

   def interface( self, name ):
      '''
      Returns an InterfaceClient object corresponding to the interface name.

      Keyword arguments:
         name -- interface name
      '''
      return InterfaceClient( name, self )

   def vlan( self, vlan ):
      '''
      Returns a VlanClient object corresponding to the vlan number.

      Keyword arguments:
         vlan -- vlan number
      '''
      return VlanClient( vlan, self )
