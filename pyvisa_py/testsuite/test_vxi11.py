import socket
import pytest

from pyvisa_py import common
from unittest.mock import MagicMock, patch
from pyvisa_py.protocols import vxi11
from pyvisa_py.protocols.rpc import Packer, RawTCPClient, TCPPortMapperClient, Unpacker
from pyvisa_py.protocols.vxi11 import CoreClient, ErrorCodes
from pyvisa_py.tcpip import TCPIPInstrVxi11, Vxi11CoreClient
from pyvisa_py.tcpip import VXI11_ERRORS_TO_VISA
from ..sessions import Session, UnknownAttribute, VISARMSession

# Test vxi11.py changes to error handling

# Test enhanced error returns from TCPIPInstrVxi11.read, write to
# map VXI11 errors to VISA errors

def setup_TCPIPinstrVxi11_mock():
    # Short circuit connection so this works w/o a real device
    TCPIPInstrVxi11.__init__ = MagicMock(return_value=None)
    client = TCPIPInstrVxi11(VISARMSession, "TCPIP::169.254.12.34::5678",None, 2000)
    client.interface = MagicMock()
    client.max_recv_size = 1024
    client.attrs = {}
    client._io_timeout = 5000
    client.link = 0
    client.lock_timeout = 5000
    return client

def test_TCPIPinstrVxi11_read():
    client = setup_TCPIPinstrVxi11_mock()
    for map_error in VXI11_ERRORS_TO_VISA.keys():
        client.interface.device_read = MagicMock(side_effect=lambda a,b,c,d,e,f: (map_error, vxi11.RX_END, b'data'))
        data, error = client.read(1024)
        assert error == VXI11_ERRORS_TO_VISA[map_error]
        if (map_error == 0):
            assert data == b'data'
        else:
            assert data == b''


def test_TCPIPinstrVxi11_write():
    client = setup_TCPIPinstrVxi11_mock()
    for map_error in VXI11_ERRORS_TO_VISA.keys():
        # Need to return the length of the block written, just use length of block passed in
        client.interface.device_write = MagicMock(side_effect=lambda a,b,c,d,block: (map_error, len(block)))
        size, error = client.write(b'data')

        assert error == VXI11_ERRORS_TO_VISA[map_error]


# Test changes CoreClient read and write to throw a timeout
# error when the timeout is exceeded vs generic io_error

def setup_CoreClient_mock():
    CoreClient.__init__ = MagicMock(return_value=None)
    client = CoreClient("169.254.12.34:5678")
    client.packer = MagicMock()
    client.unpacker = MagicMock()
    return client


def test_CoreClient_device_read():
    # Short circuit connection so this works w/o a real device
    client=setup_CoreClient_mock()
    def raise_timeout(a,b,c,d):
        raise socket.timeout("testtimout")
    client.make_call = MagicMock(side_effect=raise_timeout)
    error, reason, data = client.device_read(0, 1024, 5000, 5000, 0, 0)
    
    assert error == ErrorCodes.io_timeout
    assert reason == "testtimout"
    # TODO - Does make_call return bytes or string?
    # It looks like the higher level code forces to bytes,
    # but the read unpack already returns bytes. The error
    # return case returns a string.
    assert data == ''

def test_CoreClient_device_write():
    # Short circuit connection so this works w/o a real device
    client = setup_CoreClient_mock()
    def raise_timeout(a,b,c,d):
        raise socket.timeout("testtimout")
    client.make_call = MagicMock(side_effect=raise_timeout)
    
    error, reason = client.device_write(0, 5000, 5000, 0, b'data')
    
    assert error == ErrorCodes.io_timeout
    assert reason == "testtimout"
