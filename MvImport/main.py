# Continious Image Capture Script for Hikrobot camera
# Tushar - 29 Nov 2023

import sys
import threading
import keyboard
from PIL import Image
from PIL.ExifTags import TAGS
import piexif
from datetime import datetime

sys.path.append("../MvImport")
from MvCameraControl_class import *

EXIT = False
OUTPUT_IMAGE_DIR = "./"
# OUTPUT_IMAGE_DIR = "/home/orangewood/Orangewood/cashify/image_capture/temp_path/"

# Helper Functions
fileIndex = 0
def fileName(number=1):
    global fileIndex
    fileNameHeader = "HIKROBOT-IMG-"
    fileName = fileNameHeader + str(fileIndex) + "_" + str(number)
    fileIndex += 1
    
    return fileName

# Image Capture Thread
def work_thread(cam=0, pData=0, nDataSize=0):
    stOutFrame = MV_FRAME_OUT()
    memset(byref(stOutFrame), 0, sizeof(stOutFrame))

    frame_number = 1
    while True:
        # if keyboard.is_pressed('space'):
        ret = cam.MV_CC_GetImageBuffer(stOutFrame, 1000)

        timestamp = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
        print("Timestamp of Image Capture: ", timestamp)

        if ret == 0:
            file_name = fileName(frame_number)
            print("Image captured -", file_name)
            image_data = cast(stOutFrame.pBufAddr, POINTER(c_ubyte * nDataSize)).contents     
            image = Image.frombytes('RGB', (stOutFrame.stFrameInfo.nWidth, stOutFrame.stFrameInfo.nHeight),
                                    bytes(image_data))
            
            # Create a new EXIF data dictionary
            exif_dict = {"0th":{}, "Exif":{}, "GPS":{}, "1st":{}, "thumbnail":None}

            # Add the timestamp to the EXIF data
            exif_dict["0th"][piexif.ImageIFD.DateTime] = timestamp.encode()

            # Dump the EXIF data to bytes
            exif_bytes = piexif.dump(exif_dict)

         

            image.save(f'{OUTPUT_IMAGE_DIR}{file_name}.jpg', exif=exif_bytes)
            frame_number += 1
            cam.MV_CC_FreeImageBuffer(stOutFrame)  
        else:
            print("Fatal Error: No image data - RET {ret}")
        
        if EXIT:
            break


# Main program flow starts here

# Find metadata about the camera
SDKVersion = MvCamera.MV_CC_GetSDKVersion()
print("SDK Version ", SDKVersion)

deviceList = MV_CC_DEVICE_INFO_LIST()
tlayerType = MV_GIGE_DEVICE

ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
if ret != 0:
    print ("enum devices fail! ret[0x%x]" % ret)
    sys.exit()

if deviceList.nDeviceNum == 0:
    print("No devices found")
    sys.exit()

print(f"Number of Devices detected: {deviceList.nDeviceNum}")

first_device = cast(deviceList.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)).contents
if first_device.nTLayerType == MV_GIGE_DEVICE:
    print("TLayerType: GigE Device")

strModeName = ""
for per in first_device.SpecialInfo.stGigEInfo.chModelName:
    strModeName = strModeName + chr(per)
print ("Model Name: %s" % strModeName)

nip1 = ((first_device.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
nip2 = ((first_device.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
nip3 = ((first_device.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
nip4 = (first_device.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
print(f"IP Address:{nip1}.{nip2}.{nip3}.{nip4}")
print("")


# Standard procedure to connect device, see documentation
cam = MvCamera()

ret = cam.MV_CC_CreateHandle(first_device)
print(f"RET - Device Handle Response: {ret}")
if ret != 0:
    print(f"Fatal Error: Cannot create device handle - RET {ret}")
    sys.exit()

ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
print(f"RET - Open Device Response: {ret}")
if ret != 0:
    print(f"Fatal Error: Cannot open device - RET {ret}")

# Detect network optimal package size
nPacketSize = cam.MV_CC_GetOptimalPacketSize()
if int(nPacketSize) > 0:
    ret = cam.MV_CC_SetIntValue("GevSCPSPacketSize",nPacketSize)
    if ret != 0:
        print (f"Warning: Setting Packet Size fail - RET {ret}")
else:
    print (f"Warning: Getting Packet Size fail - nPacketSize {nPacketSize}")

# Set trigger mode as off
ret = cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
if ret != 0:
    print (f"Fatal Error: Setting trigger mode failed - RET {ret}")
    sys.exit()

# Get payload size
stParam =  MVCC_INTVALUE()
memset(byref(stParam), 0, sizeof(MVCC_INTVALUE))

ret = cam.MV_CC_GetIntValue("PayloadSize", stParam)
print(f"RET - Payload Size Response: {ret}")
if ret != 0:
    print ("get payload size fail! ret[0x%x]" % ret)
    sys.exit()
nPayloadSize = stParam.nCurValue

ret = cam.MV_CC_StartGrabbing()
if ret != 0:
    print ("start grabbing fail! ret[0x%x]" % ret)
    sys.exit()

data_buf = (c_ubyte * nPayloadSize)()
try:
    hThreadHandle = threading.Thread(target=work_thread, args=(cam, byref(data_buf), nPayloadSize))
    hThreadHandle.start()
except:
    print("Fatal Error: Unable to start a thread")



# ret = cam.MV_CC_StopGrabbing()
# if ret != 0:
#     print ("stop grabbing fail! ret[0x%x]" % ret)
#     del data_buf
#     sys.exit()

# # ch:关闭设备 | Close device
# ret = cam.MV_CC_CloseDevice()
# if ret != 0:
#     print ("close deivce fail! ret[0x%x]" % ret)
#     del data_buf
#     sys.exit()

# # ch:销毁句柄 | Destroy handle
# ret = cam.MV_CC_DestroyHandle()
# if ret != 0:
#     print ("destroy handle fail! ret[0x%x]" % ret)
#     del data_buf
#     sys.exit()
