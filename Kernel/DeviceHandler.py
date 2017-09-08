import os
import json
import shutil
import importlib
import threading
from Kernel.GlobalConstant import Unauthorized_devices


class DeviceHandler:

    devicesUuidMapRoom = dict()
    def __init__(self, iotManager):
        self.IotManager = iotManager
        roomContentList = list(self.IotManager.roomHandler.getRoomContentListDict().values())
        for roomContent in roomContentList:
            for index in range(len(roomContent['devices'])):
                # using uuid to map room, make room search faster
                deviceUuid = roomContent['devices'][index]['uuid']
                self.devicesUuidMapRoom[deviceUuid] = roomContent['name']


    def addDevice(self, roomName, device):
        deviceUuid = device['uuid']
        self.devicesUuidMapRoom[deviceUuid] = roomName
        devices = self.getDevicesByRoomName(roomName)
        devices.append(device)
        return 'Add device succeed.'


    def getDevicesByRoomName(self, roomName):
        room = self.IotManager.roomHandler.getRoomContent(roomName)
        devices = room['devices']
        return devices


    def setupIotServer(self, conn, recvdata):
        ''' Setup IotServer in a new thread '''
        threading.Thread(target=self.IotServerSetter, args=(conn, recvdata)).start()


    def IotServerSetter(self, conn, recvdata):
        ''' setup IotServer and add it to iotServerList '''
        ip = recvdata['ip']
        uuid = recvdata['mac']
        deviceName = recvdata['device']
        moduleName = className = recvdata['iotServer']

        try:
            if os.path.exists('IotServer/' + moduleName + '.py') is False:
                IotServerFile = moduleName + '.py'
                shutil.copyfile('Repository/' + IotServerFile, 'IotServer/' + IotServerFile)
            # import module from IotServer/
            iotServerModule = importlib.import_module('IotServer.' + moduleName)
            # import class from module
            iotServerClass = getattr(iotServerModule, className)
            # instantiation
            iotServer = iotServerClass(ip, uuid)

            if self.devicesUuidMapRoom.get(uuid) is None:
                # Add to list of Unauthorized devices
                # self.devicesUuidMapRoom[uuid] = Unauthorized_devices
                conn.sendall(json.dumps({'response':'Setup completed'}).encode()) # for the moment
            # search which room it's belong to
            roomName = self.devicesUuidMapRoom[uuid]

            # set status of this iotServer True
            devices = self.IotManager.roomHandler.getRoomContent[roomName]['devices']
            '''
            if roomName == Unauthorized_devices:
                deviceDict = self.buildNewDeviceDict(deviceName, uuid, iotServer)
                deviceDict['status'] = True
            else:
            '''
            for index in range(len(devices)):
                if devices[index]['uuid'] == uuid:
                    self.IotManager.roomHandler.getRoomContent[roomName]['devices'][index]['status'] = True
                    break
            conn.sendall(json.dumps({'response':'Setup completed'}).encode())
            # exec('print(iotServerList[0].' + iotServerList[0].buildDeviceJSON()['deviceContent'][0]['getter'] + ')')
        except Exception as reason:
            print(__file__ +' Error: ' + str(reason))


def buildNewDeviceDict(deviceName, deviceUuid, iotServer=None):
    ''' build a device by device blueprint '''
    deviceDict = {"name": deviceName,
                  "uuid": deviceUuid,
                  "status": False,
                  "iotServer": None}
    return deviceDict
