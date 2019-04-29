

import numpy as np
from numpy.random import random_integers
import os
import cv2 as cv
import time

stTime = time.clock()
#*********************************** param *************************************#
_config = '2'
_blockSize = 3
_visual = False

#*********************************** global ************************************#
CarList,RoadList,CrossList = [],[],[]
TheCarport = None
Time = -1
PriorStTime,PriorTime = -1,-1
PriorCarDistribution = [0, 0, 0]


Record = {}

RouteMap = {}
CrossCrossRoad = []
CrossRoadCross = []
CrossRoadDirection = []
RoadDirectionCross = []
CarDistribution = [0, 0, 0]



CarOriId2CarId,RoadOriId2RoadId,CrossOriId2CrossId = {},{},{}
CarInfo,RoadInfo,CrossInfo,AnswerInfo,PresetAnswerInfo = [],[],[],[],[]
CarSpeedRange = {}




class channelQueue():
    def __init__(self,id_,y,size,speed):
        self.id_ = id_
        self.y = y
        self.channel = [None]*(size+1)
        self.size = size + 1
        self.speed = speed
        self.frontIndex = 0
        self.backIndex = 0
        self.list_ = [None]*(size+1)
        self.list_Length = 0
    # archive and load
    def front(self):
        if self.frontIndex != self.backIndex:
            return self.channel[self.frontIndex]
        else:
            return None
    def back(self):
        if self.frontIndex != self.backIndex :
            if self.backIndex!=0:
                return self.channel[self.backIndex-1]
            else:
                return self.channel[-1]
        else:
            return None
    def put(self,carId):
        self.channel[self.backIndex]=carId
        if self.backIndex<self.size-1:
            self.backIndex += 1
        else:
            self.backIndex = 0
        if self.backIndex == self.frontIndex:
            print(self.id_,self.frontIndex,self.backIndex)
            print("ChannelQueue overflow!")
    def pop(self):
        if self.frontIndex == self.backIndex:
            print("ChannelQueue is already empty!")
            return
        if self.frontIndex < self.size-1:
            self.frontIndex += 1
        else:
            self.frontIndex = 0
    def nextStart(self):
        self.nextIndex = self.frontIndex
    def next(self):
        if self.nextIndex != self.backIndex:
            carId = self.channel[self.nextIndex]
            if self.nextIndex < self.size - 1:
                self.nextIndex += 1
            else:
                self.nextIndex = 0
            return carId
        else:
            return -1
    def stepInit(self):
        global CarList
        if self.frontIndex <= self.backIndex:
            back = self.backIndex
        else:
            back = self.size
        for i in range(self.frontIndex, back):
            CarList[self.channel[i]].stepInit()
        if self.frontIndex > self.backIndex:
            for i in range(0, self.backIndex):
                CarList[self.channel[i]].stepInit()
    def moveInChannel(self):
        global CarList
        frontCarLoc,frontCarState = -1,1
        if self.frontIndex<=self.backIndex:
            back = self.backIndex
        else:
            back = self.size
        #if self.id_ == 0:
        #    print("*"*5)
        for i in range(self.frontIndex, back):
            car = CarList[self.channel[i]]
            v = min(car.__speed__(), self.speed)
            #if self.id_==0:
            #    print(self.channel[i],frontCarLoc,car.__x__(),v)
            if car.__state__() == 2:
                frontCarLoc, frontCarState = car.__x__(), 2
                continue
            elif car.__x__() - v > frontCarLoc:
                car.update(state=2, x=car.__x__() - v)
                frontCarLoc, frontCarState = car.__x__(), 2
            elif frontCarState == 1:
                frontCarLoc, frontCarState = car.__x__(), 1
            else:
                car.update(state=2, x=frontCarLoc + 1)
                frontCarLoc, frontCarState = frontCarLoc + 1, 2
        if self.frontIndex>self.backIndex:
            for i in range(0,self.backIndex):
                car = CarList[self.channel[i]]
                v = min(car.__speed__(), self.speed)
                if car.__state__() == 2:
                    frontCarLoc, frontCarState = car.__x__(), 2
                    continue
                elif car.__x__() - v > frontCarLoc:
                    car.update(state=2, x=car.__x__() - v)
                    frontCarLoc, frontCarState = car.__x__(), 2
                elif frontCarState == 1:
                    frontCarLoc, frontCarState = car.__x__(), 1
                else:
                    car.update(state=2, x=frontCarLoc + 1)
                    frontCarLoc, frontCarState = frontCarLoc + 1, 2
    def firstPriorityCar(self):
        global CarList
        carId = self.front()
        if carId is None:
            return None
        if CarList[carId].__state__()==2:
            self.moveInChannel()
            return None
        if CarList[carId].__x__() >= min(self.speed,CarList[carId].__speed__()):
            self.moveInChannel()
            return None
        return carId
    def toList(self):
        global CarList,CarInfo
        list_ = [-1]*(self.size-1)
        if self.frontIndex<=self.backIndex:
            back = self.backIndex
        else:
            back = self.size
        for i in range(self.frontIndex, back):
            car = CarList[self.channel[i]]
            list_[car.__x__()] = CarInfo[self.channel[i]][0]
        if self.frontIndex > self.backIndex:
            for i in range(0, self.backIndex):
                car = CarList[self.channel[i]]
                list_[car.__x__()] = CarInfo[self.channel[i]][0]
        return list_

class Car():
    def __init__(self,id_, from_, to_, speed_, planTime_,priority_,preset_):
        # **** statistic param **** #
        self.id_, self.from_, self.to_, self.speed_, self.planTime_,self.priority_,self.preset_ = \
            id_, from_, to_, speed_, planTime_,priority_,preset_
        self.carColor = [int(value) for value in random_integers(0, 255, [3])]
        # **** dynamic param **** #
        self.state,self.nextRoadId = 0,None
        self.x, self.y = 0, 0
        self.presentRoadId,self.roadDirection = None,None
        # car route record
        self.route = []
        self.routeIndex = 1
        # simulate #
        self.stTime = None
        self.endTime = None
    # states update
    def stepInit(self):
        self.state = 1
    def update(self, state, x=None, y=None, presentRoadId=None, roadDirection=None):
        global Time
        if self.state != 0 or presentRoadId is not None:
            self.state = state
        self.x = x if x is not None else self.x
        self.y = y if y is not None else self.y
        self.presentRoadId = presentRoadId if presentRoadId is not None else self.presentRoadId
        self.roadDirection = roadDirection if roadDirection is not None else self.roadDirection
        if presentRoadId is not None:
            self.nextRoadId = None
    # route
    def loadRoute(self,data):
        assert data[0]>=self.planTime_,print(self.id_,self.planTime_,data,'ATD earlier than planTime')
        self.route = data[1:]
    def next(self):
        if self.nextRoadId is not None:
            return self.nextRoadId
        if self.routeIndex == self.route.__len__():
            return None
        self.nextRoadId = self.route[self.routeIndex]
        self.routeIndex += 1
        return self.nextRoadId
    def end(self,time):
        self.endTime = time
    def runTime(self):
        return self.endTime-self.planTime_
    # **** statistic param **** #
    def __id__(self):
        return self.id_
    def __from__(self):
        return self.from_
    def __to__(self):
        return self.to_
    def __speed__(self):
        return self.speed_
    def __planTime__(self):
        self.planTime_
    def isPriority(self):
        return self.priority_
    def __color__(self):
        return self.carColor
    # **** dynamic param **** #
    def __state__(self):
        return self.state
    def __x__(self):
        return self.x
    def __y__(self):
        return self.y
    def __presentRoadId__(self):
        return self.presentRoadId
    def __roadDirection__(self):
        return self.roadDirection

class Road():
    def __init__(self,id_, length_, speed_, channel_,from_,to_,direction):
        # **** statistic param **** #
        self.id_, self.length_, self.speed_, self.channel_, self.from_,self.to_,self.direction = \
            id_, length_, speed_, channel_, from_, to_, direction
        self.carCapcity = self.length_ * self.channel_
        # **** dynamic param **** #
        self.queues = [channelQueue(id_,i,length_,speed_) for i in range(self.channel_)]
        self.carNum = 0
        if speed_ <= 8:
            self.roadColor = [0, 0, 0]
        elif speed_<12:
            self.roadColor = [255, 0, 0]
        else:
            self.roadColor = [0, 255, 0]
        # **** step param ****#
        self.firstPriorityCarChannel = 0
        self.channelFirstPriorityCar = [None] * self.channel_
        self.full = False
    # stepInit
    def stepInit(self):
        global CarList
        self.full = False
        for y in range(self.channel_):
            self.queues[y].stepInit()
            self.queues[y].moveInChannel()
        for y in range(self.channel_):
            self.channelFirstPriorityCar[y] = self.queues[y].firstPriorityCar()
    # car actions
    def firstPriorityCar(self):
        global CarList
        self.firstPriorityCarChannel = 0
        carId = self.channelFirstPriorityCar[0]
        for i in range(1, self.channel_):
            nextCarId = self.channelFirstPriorityCar[i]
            if nextCarId is None:
                continue
            if carId is None:
                self.firstPriorityCarChannel = i
                carId = nextCarId
            elif CarList[nextCarId].isPriority() > CarList[carId].isPriority():
                self.firstPriorityCarChannel = i
                carId = nextCarId
            elif CarList[nextCarId].isPriority() == CarList[carId].isPriority():
                if CarList[nextCarId].__x__() < CarList[carId].__x__():
                    self.firstPriorityCarChannel = i
                    carId = nextCarId
        return carId
    def firstPriorityCarAct(self, action):
        global TheCarport
        if action == 0:
            self.queues[self.firstPriorityCarChannel].pop()
            self.carNum -= 1
        self.channelFirstPriorityCar[self.firstPriorityCarChannel] = \
            self.queues[self.firstPriorityCarChannel].firstPriorityCar()
        if action == 0 or action == 1:
            TheCarport.outOfCarport(self.id_,self.direction)
    def receiveCar(self, carId):
        global CarList,TheCarport
        car = CarList[carId]
        if self.full:
            car.update(state=2, x=0)
            return 1
        leftX = max(min(self.speed_, car.__speed__()) - car.__x__(), 0)
        if leftX == 0:
            car.update(state=2,x=0)
            return 1
        for y in range(self.channel_):
            backCarId = self.queues[y].back()
            #RoadList[0][0].queues[0].channel
            if backCarId is None or CarList[backCarId].__x__()<self.length_-leftX:
                self.queues[y].put(carId)
                self.carNum += 1
                car.update(state=2, x=self.length_-leftX, y=y, presentRoadId=self.id_, roadDirection=self.direction)
                return 0
            if CarList[backCarId].__state__() == 1:
                return 2
            if CarList[backCarId].__x__()!=self.length_-1:
                self.queues[y].put(carId)
                self.carNum += 1
                car.update(state=2, x=CarList[backCarId].__x__()+1, y=y, presentRoadId=self.id_, roadDirection=self.direction)
                return 0
        self.full = True
        car.update(state=2, x=0)
        return 1
    def visualizationInfo(self):
        global RoadInfo
        list_ = []
        for y in range(self.channel_):
            list_.append(self.queues[y].toList())
        string = '('
        string += str(RoadInfo[self.id_][0])
        if self.direction == 0:
            string += '_forward_'
        else:
            string += '_backward_'
        string += str(list_)
        string += ')\n'
        return string
    # **** statistic param **** #
    def __id__(self):
        return self.id_
    def __length__(self):
        return  self.length_
    def __speed__(self):
        return self.speed_
    def __channel__(self):
        return self.channel_
    def __from__(self):
        return self.from_
    def __to__(self):
        return self.to_
    def __direction__(self):
        return self.direction
    def __carCapcity__(self):
        return self.carCapcity
    # **** draw **** #
    def getChannel(self,y):
        return self.queues[y]
    def __color__(self):
        return self.roadColor
    # **** dynamic param **** #
    def __carBucket__(self):
        return self.carBucket
    def __backCarLoc__(self):
        return  self.backCarLoc
    def __carNum__(self):
        return self.carNum
    # **** step param **** #
    def __full__(self):
        return self.full

class Cross():
    def __init__(self,id_, road1, road2, road3, road4):
        global CrossRoadDirection,RoadList
        # **** statistic param **** #
        self.id_ = id_
        self.roadIds = [road1,road2,road3,road4]
        self.roadDirection = {self.roadIds[i]:i for i in range(4)}
        self.directionMap = {road1: {road2: 1, road3: 2, road4: -1}, \
                             road2: {road3: 1, road4: 2, road1: -1}, \
                             road3: {road4: 1, road1: 2, road2: -1}, \
                             road4: {road1: 1, road2: 2, road3: -1}}
        self.roadIds.sort()
        self.provider,self.receiverDirection = [],{}
        for roadId in self.roadIds:
            if roadId == -1:
                continue
            direction = CrossRoadDirection[id_][roadId]
            if RoadList[roadId][direction] is not None:
                self.receiverDirection[roadId] = direction
            if RoadList[roadId][(direction+1)%2] is not None:
                self.provider.append(RoadList[roadId][(direction+1)%2])
        # **** dynamic param **** #
        self.finishCarNum=0
        # **** step param **** #
        self.update = False
        self.done = False
    #
    def roadIdsInit(self,roadIds):
        self.roadIds = roadIds
    def stepInit(self):
        self.done = False
    def step(self):
        global CarList, RoadList, CrossList, TheCarport, CarDistribution, PriorCarDistribution
        self.update = False
        # data preapre
        nextCarId = []
        for index in range(self.provider.__len__()):
            nextCarId.append(self.provider[index].firstPriorityCar())
        # loop
        for presentRoadIndex in range(self.provider.__len__()):
            conflict = False
            while nextCarId[presentRoadIndex] != None:
                # same next road and high priority lead to conflict
                for otherRoadIndex in range(self.provider.__len__()):
                    if nextCarId[otherRoadIndex] != None and \
                            self.isConflict(nextCarId[presentRoadIndex],nextCarId[otherRoadIndex]):
                        conflict = True
                        break
                # conflict
                # first priority car exists at road self.provider[otherRoadIndex]
                if conflict:
                    break
                nextRoadId = CarList[nextCarId[presentRoadIndex]].next()
                if nextRoadId is None:
                    assert CarList[nextCarId[presentRoadIndex]].to_ == self.id_,print("!")
                    if CarList[nextCarId[presentRoadIndex]].isPriority():
                        PriorCarDistribution[1] -= 1
                        PriorCarDistribution[2] += 1
                    self.provider[presentRoadIndex].firstPriorityCarAct(0)
                    CarList[nextCarId[presentRoadIndex]].update(state=3)
                    CarList[nextCarId[presentRoadIndex]].end(Time)
                    CarDistribution[1] -= 1
                    CarDistribution[2] += 1
                    self.finishCarNum += 1
                    self.update = True
                else:
                    action = RoadList[nextRoadId][self.receiverDirection[nextRoadId]].receiveCar(nextCarId[presentRoadIndex])
                    if action == 2:
                        # waiting conflict
                        break
                    self.update = True
                    #if action == 0 or action == 1:
                    #    TheCarport.outOfCarport(nextRoadId,self.receiverDirection[nextRoadId])
                    self.provider[presentRoadIndex].firstPriorityCarAct(action)
                nextCarId[presentRoadIndex] = self.provider[presentRoadIndex].firstPriorityCar()
        done = True
        for fromA in range(self.provider.__len__()):
            if nextCarId[fromA] != None:
                done = False
        self.done = done
    def isConflict(self,carIdA,carIdB):
        if carIdA == carIdB:
            return False
        global CarList
        fromRoadIdA, toRoadIdA = CarList[carIdA].__presentRoadId__(), CarList[carIdA].next()
        fromRoadIdB, toRoadIdB = CarList[carIdB].__presentRoadId__(), CarList[carIdB].next()
        fromDirectionA, fromDirectionB = self.roadDirection[fromRoadIdA], self.roadDirection[fromRoadIdB]
        directionA = self.directionMap[fromRoadIdA][toRoadIdA] if toRoadIdA is not None else 2
        directionB = self.directionMap[fromRoadIdB][toRoadIdB] if toRoadIdB is not None else 2
        if (fromDirectionA + directionA) % 4 != (fromDirectionB + directionB) %4:
            return False
        priorityA, priorityB = CarList[carIdA].isPriority(), CarList[carIdB].isPriority()
        if priorityA < priorityB:
            return True
        elif priorityA > priorityB:
            return False
        if directionA < directionB:
            return True
        else:
            return False
    def __done__(self):
        return self.done
    def __update__(self):
        return self.update

class Carport():
    def __init__(self):
        global RoadList,CarList
        self.setRoute =[0]*CarList.__len__()
        self.priorCar=[[[],[]] for i in range(RoadList.__len__())]
        self.car = [[[],[]] for i in range(RoadList.__len__())]
    def carportInit(self,carId,time,roadId):
        global CarList,CrossRoadDirection
        if self.setRoute[carId] >= 1:
            self.setRoute[carId] += 1
            return
        else:
            self.setRoute[carId]=1
        direction = CrossRoadDirection[CarList[carId].__from__()][roadId]
        if CarList[carId].isPriority() == 1:
            self.priorCar[roadId][direction].append([time, carId])
        else:
            self.car[roadId][direction].append([time, carId])
    def simulateInit(self):
        global RoadList
        for i in range(RoadList.__len__()):
            self.priorCar[i][0].sort()
            self.car[i][0].sort()
            if RoadList[i][1] is not None:
                self.priorCar[i][1].sort()
                self.car[i][1].sort()
    def outOfCarport(self,roadId,direction,all=False):
        global Time,RoadList,CarDistribution,PriorCarDistribution, PriorStTime
        road = RoadList[roadId][direction]
        if road.__full__():
            return
        temp = []
        for i in range(self.priorCar[roadId][direction].__len__()):
            time, carId = self.priorCar[roadId][direction][i]
            if time > Time:
                temp.extend(self.priorCar[roadId][direction][i:])
                break
            else:
                action = road.receiveCar(carId)
                if action != 0:
                    temp.append(self.priorCar[roadId][direction][i])
                    continue
                else:
                    # prior car start time
                    if PriorStTime == -1:
                        PriorStTime = time
                    PriorCarDistribution[0] -= 1
                    PriorCarDistribution[1] += 1
                    CarDistribution[0] -= 1
                    CarDistribution[1] += 1
        self.priorCar[roadId][direction] = temp
        if all:
            temp = []
            for i in range(self.car[roadId][direction].__len__()):
                time, carId = self.car[roadId][direction][i]
                if time > Time:
                    temp.extend(self.car[roadId][direction][i:])
                    break
                else:
                    action = road.receiveCar(carId)
                    if action != 0:
                        temp.extend(self.car[roadId][direction][i:])
                        break
                    else:
                        CarDistribution[0] -= 1
                        CarDistribution[1] += 1
            self.car[roadId][direction] = temp

class simulation():
    def __init__(self):
        self.dead = False
        self.unfinishedCross=None
        self.f = open('distribution.txt','w')
    def step(self):
        global CarList, RoadList, CrossList, TheCarport,Time
        # step1
        #print("step1")
        for i in range(RoadList.__len__()):
            RoadList[i][0].stepInit()
            TheCarport.outOfCarport(i,0)
            if RoadList[i][1] is not None:
                RoadList[i][1].stepInit()
                TheCarport.outOfCarport(i,1)
        for i in range(CrossList.__len__()):
            CrossList[i].stepInit()
        # step2
        #print("step2")
        self.unfinishedCross = [i for i in range(CrossList.__len__())]
        while self.unfinishedCross.__len__() > 0:
            self.dead = True
            nextCross = []
            for crossId in self.unfinishedCross:
                cross = CrossList[crossId]
                cross.step()
                if not cross.__done__():
                    nextCross.append(crossId)
                if cross.__update__() or cross.__done__():
                    self.dead = False
            self.unfinishedCross = nextCross
            if self.dead:
                print("dead lock in", self.unfinishedCross)
                return
        # step 3
        #print("step3")
        for i in range(RoadList.__len__()):
            TheCarport.outOfCarport(i,0,True)
            if RoadList[i][1] is not None:
                TheCarport.outOfCarport(i,1,True)
    def simulate(self):
        global Time,CarDistribution,PriorCarDistribution,RoadList,TheGraph,priorCarNum,PriorTime
        while True:
            Time += 1
            self.step()
            #TheLog.write()
            if _visual:
                TheGraph.drawMap()
            if PriorCarDistribution[2] == priorCarNum and PriorTime==-1:
                PriorTime = Time
            print(Time,CarDistribution,sum(CarDistribution),PriorCarDistribution,sum(PriorCarDistribution))
            self.f.write("Time:"+str(Time)+",total:"+str(CarDistribution)+", prior:"+str(PriorCarDistribution)+"\n")
            if CarDistribution[2] == sum(CarDistribution):
                return
            if self.dead:
                return

class Graph():
    def __init__(self):
        # cross
        self.crossLoc = None
        self.locCross = None
        # block
        self.crossBlock = None
        self.block = None
        self.blockColor = None
        self.blockCongestion = None
        # visualization
        self.savePath = './rebornPictures'
        if not os.path.exists(self.savePath):
            os.mkdir(self.savePath)
        # cross
        self.maxX,self.maxY = None,None
        self.crossDistance = 150
        self.crossRadius = 14
        # road
        self.roadLoc = None
        self.channelWidth = 5
        self.channelDistance = 3
        self.roadLength = self.crossDistance - self.crossRadius * 4
    # loc gen
    def graphGen(self):
        global CrossInfo,RoadList, CrossRoadDirection
        #******************************* locations **********************************#
        # cross to loc
        self.crossLoc = [[-233,-233]]*CrossInfo.__len__()
        # set cross 0 as the start point
        self.dfs(-233,0,-233)
        minLoc,maxLoc=[0,0],[0,0]
        for i in range(self.crossLoc.__len__()):
            minLoc[0] = min(self.crossLoc[i][0],minLoc[0])
            minLoc[1] = min(self.crossLoc[i][1],minLoc[1])
            maxLoc[0] = max(self.crossLoc[i][0],maxLoc[0])
            maxLoc[1] = max(self.crossLoc[i][1],maxLoc[1])
        maxLoc[0],maxLoc[1] = maxLoc[0] - minLoc[0],maxLoc[1] - minLoc[1]
        self.maxX, self.maxY = maxLoc[0],maxLoc[1]
        for i in range(self.crossLoc.__len__()):
            self.crossLoc[i][0],self.crossLoc[i][1] = self.crossLoc[i][0]-minLoc[0],self.crossLoc[i][1]-minLoc[1]
        # location to cross
        self.locCross = [[-1 for i in range(maxLoc[1]+1)] for j in range(maxLoc[0]+1)]
        for i in range(CrossList.__len__()):
            self.locCross[self.crossLoc[i][0]][self.crossLoc[i][1]] = i
        # ******************************* blocks **********************************#
        # cross to block
        self.crossBlock = [None for i in range(CrossInfo.__len__())]
        blockX = int(maxLoc[0]/_blockSize) if maxLoc[0] % _blockSize <=1  else int(maxLoc[0]/_blockSize)+1
        blockY = int(maxLoc[1]/_blockSize) if maxLoc[1] % _blockSize <=1  else int(maxLoc[1]/_blockSize)+1
        # cross in block
        self.block = [[[] for i in range(blockY)]for j in range(blockX)]
        # block color
        self.blockColor = [[[int(value) for value in np.random.random_integers(126, 255, [3])] for i in range(blockY)]for j in range(blockX)]
        for x in range(blockX):
            for y in range(blockY):
                endX = maxLoc[0]+1 if x == blockX-1 else (x+1)*_blockSize
                endY = maxLoc[1]+1 if y == blockY-1 else (y+1)*_blockSize
                for i in range(x*_blockSize,endX):
                    for j in range(y*_blockSize,endY):
                        if self.locCross[i][j]!=-1:
                            self.crossBlock[self.locCross[i][j]] = [x,y]
                            self.block[x][y].append(self.locCross[i][j])
        # ******************************* roads ***********************************#
        self.roadLoc = [[None,None] for i in range(RoadList.__len__())]
        for crossId in range(CrossList.__len__()):
            crossX,crossY = self.crossLoc[crossId]
            for i,roadId in enumerate(CrossInfo[crossId][1:]):
                # roadId is invalid
                if roadId == -1:
                    continue
                # only consider the provider
                direction = (CrossRoadDirection[crossId][roadId] + 1) % 2
                unitL = self.roadLength / RoadList[roadId][0].__length__()
                loc = [0,0,0,0,0]
                if i == 0:
                    loc[0] = (crossX+1)*self.crossDistance - self.channelDistance
                    loc[1] = (crossY+1)*self.crossDistance - self.crossRadius * 2
                    loc[2] = -self.channelWidth
                    loc[3] = -unitL
                    loc[4] = 0
                elif i == 1:
                    loc[0] = (crossX + 1) * self.crossDistance + self.crossRadius * 2
                    loc[1] = (crossY + 1) * self.crossDistance - self.channelDistance
                    loc[2] = unitL
                    loc[3] = -self.channelWidth
                    loc[4] = 1
                elif i == 2:
                    loc[0] = (crossX + 1) * self.crossDistance + self.channelDistance
                    loc[1] = (crossY + 1) * self.crossDistance + self.crossRadius * 2
                    loc[2] = self.channelWidth
                    loc[3] = unitL
                    loc[4] = 0
                elif i == 3:
                    loc[0] = (crossX + 1) * self.crossDistance - self.crossRadius * 2
                    loc[1] = (crossY + 1) * self.crossDistance + self.channelDistance
                    loc[2] = -unitL
                    loc[3] = self.channelWidth
                    loc[4] = 1
                else:
                    print("wrong direction in Graph.graphGen()")
                self.roadLoc[roadId][direction] = loc
    def dfs(self,previousCrossId,presentCrossId,direction):
        '''
                    direction:
                        previousCross -> presentCross
                        0,1,2,3 denote north,east,south,west
                        -233 denotes the start point
        '''
        global CrossInfo, CrossRoadCross , CrossList
        # if visited
        if self.crossLoc[presentCrossId] != [-233, -233]:
            return
        if direction == 0:
            self.crossLoc[presentCrossId] = [self.crossLoc[previousCrossId][0], self.crossLoc[previousCrossId][1] - 1]
        elif direction == 1:
            self.crossLoc[presentCrossId] = [self.crossLoc[previousCrossId][0] + 1, self.crossLoc[previousCrossId][1]]
        elif direction == 2:
            self.crossLoc[presentCrossId] = [self.crossLoc[previousCrossId][0], self.crossLoc[previousCrossId][1] + 1]
        elif direction == 3:
            self.crossLoc[presentCrossId] = [self.crossLoc[previousCrossId][0] - 1, self.crossLoc[previousCrossId][1]]
        elif direction == -233:
            self.crossLoc[presentCrossId] = [0,0]
        if direction!=-233:
            direction_ = -1
            for i, roadId in enumerate(CrossInfo[presentCrossId][1:]):
                if roadId != -1 and CrossRoadCross[presentCrossId][roadId] == previousCrossId:
                    direction_ = i
                    break
            directionAdjust = (direction - direction_ + 2)
        else:
            directionAdjust = 0
        for i in range((4-directionAdjust)%4):
            temp =  CrossInfo[presentCrossId][1]
            CrossInfo[presentCrossId][1:-1] = CrossInfo[presentCrossId][2:]
            CrossInfo[presentCrossId][-1] = temp
        CrossList[presentCrossId].roadIdsInit(CrossInfo[1:])
        for i, roadId in enumerate(CrossInfo[presentCrossId][1:]):
            if roadId != -1:
                nextCross = CrossRoadCross[presentCrossId][roadId]
                self.dfs(presentCrossId, nextCross, i % 4)
    def drawMap(self):
        global CrossList,Time
        img = np.ones(((self.maxY+2)*self.crossDistance, (self.maxX+2)*self.crossDistance, 3), np.uint8) * 255
        # draw cross
        self.drawRoads(img)
        self.drawCross(img)
        cv.imwrite(self.savePath + '/%5d.jpg' % Time, img)
    def drawRoads(self,img):
        global CarList, RoadList
        # draw road
        for roadId in range(RoadList.__len__()):
            fromCross,toCross = RoadList[roadId][0].__from__(),RoadList[roadId][0].__to__()
            fromX,fromY = self.crossLoc[fromCross]
            toX,toY =  self.crossLoc[toCross]
            cv.line(img, ((fromX+1)*self.crossDistance,(fromY+1)*self.crossDistance),
                    ((toX+1)*self.crossDistance,(toY+1)*self.crossDistance), color=[0,0,0], thickness=1)
            self.drawRoad(img,roadId,0)
            if RoadList[roadId][1] is not None:
                self.drawRoad(img, roadId, 1)
    def drawRoad(self,img,roadId,direction):
        length, channel, color = \
            RoadList[roadId][0].__length__(), RoadList[roadId][0].__channel__(),RoadList[roadId][0].__color__()
        loc = self.roadLoc[roadId][direction]
        x, y = loc[0], loc[1]
        if loc[-1] == 0:
            # draw road
            for i in range(length + 1):
                cv.line(img, (int(x), int(y + i * loc[3])),
                        (int(x + channel * loc[2]), int(y + i * loc[3])), color=color, thickness=1)
            for i in range(channel + 1):
                cv.line(img, (int(x + i * loc[2]), int(y)),
                        (int(x + i * loc[2]), int(y + length * loc[3])), color=color, thickness=1)
            # draw car
            for i in range(channel):
                maxX = x + i * loc[2] if loc[2] < 0 else x + (i + 1) * loc[2]
                minX = x + (i + 1) * loc[2] if loc[2] < 0 else x + i * loc[2]
                channelqueue = RoadList[roadId][direction].getChannel(i)
                channelqueue.nextStart()
                carId = channelqueue.next()
                while carId != -1:
                    carX = CarList[carId].__x__()
                    color = CarList[carId].__color__()
                    maxY = y + carX * loc[3] if loc[3]<0 else y + (carX+1) * loc[3]
                    minY = y + (carX+1) * loc[3] if loc[3]<0 else y + carX * loc[3]
                    cv.rectangle(img, (int(minX),int(minY)),(int(maxX),int(maxY)), color=color, thickness=-1)
                    carId = channelqueue.next()
        else:
            # draw road
            for i in range(length + 1):
                cv.line(img, (int(x+ i * loc[2]), int(y)),
                        (int(x + i * loc[2]), int(y + channel * loc[3])), color=color, thickness=1)
            for i in range(channel + 1):
                cv.line(img, (int(x), int(y + i * loc[3])),
                        (int(x + length * loc[2]), int(y + i * loc[3])), color=color, thickness=1)
            # draw car
            for i in range(channel):
                maxY = y + i * loc[3] if loc[3] < 0 else y + (i + 1) * loc[3]
                minY = y + (i + 1) * loc[3] if loc[3] < 0 else y + i * loc[3]
                channelqueue = RoadList[roadId][direction].getChannel(i)
                channelqueue.nextStart()
                carId = channelqueue.next()
                while carId != -1:
                    carX = CarList[carId].__x__()
                    color = CarList[carId].__color__()
                    maxX = x + carX * loc[2] if loc[2] < 0 else x + (carX + 1) * loc[2]
                    minX = x + (carX + 1) * loc[2] if loc[2] < 0 else x + carX * loc[2]
                    cv.rectangle(img, (int(minX),int(minY)),(int(maxX),int(maxY)), color=color, thickness=-1)
                    carId = channelqueue.next()
    def drawCross(self,img):
        for x in range(self.block.__len__()):
            for y in range(self.block[0].__len__()):
                block = self.block[x][y]
                color = self.blockColor[x][y]
                for crossId in block:
                    crossX,crossY = self.crossLoc[crossId]
                    mapX,mapY = (crossX+1)*self.crossDistance,(crossY+1)*self.crossDistance
                    cv.circle(img, (mapX, mapY), self.crossRadius, color=color, thickness=-1, lineType=-1)
                    if crossId >= 10:
                        xx, yy = int(mapX - 4 * self.crossRadius / 5), int(mapY + self.crossRadius / 2)
                    else:
                        xx, yy = int(mapX - self.crossRadius / 2), int(mapY + self.crossRadius / 2)
                    cv.putText(img, str(crossId), (xx, yy), cv.FONT_HERSHEY_SIMPLEX, 0.6, [0, 0, 0], 2)

def merge(sortedList1,sortedList2):
    i,j,length1,length2 = 0,0,sortedList1.__len__(),sortedList2.__len__()
    temp = [0]*(length1+length2)
    while(i<length1 and j<length2):
        if sortedList1[i]<sortedList2[j]:
            temp[i+j] = sortedList1[i]
            i += 1
        else:
            temp[i + j] = sortedList2[j]
            j += 1
    for index in range(i,length1):
        temp[index+j]=sortedList1[index]
    for index in range(j,length2):
        temp[index+i]=sortedList2[index]
    return temp



class log():
    def __init__(self,path=None):
        if path is None:
            self.f = open('../config_' + _config + '/logging.txt','w')
    def write(self):
        global RoadList
        self.f.writelines('time:%d\n'%Time)
        for i in range(RoadList.__len__()):
            self.f.writelines(RoadList[i][0].visualizationInfo())
            if RoadList[i][1] is not None:
                self.f.writelines(RoadList[i][1].visualizationInfo())

TheLog = log()
#*********************************** main ************************************#
#**** load .txt files ****#
car_path = '../config_' + _config + '/car.txt'
road_path = '../config_' + _config + '/road.txt'
cross_path = '../config_' + _config + '/cross.txt'
presetAnswer_path = '../config_' + _config + '/presetAnswer.txt'
answer_path = '../config_' + _config + '/answer.txt'


carData = open(car_path, 'r').read().split('\n')[1:]
roadData = open(road_path, 'r').read().split('\n')[1:]
crossData = open(cross_path, 'r').read().split('\n')[1:]
answerData = open(answer_path,'r').read().split('\n')[0:]
presetAnswerData = open(presetAnswer_path,'r').read().split('\n')[1:]

'''
    read,sort,map,rebuild serial number
    read:[[10005,xxx],[10010,yyy],[10001,zzz]]
    sort:[[10001,zzz],[10005,xxx],[10010,yyy]]
    map: {10001:0,10005:1,10010:2}
    rebuild: [[0,zzz],[1,xxx],[2,yyy]]
    CarInfo,RoadInfo,CrossInfo
'''
# read
# line = (id,from,to,speed,planTime
for info in carData:
    id_, from_, to_, speed_, planTime_,priority_, preset_ = info.replace(' ', '').replace('\t', '')[1:-1].split(',')
    try:
        CarSpeedRange[int(speed_)] += 1
    except:
        CarSpeedRange[int(speed_)] = 1
    CarInfo.append([int(id_), int(from_), int(to_), int(speed_), int(planTime_), int(priority_), int(preset_)])

# line = (id,length,speed,channel,from,to,isDuplex)
for info in roadData:
    id_, length_, speed_, channel_, from_, to_, isDuplex_ = info.replace(' ', '').replace('\t', '')[1:-1].split(',')
    RoadInfo.append([int(id_), int(length_), int(speed_), int(channel_), int(from_), int(to_),int(isDuplex_)])

# line = (id,north,east,south,west)
for info in crossData:
    id_, road1,road2,road3,road4 = info.replace(' ', '').replace('\t', '')[1:-1].split(',')
    CrossInfo.append([int(id_),int(road1), int(road2), int(road3), int(road4)])

# sort
CarInfo.sort()
RoadInfo.sort()
CrossInfo.sort()

# map
for i,info in enumerate(CarInfo):
    CarOriId2CarId[info[0]] = i

for i,info in enumerate(RoadInfo):
    RoadOriId2RoadId[info[0]] = i

for i,info in enumerate(CrossInfo):
    CrossOriId2CrossId[info[0]] = i

# rebuild
for i in range(CarInfo.__len__()):
    CarInfo[i][1] = CrossOriId2CrossId[CarInfo[i][1]]
    CarInfo[i][2] = CrossOriId2CrossId[CarInfo[i][2]]

for i in range(RoadInfo.__len__()):
    RoadInfo[i][4] = CrossOriId2CrossId[RoadInfo[i][4]]
    RoadInfo[i][5] = CrossOriId2CrossId[RoadInfo[i][5]]

for i in range(CrossInfo.__len__()):
    for j in range(1,5):
        if CrossInfo[i][j] != -1:
            CrossInfo[i][j] = RoadOriId2RoadId[CrossInfo[i][j]]

# line = (id,time,route)
for info in answerData:
    if info.__len__()<3:
        break
    info = info[1:-1].split(',')
    temp = [CarOriId2CarId[int(info[0])], int(info[1])]
    for roadId in info[2:]:
        temp.append(RoadOriId2RoadId[int(roadId)])
    AnswerInfo.append(temp)

# line = (id,time,route)
for info in presetAnswerData:
    if info.__len__()<3:
        break
    info = info[1:-1].split(',')
    temp = [CarOriId2CarId[int(info[0])], int(info[1])]
    for roadId in info[2:]:
        temp.append(RoadOriId2RoadId[int(roadId)])
    PresetAnswerInfo.append(temp)


#**** create Graph ****#
CrossCrossRoad,CrossRoadCross = [{} for i in range(CrossInfo.__len__())],[{} for i in range(CrossInfo.__len__())]
for crossId,info in enumerate(CrossInfo):
    for roadId in info[1:]:
        if roadId!=-1:
            from_,to_ = RoadInfo[roadId][4:6]
            nextCrossId = from_ if from_ != crossId else to_
            CrossCrossRoad[crossId][nextCrossId]=roadId
            CrossRoadCross[crossId][roadId]=nextCrossId


# **** create Car, Road, Cross, Carport classes **** #
totalCarNum,priorCarNum = 0,0
carSpeed,priorCarSpeed = {},{}
startPoints,endPoints,priorStartPoints,priorEndPoints = {},{},{},{}
minTime,maxTime,minPriorTime,maxPriorTime = 10000,0,10000,0
a,b = [0]*5,[0]*5

CarList = [None]*CarInfo.__len__()
RoadList = [None]*RoadInfo.__len__()
CrossList = [None]*CrossInfo.__len__()
CrossRoadDirection = [{} for i in range(CrossInfo.__len__())]


for i in range(CarInfo.__len__()):
    id_, from_, to_, speed_, planTime_, priority_, preset_ = CarInfo[i]
    CarList[i]=Car(i, from_, to_, speed_, planTime_, priority_, preset_)
    # a0
    totalCarNum += 1
    # a1
    try:
        carSpeed[speed_] += 1
    except:
        carSpeed[speed_] = 1
    # a2
    maxTime,minTime = max(maxTime,planTime_),min(minTime,planTime_)
    # a3
    try:
        startPoints[from_] += 1
    except:
        startPoints[from_] = 1
    # a4
    try:
        endPoints[to_] += 1
    except:
        endPoints[to_] = 1
    if priority_ == 1:
        # a0
        priorCarNum += 1
        # a1
        try:
            priorCarSpeed[speed_] += 1
        except:
            priorCarSpeed[speed_] = 1
        # a2
        maxPriorTime, minPriorTime = max(maxPriorTime, planTime_), min(minPriorTime, planTime_)
        # a3
        try:
            priorStartPoints[from_] += 1
        except:
            priorStartPoints[from_] = 1
        # a4
        try:
            priorEndPoints[to_] += 1
        except:
            priorEndPoints[to_] = 1

a[0] = round(round(totalCarNum/priorCarNum,5)*0.05,4)
a[1] = round(max(carSpeed.keys())*min(priorCarSpeed.keys())/max(priorCarSpeed.keys())/min(carSpeed.keys())*0.2375,5)
a[2] = round(round(maxTime/minTime,5)*round(minPriorTime/maxPriorTime,5)*0.2375,5)
a[3] = round(len(startPoints.keys())/len(priorStartPoints.keys())*0.2375,5)
a[4] = round(len(endPoints.keys())/len(priorEndPoints.keys())*0.2375,5)


b[0] = round(round(totalCarNum/priorCarNum,5)*0.8,5)
b[1] = round(max(carSpeed.keys())*min(priorCarSpeed.keys())/max(priorCarSpeed.keys())/min(carSpeed.keys())*0.05,5)
b[2] = round(round(maxTime/minTime,5)*round(minPriorTime/maxPriorTime,5)*0.05,5)
b[3] = round(len(startPoints.keys())/len(priorStartPoints.keys())*0.05,5)
b[4] = round(len(endPoints.keys())/len(priorEndPoints.keys())*0.05,5)


CarDistribution[0] = totalCarNum
PriorCarDistribution[0] = priorCarNum


for i in range(RoadInfo.__len__()):
    RoadList[i] = [None,None]
    id_, length_, speed_, channel_, from_, to_, isDuplex_ = RoadInfo[i]
    CrossRoadDirection[from_][i] = 0
    CrossRoadDirection[to_][i] = 1
    RoadList[i][0] = Road(i, length_, speed_, channel_, from_, to_,0)
    if isDuplex_==1:
        RoadList[i][1] = Road(i, length_, speed_, channel_, from_, to_, 1)

for i in range(CrossInfo.__len__()):
    id_,road1,road2,road3,road4 = CrossInfo[i]
    CrossList[i] = Cross(i,road1,road2,road3,road4)

TheCarport = Carport()
# load planTime and route
#car
for i in range(PresetAnswerInfo.__len__()):
    CarList[PresetAnswerInfo[i][0]].loadRoute(PresetAnswerInfo[i][1:])

for i in range(AnswerInfo.__len__()):
    CarList[AnswerInfo[i][0]].loadRoute(AnswerInfo[i][1:])

#carport
for i in range(AnswerInfo.__len__()):
    TheCarport.carportInit(AnswerInfo[i][0],AnswerInfo[i][1],AnswerInfo[i][2])

for i in range(PresetAnswerInfo.__len__()):
    TheCarport.carportInit(PresetAnswerInfo[i][0], PresetAnswerInfo[i][1], PresetAnswerInfo[i][2])

'''
for i in range(RoadList.__len__()):
    print(i,TheCarport.priorCar[i][0])
    print(i,TheCarport.priorCar[i][1])
    print(i, TheCarport.car[i][0])
    print(i, TheCarport.car[i][1])
'''
# simulate
TheGraph = Graph()
TheGraph.graphGen()

TheCarport.simulateInit()
simulate = simulation()
simulate.simulate()



priorCarTime,carTime = 0,0
for i in range(CarList.__len__()):
    carTime += CarList[i].runTime()
    if CarList[i].isPriority()==1:
        priorCarTime += CarList[i].runTime()

print("(%d-%d)*%f+%d=%d"%(PriorTime,PriorStTime,round(sum(a),5),Time,round((PriorTime-PriorStTime)*round(sum(a),5),0)+Time))
print("%d*%f+%d=%d"%(priorCarTime,round(sum(b),5),carTime,round(priorCarTime*round(sum(b),5),0)+carTime))



endTime = time.clock()










print(endTime-stTime)


