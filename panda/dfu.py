from __future__ import print_function
import usb1
import struct

# *** DFU mode ***

DFU_DNLOAD = 1
DFU_UPLOAD = 2
DFU_GETSTATUS = 3
DFU_CLRSTATUS = 4
DFU_ABORT = 6

class PandaDFU(object):
  def __init__(self, dfu_serial):
    context = usb1.USBContext()
    for device in context.getDeviceList(skip_on_error=True):
      if device.getVendorID() == 0x0483 and device.getProductID() == 0xdf11:
        try:
          this_dfu_serial = device._getASCIIStringDescriptor(3)
        except Exception:
          pass
        if this_dfu_serial == dfu_serial:
          self._handle = device.open()
          return
    raise Exception("failed to open "+dfu_serial)

  @staticmethod
  def list():
    context = usb1.USBContext()
    dfu_serials = []
    for device in context.getDeviceList(skip_on_error=True):
      if device.getVendorID() == 0x0483 and device.getProductID() == 0xdf11:
        try:
          dfu_serials.append(device._getASCIIStringDescriptor(3))
        except Exception:
          pass
    return dfu_serials

  @staticmethod
  def st_serial_to_dfu_serial(st):
    uid_base = struct.unpack("H"*6, st.decode("hex"))
    return struct.pack("!HHH", uid_base[1] + uid_base[5], uid_base[0] + uid_base[4] + 0xA, uid_base[3]).encode("hex").upper()


  def status(self):
    while 1:
      dat = str(self._handle.controlRead(0x21, DFU_GETSTATUS, 0, 0, 6))
      if dat[1] == "\x00":
        break

  def clear_status(self):
    # Clear status
    stat = str(self._handle.controlRead(0x21, DFU_GETSTATUS, 0, 0, 6))
    if stat[4] == "\x0a":
      self._handle.controlRead(0x21, DFU_CLRSTATUS, 0, 0, 0)
    elif stat[4] == "\x09":
      self._handle.controlWrite(0x21, DFU_ABORT, 0, 0, "")
      self.status()
    stat = str(self._handle.controlRead(0x21, DFU_GETSTATUS, 0, 0, 6))

  def erase(self, address):
    self._handle.controlWrite(0x21, DFU_DNLOAD, 0, 0, "\x41" + struct.pack("I", address))
    self.status()

  def program(self, address, dat, block_size=None):
    if block_size == None:
      block_size = len(dat)
      
    # Set Address Pointer
    self._handle.controlWrite(0x21, DFU_DNLOAD, 0, 0, "\x21" + struct.pack("I", address))
    self.status()

    # Program
    dat += "\xFF"*((block_size-len(dat)) % block_size)
    for i in range(0, len(dat)/block_size):
      ldat = dat[i*block_size:(i+1)*block_size]
      print("programming %d with length %d" % (i, len(ldat)))
      self._handle.controlWrite(0x21, DFU_DNLOAD, 2+i, 0, ldat)
      self.status()

  def reset(self):
    # **** Reset ****
    self._handle.controlWrite(0x21, DFU_DNLOAD, 0, 0, "\x21" + struct.pack("I", 0x8000000))
    self.status()
    try:
      self._handle.controlWrite(0x21, DFU_DNLOAD, 2, 0, "")
      stat = str(self._handle.controlRead(0x21, DFU_GETSTATUS, 0, 0, 6))
    except Exception:
      pass
