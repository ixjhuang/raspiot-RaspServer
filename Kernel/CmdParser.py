'''CmdParser.py
Parser cmd that from app
'''
import copy
import json
import datetime
from Kernel.DeviceHandler import buildNewDeviceDict
from Kernel.GlobalConstant import DEFAULT_IDENTITY
from Kernel.GlobalConstant import Unauthorized_devices
from UserConfig import IDENTITY

class CmdParser:
    def __init__(self, iotManager):
        self.IotManager = iotManager

    def setCommand(self, conn, target, value):
        target = target.split(':')
        if target[0] == 'room':         # room rename
            old, new = target[1], value
            roomHandler = self.IotManager.getRoomHandler()
            roomHandler.renameRoom(old, new)
            deviceHandler = self.IotManager.getDeviceHandler()
            deviceHandler.moveAllDevice(old, new)
            conn.sendall('Rename succeed.'.encode())

        elif target[0] == 'device':
            oldRoom, deviceName = target[1].split('/')
            newRoom, newDeviceName = value.split('/')
            if oldRoom == newRoom:      # device rename
                pass
            else:                       # device move
                roomHandler = self.IotManager.getRoomHandler()
                roomContent = roomHandler.getRoomContent(oldRoom)
                if roomContent:
                    for d in roomContent['devices']:
                        if d['name'] == deviceName:
                            deviceHandler = self.IotManager.getDeviceHandler()
                            deviceHandler.moveDevice(d['uuid'], newRoom)
                            break

        elif target[0] == 'deviceContent':  # set deviceContent to new value
            roomName, deviceName, deviceContentName = target[1].split('/')
            deviceHandler = self.IotManager.getDeviceHandler()
            result = deviceHandler.setValueToDeviceContent(roomName, deviceName, deviceContentName, value)
            conn.sendall(result.encode())
        print("Finished.")
        conn.close()

    def	getCommand(self, conn, target, value):
        target = target.split(':')
        if target[0] == 'server' and value == 'checkServices':  # check services
            conn.sendall("raspServer is ready.".encode())

        elif target[0] == 'room' and value == 'roomlist':       # get room list
            roomHandler = self.IotManager.getRoomHandler()
            conn.sendall(roomHandler.getRoomJsonList().encode())

        elif target[0] == 'device' and value == 'devicelist':   # get device list
            sendJson = self.buildJSON(target[1])
            conn.sendall(sendJson.encode())
        print("Finished.")
        conn.close()

    def addCommand(self, conn, target, value):
        target = target.split(':')
        if target[0] == 'room':             # add a new room
            roomName = value
            roomHandler = self.IotManager.getRoomHandler()
            conn.sendall(roomHandler.addRoom(roomName).encode())

        elif target[0] == 'device':         # add a new device
            deviceUuid = value
            roomName, deviceName = target[1].split('/')
            deviceDict = buildNewDeviceDict(deviceName, deviceUuid)
            deviceHandler = self.IotManager.getDeviceHandler()
            conn.sendall(deviceHandler.addDevice(roomName, deviceDict).encode())
        print("Finished.")
        conn.close()

    def delCommand(self, conn, target, value):
        if target.split(':')[0] == 'room':      # delete a room from home
            roomName = value
            roomHandler = self.IotManager.getRoomHandler()
            deviceHandler = self.IotManager.getDeviceHandler()
            roomHandler.delRoom(roomName)
            deviceHandler.moveAllDevice(roomName, Unauthorized_devices)
            conn.sendall('Done'.encode())

        elif target.split(':')[0] == 'device':  # delete a device from room and move to Unauthorized_devices
            roomName, deviceName = target.split(':')[1], value
            roomHandler = self.IotManager.getRoomHandler()
            roomContent = roomHandler.getRoomContent(roomName)
            if roomContent:
                for d in roomContent['devices']:
                    if d['name'] == deviceName:
                        deviceHandler = self.IotManager.getDeviceHandler()
                        deviceHandler.moveDevice(d['uuid'], Unauthorized_devices)
                        break
        print("Finished.")
        conn.close()

    def commandParser(self, conn, recvdata):
        if recvdata['identity'] == IDENTITY or recvdata['identity'] == DEFAULT_IDENTITY:
            # cmd, target, value = json.loads(Json)
            # 以免json的Key顺序乱了，不够保险
            cmd, target, value = recvdata['cmd'], recvdata['target'], recvdata['value']
            if cmd == "get":
                self.getCommand(conn, target, value)
            elif cmd == 'set':
                self.setCommand(conn, target, value)
            elif cmd == 'add':
                self.addCommand(conn, target, value)
            elif cmd == 'del':
                self.delCommand(conn, target, value)
        elif recvdata['identity'] == 'device':
            self.IotManager.deviceHandler.setupIotServer(conn, recvdata)


    def buildJSON(self, roomName):
        deviceList = []
        deviceHandler = self.IotManager.getDeviceHandler()
        roomContent = copy.deepcopy(self.IotManager.roomHandler.getRoomContent(roomName))
        if not roomContent:
            return json.dumps([])
        for d in roomContent['devices']:
            if d['status'] is True:
                deviceAttribute = deviceHandler.getDeviceAttributeByUuid(d['uuid'])
                # pop key: 'getter' or 'setter'
                if deviceAttribute:
                    for deviceContent in deviceAttribute['deviceContent']:
                        if deviceContent.get('getter'):
                            deviceContent.pop('getter')
                        elif deviceContent.get('setter'):
                            deviceContent.pop('setter')
                    deviceAttribute['status'] = True
                    deviceList.append(deviceAttribute)
                    continue

            # elif d['status'] is False:
            d['status'] = False
            d['deviceContent'] = []
            deviceList.append(d)

        roomjson = {}
        roomjson['name'] = roomName
        roomjson['updateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        roomjson['devices'] = deviceList

        return json.dumps(roomjson)
