import ctypes

class XINPUT_VIBRATION(ctypes.Structure):
    _fields_=[('wLeftMotorSpeed',ctypes.c_ushort),
              ('wRightMotorSpeed',ctypes.c_ushort)]

xinput=ctypes.windll.xinput9_1_0
XInputSetState=xinput.XInputSetState
XInputSetState.argtypes=[ctypes.c_uint,ctypes.POINTER(XINPUT_VIBRATION)]
XInputSetState.restype=ctypes.c_uint

def rumble(left,right):
    vib=XINPUT_VIBRATION(int(left*65535),int(right*65535))
    XInputSetState(0,ctypes.byref(vib))
