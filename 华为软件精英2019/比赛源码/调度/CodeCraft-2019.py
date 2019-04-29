
import sys
import heapq
import time

StTime = time.clock()


#*********************************** param *************************************#
_archiveFrequency = 5
_routeMapUpdateFrequency = 3
_randomSeed = 951022
_PriorMore = 100
_expSmoothRouteMap = 0.8
_routeMapPrarm = [15, 3, 10]
_PriorMore = 100
_postponeSpeed = [14, 16]
_postponeTime = [200, 200]
_priorFactor = None
factor,factorOri,factorMax = None,None,None
_MaxCarNum, _MaxCarNumMax, _MaxCarNumMin, _MaxCarNumTime,\
         =  5000, None, None, None,

_correctionP = 4







#*********************************** global ************************************#
TheCarport = None
TheGraph = None
TheRandom = None
TheStage = None
TheA,TheB = None,None
# total schedual time
Time = -1
TimeSave = [-1,-1]
Time_Stage = [-1 for i in range(4)]
# priority schedual time
StageArchiveTime = [10000 for i in range(4)]
PriorStTime, PriorTime = -1,-1
PriorStTimeSave, PriorTimeSave = [-1,-1],[-1,-1]
PriorStTime_Stage, PriorTime_Stage = [-1 for i in range(4)],[-1 for i in range(4)]
# distribution
CarDistribution = [0,0,0]
CarDistributionSave = [[0,0,0],[0,0,0]]
CarDistribution_Stage = [[0,0,0] for i in range(4)]
PriorCarDistribution = [0,0,0]
PriorCarDistributionSave = [[0,0,0],[0,0,0]]
PriorCarDistribution_Stage = [[0,0,0] for i in range(4)]
CarSpeedDistribution = {}
CarSpeedDistributionSave = [{},{}]
CarSpeedDistribution_Stage = [{} for i in range(4)]

# index map, dataInfo, class list #
CarOriId2CarId,RoadOriId2RoadId,CrossOriId2CrossId = {},{},{}
CarInfo,RoadInfo,CrossInfo,PresetAnswerInfo = [],[],[],[]
CarList,RoadList,CrossList = [],[],[]

# useful map
CrossCrossRoad = []
CrossRoadCross = []
CrossRoadDirection = []
RoadDirectionCross = []

# avoid dead lock strategy
Avoid = []
ArchiveIndex = 0
LoadIndex = 0
LoadTime = 0
DeadCount = 0
#*********************************** class ************************************#
class Car():
    def __init__(self,id_, from_, to_, speed_, planTime_,priority_,preset_):
        # **** statistic param **** #
        self.id_, self.from_, self.to_, self.speed_, self.planTime_,self.priority_,self.preset_ = \
            id_, from_, to_, speed_, planTime_,priority_,preset_
        self.changable = False
        self.presetTime = None
        # **** dynamic param **** #
        self.state,self.nextRoadId = 0,None
        self.x, self.y = 0, 0
        self.presentRoadId,self.roadDirection = None,None
        # car route record
        self.route = []
        self.routeIndex = 1
        # **** copy **** #
        self.state_,self.nextRoadId_ = [0,0], [None,None]
        self.x_, self.y_ = [0,0], [0,0]
        self.presentRoadId_, self.roadDirection_ = [None,None],[None,None]
        self.routeIndex_ = [1,1]
        # **** stage copy **** #
        self.state_stage, self.nextRoadId_stage = [0 for i in range(4)], [None for i in range(4)]
        self.x_stage, self.y_stage = [0 for i in range(4)], [0 for i in range(4)]
        self.presentRoadId_stage, self.roadDirection_stage = [None for i in range(4)], [None for i in range(4)]
        self.routeIndex_stage = [1 for i in range(4)]
        self.route_stage = [[] for i in range(4)]
    # archive and load
    def archive(self,index):
        self.state_[index],self.nextRoadId_[index], self.x_[index],self.y_[index],self.presentRoadId_[index],\
        self.roadDirection_[index],self.routeIndex_[index] = \
            self.state, self.nextRoadId, self.x, self.y, self.presentRoadId, self.roadDirection,self.routeIndex
    def load(self,index):
        self.state, self.nextRoadId, self.x, self.y, self.presentRoadId, self.roadDirection,self.routeIndex = \
        self.state_[index], self.nextRoadId_[index], self.x_[index], self.y_[index], self.presentRoadId_[index],\
        self.roadDirection_[index],self.routeIndex_[index]
    #
    def stage_archive(self,stage):
        self.state_stage[stage], self.nextRoadId_stage[stage], self.x_stage[stage], self.y_stage[stage], self.presentRoadId_stage[stage], \
        self.roadDirection_stage[stage], self.routeIndex_stage[stage],self.route_stage[stage] = \
            self.state, self.nextRoadId, self.x, self.y, self.presentRoadId, self.roadDirection, self.routeIndex,self.route.copy()
    def stage_load(self,stage):
        self.state, self.nextRoadId, self.x, self.y, self.presentRoadId, self.roadDirection, self.routeIndex,self.route = \
            self.state_stage[stage], self.nextRoadId_stage[stage], self.x_stage[stage], self.y_stage[stage], self.presentRoadId_stage[stage], \
            self.roadDirection_stage[stage], self.routeIndex_stage[stage], self.route_stage[stage].copy()
    # states update
    def stepInit(self):
        self.state = 1
    def update(self, state, x=None, y=None, presentRoadId=None, roadDirection=None):
        global Time
        if self.state != 0 or presentRoadId is not None:
            self.state = state
        self.x = x if x is not None else self.x
        self.y = y if y is not None else self.y
        if presentRoadId is not None:
            self.nextRoadId = None
            # update route
            if self.preset_ == 0 or self.changable:
                if self.presentRoadId is None:
                    if self.changable:
                        self.route = [self.presetTime]
                    else:
                        self.route = [Time]
                    self.route.append(presentRoadId)
                    self.routeIndex = 2
                else:
                    try:
                        self.route[self.routeIndex] = presentRoadId
                    except:
                        self.route.append(presentRoadId)
                    self.routeIndex += 1
        self.presentRoadId = presentRoadId if presentRoadId is not None else self.presentRoadId
        self.roadDirection = roadDirection if roadDirection is not None else self.roadDirection
    # route
    def setChangable(self):
        self.changable = True
    def loadRoute(self,data):
        assert data[0] >= self.planTime_,print(self.id_,'ATD earlier than planTime')
        self.presetTime = data[0]
        self.route = data[1:]
    def next(self):
        global TheGraph
        # if next road confirmed
        if self.nextRoadId is not None:
            return self.nextRoadId
        # if preset
        if self.preset_ == 1 and self.changable == False:
            if self.routeIndex < self.route.__len__():
                self.nextRoadId = self.route[self.routeIndex]
                self.routeIndex += 1
                return self.nextRoadId
            else:
                return None
        # if not preset
        if self.presentRoadId is None:          # in the carport
            return TheGraph.next(self.id_)
        else:                                   # on the road
            self.nextRoadId = TheGraph.next(self.id_)
            return self.nextRoadId
    def start(self):
        global Time
        self.self.route = [Time,self.nextRoadId]
        self.routeIndex = 2
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
        return self.planTime_
    def __color__(self):
        return self.carColor
    def isPriority(self):
        return self.priority_
    def isPreset(self):
        return self.preset_
    def isChangable(self):
        return self.changable
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
    def __route__(self):
        return self.route

class channelQueue():
    def __init__(self,id_,y,size,speed):
        self.id_ = id_
        self.y = y
        self.channel = [None]*(size+1)
        self.size = size+1
        self.speed = speed
        self.frontIndex = 0
        self.backIndex = 0
        # archive and load
        self.list_ = [[None for i in range(size+1)], [None for i in range(size+1)]]
        self.list_Length = [0,0]
        # stage archive and load
        self.list_stage = [[None for i in range(size + 1)] for i in range(4)]
        self.list_Length_stage = [0 for i in range(4)]
        self.nextIndex = 0
    # archive and load
    def archive(self,index):
        if self.frontIndex > self.backIndex:
            back = self.size
            self.list_Length[index] = self.backIndex +self.size-self.frontIndex
        else:
            self.list_Length[index] = self.backIndex - self.frontIndex
            back = self.backIndex
        for i in range(self.frontIndex,back):
            self.list_[index][i-self.frontIndex] = self.channel[i]
        if self.frontIndex > self.backIndex:
            for i in range(self.backIndex):
                self.list_[index][back-self.frontIndex+i] = self.channel[i]
    def load(self,index):
        self.frontIndex,self.backIndex = 0,self.list_Length[index]
        for i in range(self.list_Length[index]):
            self.channel[i] = self.list_[index][i]
    # stage archive and load
    def stage_archive(self,stage):
        if self.frontIndex > self.backIndex:
            back = self.size
            self.list_Length_stage[stage] = self.backIndex +self.size-self.frontIndex
        else:
            self.list_Length_stage[stage] = self.backIndex - self.frontIndex
            back = self.backIndex
        for i in range(self.frontIndex,back):
            self.list_stage[stage][i-self.frontIndex] = self.channel[i]
        if self.frontIndex > self.backIndex:
            for i in range(self.backIndex):
                self.list_stage[stage][back-self.frontIndex+i] = self.channel[i]
    def stage_load(self,stage):
        self.frontIndex, self.backIndex = 0, self.list_Length_stage[stage]
        for i in range(self.list_Length_stage[stage]):
            self.channel[i] = self.list_stage[stage][i]
    # queue functions
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
            print(self.id_,self.channel,self.frontIndex,self.backIndex)
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
    # stepInit
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
        for i in range(self.frontIndex, back):
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

class Road():
    def __init__(self,id_, length_, speed_, channel_,from_,to_,direction):
        # **** statistic param **** #
        self.id_, self.length_, self.speed_, self.channel_, self.from_,self.to_,self.direction = \
            id_, length_, speed_, channel_, from_, to_, direction
        self.carCapcity = self.length_ * self.channel_
        self.carFlow = self.speed_ * self.channel_
        if speed_ <= 8:
            self.roadColor = [0, 0, 0]
        elif speed_<12:
            self.roadColor = [255, 0, 0]
        else:
            self.roadColor = [0, 255, 0]
        # **** dynamic param **** #
        self.queues = [channelQueue(id_,i,length_,speed_) for i in range(self.channel_)]
        self.carNum = 0
        # **** copy **** #
        self.carNum_ = [0,0]
        # **** stage archive and load **** #
        self.carNum_stage = [0 for i in range(4)]
        # **** step param ****#
        self.firstPriorityCarChannel = 0
        self.channelFirstPriorityCar = [None] * self.channel_
        self.full = False
    # archive load
    def archive(self,index):
        self.carNum_[index] = self.carNum
        for y in range(self.channel_):
            self.queues[y].archive(index)
    def load(self,index):
        self.carNum = self.carNum_[index]
        for y in range(self.channel_):
            self.queues[y].load(index)
    def stage_archive(self,stage):
        self.carNum_stage[stage] = self.carNum
        for y in range(self.channel_):
            self.queues[y].stage_archive(stage)
    def stage_load(self,stage):
        self.carNum = self.carNum_stage[stage]
        for y in range(self.channel_):
            self.queues[y].stage_load(stage)
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
        if action==0 or action == 1:
            TheCarport.outOfCarport(self.id_,self.direction)
    def receiveCar(self, carId):
        global CarList
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
                car.update(state=2, x=self.length_-leftX, y=y, presentRoadId=self.id_, roadDirection=self.direction)
                self.carNum+=1
                return 0
            if CarList[backCarId].__state__() == 1:
                return 2
            if CarList[backCarId].__x__()!=self.length_-1:
                self.queues[y].put(carId)
                car.update(state=2, x=CarList[backCarId].__x__()+1, y=y, presentRoadId=self.id_, roadDirection=self.direction)
                self.carNum+=1
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
    def __carFlow__(self):
        return self.carFlow
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
    # **** road condition ****#
    def __congestion__(self):
        return self.carNum/self.carCapcity

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
        self.provider,self.receiver,self.receiverDirection = [],[],{}
        for roadId in self.roadIds:
            if roadId == -1:
                continue
            direction = CrossRoadDirection[id_][roadId]
            if RoadList[roadId][direction] is not None:
                self.receiver.append(RoadList[roadId][direction])
                self.receiverDirection[roadId] = direction
            if RoadList[roadId][(direction+1)%2] is not None:
                self.provider.append(RoadList[roadId][(direction+1)%2])
        # **** dynamic param **** #
        self.finishCarNum = 0
        # **** copy **** #
        self.finishCarNum_ = [0,0]
        # **** stage archive **** #
        self.finishCarNum_stage = [0 for i in range(4)]
        # **** step param **** #
        self.update = False
        self.done = False
    # archive and load
    def archive(self,index):
        self.finishCarNum_[index] = self.finishCarNum
    def load(self,index):
        self.finishCarNum = self.finishCarNum_[index]
    # stage archive and load
    def stage_archive(self,stage):
        self.finishCarNum_stage[stage] = self.finishCarNum
    def stage_load(self,stage):
        self.finishCarNum = self.finishCarNum_stage[stage]
    #
    def roadIdsInit(self,roadIds):
        self.roadIds = roadIds
    def stepInit(self):
        self.done = False
    def step(self):
        global CarList, RoadList, CrossList, TheCarport, CarDistribution, PriorCarDistribution,CarSpeedDistribution
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
                    self.provider[presentRoadIndex].firstPriorityCarAct(0)
                    CarList[nextCarId[presentRoadIndex]].update(state=3)
                    CarSpeedDistribution[CarList[nextCarId[presentRoadIndex]].__speed__()] -=1
                    if CarList[nextCarId[presentRoadIndex]].isPriority()==1:
                        PriorCarDistribution[1] -= 1
                        PriorCarDistribution[2] += 1
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
        fromDirectionA ,fromDirectionB = self.roadDirection[fromRoadIdA],self.roadDirection[fromRoadIdB]
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
    # **** statistic param **** #
    def __id__(self):
        return self.id_
    def __roadIds__(self):
        return self.roadIds
    def __roadDirection__(self):
        return self.roadDirection
    def __directionMap__(self):
        return self.directionMap
    def __provider__(self):
        return self.provider
    def __receiver__(self):
        return self.receiver
    def __receiverDirection__(self):
        return self.receiverDirection
    # **** dynamic param **** #
    def __finishCarNum__(self):
        return self.finishCarNum
    # **** step param **** #
    def __update__(self):
        return self.update
    def __done__(self):
        return self.done
    # **** useful **** #
    def __congestion__(self):
        carNum,carCapcity= 0,0
        for receiver in self.receiver:
            carNum += receiver.__carNum__()
            carCapcity += receiver.__carCapcity__()
        for provider in self.provider:
            carNum += provider.__carNum__()
            carCapcity += provider.__carCapcity__()
        assert carCapcity!=0,print("carCapcity should not be 0")
        return carNum/(carCapcity+1e-5)

class Carport():
    def __init__(self):
        global RoadList, CrossList, CarList
        self.readyCarNum = 0
        self.readyCarNumSave = [0,0]
        self.readyCarNum_stage = [0 for i in range(4)]
        self.setRoute = [0] * CarList.__len__()
        # in
        # preset
        self.priorCar = [[[], []] for i in range(RoadList.__len__())]
        self.car = [[[], []] for i in range(RoadList.__len__())]
        # not preset
        self.freePriorCar = [[] for i in range(CrossList.__len__())]
        self.freeCar = [[] for i in range(CrossList.__len__())]
        # preset index
        self.priorCarIndex = [[0,0] for i in range(RoadList.__len__())]
        self.carIndex = [[0,0] for i in range(RoadList.__len__())]
        # not preset index
        self.freePriorCarIndex = [0 for i in range(RoadList.__len__())]
        self.freeCarIndex = [0 for i in range(RoadList.__len__())]
        # time ready
        self.priorTimeReady = [[] for i in range(CrossList.__len__())]
        self.timeReady = [[] for i in range(CrossList.__len__())]
        # ready
        self.priorReadyCar = [[[], []] for i in range(RoadList.__len__())]
        self.readyCar = [[[], []] for i in range(RoadList.__len__())]
        # copy
        self.freePriorCarIndexSave, self.freeCarIndexSave, self.priorReadyCarSave, self.readyCarSave,self.priorCarIndexSave,\
        self.carIndexSave = [None, None], [None, None], [None, None], [None, None], [None, None], [None, None]
        self.priorTimeReadySave , self.timeReadySave = [None, None], [None, None]
        # stage copy
        self.freePriorCarIndex_stage, self.freeCarIndex_stage, self.priorReadyCar_stage, \
        self.readyCar_stage, self.priorCarIndex_stage, self.carIndex_stage = [None for i in range(4)], \
        [None for i in range(4)], [None for i in range(4)], [None for i in range(4)], [None for i in range(4)], \
        [None for i in range(4)]
        self.priorTimeReady_stage, self.timeReady_stage = [None for i in range(4)], [None for i in range(4)]
        # data
        self.carportCarNum = [0 for i in range(CrossList.__len__())]
        self.carportCarNumSave = [[0 for i in range(CrossList.__len__())],[0 for i in range(CrossList.__len__())]]
        self.carportCarNum_stage = [[0 for i in range(CrossList.__len__())] for j in range(4)]
        self.vipCarNum = [0 for i in range(CrossList.__len__())]
        self.vipCarNumSave = [[0 for i in range(CrossList.__len__())],[0 for i in range(CrossList.__len__())]]
        self.vipCarNum_stage = [[0 for i in range(CrossList.__len__())] for j in range(4)]
    def archive(self,index):
        global RoadList, CrossList
        # preset
        self.priorCarIndexSave[index] = [[0, 0] for i in range(RoadList.__len__())]
        self.carIndexSave[index] = [[0, 0] for i in range(RoadList.__len__())]
        self.priorReadyCarSave[index] = [[[], []] for i in range(RoadList.__len__())]
        self.readyCarSave[index] = [[[], []] for i in range(RoadList.__len__())]
        # list
        self.freePriorCarIndexSave[index] = [0 for i in range(CrossList.__len__())]
        self.freeCarIndexSave[index] = [0 for i in range(CrossList.__len__())]
        self.priorTimeReadySave[index] = [[] for i in range(CrossList.__len__())]
        self.timeReadySave[index] = [[] for i in range(CrossList.__len__())]
        for i in range(RoadList.__len__()):
            self.priorReadyCarSave[index][i][0], self.priorReadyCarSave[index][i][1] = \
                self.priorReadyCar[i][0].copy(), self.priorReadyCar[i][1].copy()
            self.readyCarSave[index][i][0], self.readyCarSave[index][i][1] = \
                self.readyCar[i][0].copy(), self.readyCar[i][1].copy()
            self.priorCarIndexSave[index][i][0],self.priorCarIndexSave[index][i][1] = \
                self.priorCarIndex[i][0],self.priorCarIndex[i][1]
            self.carIndexSave[index][i][0],self.carIndexSave[index][i][1] = \
                self.carIndex[i][0],self.carIndex[i][1]
        for i in range(CrossList.__len__()):
            self.freePriorCarIndexSave[index][i] = self.freePriorCarIndex[i]
            self.freeCarIndexSave[index][i] = self.freeCarIndex[i]
            self.priorTimeReadySave[index][i] = self.priorTimeReady[i].copy()
            self.timeReadySave[index][i] = self.timeReady[i].copy()
        self.carportCarNumSave[index] = self.carportCarNum.copy()
        self.vipCarNumSave[index] = self.vipCarNum.copy()
        self.readyCarNumSave[index] = self.readyCarNum
    def load(self,index):
        global RoadList, CrossList
        self.priorCarIndex = [[0, 0] for i in range(RoadList.__len__())]
        self.carIndex = [[0, 0] for i in range(RoadList.__len__())]
        self.freePriorCarIndex = [0 for i in range(CrossList.__len__())]
        self.freeCarIndex = [0 for i in range(CrossList.__len__())]
        self.priorReadyCar = [[[], []] for i in range(RoadList.__len__())]
        self.readyCar = [[[], []] for i in range(RoadList.__len__())]
        self.priorTimeReady = [[] for i in range(CrossList.__len__())]
        self.timeReady = [[] for i in range(CrossList.__len__())]
        for i in range(RoadList.__len__()):
            self.priorReadyCar[i][0], self.priorReadyCar[i][1] = \
                self.priorReadyCarSave[index][i][0].copy(), self.priorReadyCarSave[index][i][1].copy()
            self.readyCar[i][0], self.readyCar[i][1] = \
                self.readyCarSave[index][i][0].copy(), self.readyCarSave[index][i][1].copy()
            self.priorCarIndex[i][0],self.priorCarIndex[i][1] = \
                self.priorCarIndexSave[index][i][0],self.priorCarIndexSave[index][i][1]
            self.carIndex[i][0],self.carIndex[i][1] = \
                self.carIndexSave[index][i][0],self.carIndexSave[index][i][1]
        for i in range(CrossList.__len__()):
            self.freePriorCarIndex[i] = self.freePriorCarIndexSave[index][i]
            self.freeCarIndex[i] = self.freeCarIndexSave[index][i]
            self.priorTimeReady[i] = self.priorTimeReadySave[index][i].copy()
            self.timeReady[i] = self.timeReadySave[index][i].copy()
        self.carportCarNum = self.carportCarNumSave[index].copy()
        self.vipCarNum = self.vipCarNumSave[index].copy()
        self.readyCarNum = self.readyCarNumSave[index]
    def stage_archive(self,stage):
        global RoadList, CrossList
        # preset
        self.priorCarIndex_stage[stage] = [[0, 0] for i in range(RoadList.__len__())]
        self.carIndex_stage[stage] = [[0, 0] for i in range(RoadList.__len__())]
        self.priorReadyCar_stage[stage] = [[[], []] for i in range(RoadList.__len__())]
        self.readyCar_stage[stage] = [[[], []] for i in range(RoadList.__len__())]
        # list
        self.freePriorCarIndex_stage[stage] = [0 for i in range(CrossList.__len__())]
        self.freeCarIndex_stage[stage] = [0 for i in range(CrossList.__len__())]
        self.priorTimeReady_stage[stage] = [[] for i in range(CrossList.__len__())]
        self.timeReady_stage[stage] = [[] for i in range(CrossList.__len__())]
        for i in range(RoadList.__len__()):
            self.priorReadyCar_stage[stage][i][0], self.priorReadyCar_stage[stage][i][1] = \
                self.priorReadyCar[i][0].copy(), self.priorReadyCar[i][1].copy()
            self.readyCar_stage[stage][i][0], self.readyCar_stage[stage][i][1] = \
                self.readyCar[i][0].copy(), self.readyCar[i][1].copy()
            self.priorCarIndex_stage[stage][i][0], self.priorCarIndex_stage[stage][i][1] = \
                self.priorCarIndex[i][0], self.priorCarIndex[i][1]
            self.carIndex_stage[stage][i][0], self.carIndex_stage[stage][i][1] = \
                self.carIndex[i][0], self.carIndex[i][1]
        for i in range(CrossList.__len__()):
            self.freePriorCarIndex_stage[stage][i] = self.freePriorCarIndex[i]
            self.freeCarIndex_stage[stage][i] = self.freeCarIndex[i]
            self.priorTimeReady_stage[stage][i] = self.priorTimeReady[i].copy()
            self.timeReady_stage[stage][i] = self.timeReady[i].copy()
        self.carportCarNum_stage[stage] = self.carportCarNum.copy()
        self.vipCarNum_stage[stage] = self.vipCarNum.copy()
        self.readyCarNum_stage[stage] = self.readyCarNum
    def stage_load(self,stage):
        global RoadList, CrossList
        self.priorCarIndex = [[0, 0] for i in range(RoadList.__len__())]
        self.carIndex = [[0, 0] for i in range(RoadList.__len__())]
        self.freePriorCarIndex = [0 for i in range(CrossList.__len__())]
        self.freeCarIndex = [0 for i in range(CrossList.__len__())]
        self.priorReadyCar = [[[], []] for i in range(RoadList.__len__())]
        self.readyCar = [[[], []] for i in range(RoadList.__len__())]
        self.priorTimeReady = [[] for i in range(CrossList.__len__())]
        self.timeReady = [[] for i in range(CrossList.__len__())]
        for i in range(RoadList.__len__()):
            self.priorReadyCar[i][0], self.priorReadyCar[i][1] = \
                self.priorReadyCar_stage[stage][i][0].copy(), self.priorReadyCar_stage[stage][i][1].copy()
            self.readyCar[i][0], self.readyCar[i][1] = \
                self.readyCar_stage[stage][i][0].copy(), self.readyCar_stage[stage][i][1].copy()
            self.priorCarIndex[i][0], self.priorCarIndex[i][1] = \
                self.priorCarIndex_stage[stage][i][0], self.priorCarIndex_stage[stage][i][1]
            self.carIndex[i][0], self.carIndex[i][1] = \
                self.carIndex_stage[stage][i][0], self.carIndex_stage[stage][i][1]
        for i in range(CrossList.__len__()):
            self.freePriorCarIndex[i] = self.freePriorCarIndex_stage[stage][i]
            self.freeCarIndex[i] = self.freeCarIndex_stage[stage][i]
            self.priorTimeReady[i] = self.priorTimeReady_stage[stage][i].copy()
            self.timeReady[i] = self.timeReady_stage[stage][i].copy()
        self.carportCarNum = self.carportCarNum_stage[stage].copy()
        self.vipCarNum = self.vipCarNum_stage[stage].copy()
        self.readyCarNum = self.readyCarNum_stage[stage]
    def carportInit(self, carId, time, roadId=None,runTime=None):
        global CarList, CrossRoadDirection
        if self.setRoute[carId] >= 1:
            self.setRoute[carId] += 1
            return
        else:
            self.setRoute[carId] = 1
        if roadId is not None:
            if CarList[carId].isPriority() == 1:
                self.vipCarNum[CarList[carId].__from__()] += 1
            self.carportCarNum[CarList[carId].__from__()] += 1
            direction = CrossRoadDirection[CarList[carId].__from__()][roadId]
            if CarList[carId].isPriority() == 1:
                self.priorCar[roadId][direction].append([time, carId])
            else:
                self.car[roadId][direction].append([time, carId])
        else:
            if CarList[carId].isPriority() == 1:
                self.vipCarNum[CarList[carId].__from__()] += 1
            self.carportCarNum[CarList[carId].__from__()] += 1
            if CarList[carId].isPriority() == 1:
                self.freePriorCar[CarList[carId].__from__()].append([time, runTime, carId])
            else:
                self.freeCar[CarList[carId].__from__()].append([time, runTime, carId])
    def simulateInit(self):
        global RoadList, CrossList
        for i in range(RoadList.__len__()):
            self.priorCar[i][0].sort()
            self.car[i][0].sort()
            if RoadList[i][1] is not None:
                self.priorCar[i][1].sort()
                self.car[i][1].sort()
        for i in range(CrossList.__len__()):
            self.freePriorCar[i].sort()
            self.freeCar[i].sort()
        self.archive(0)
        self.archive(1)
    def stepInit(self):
        global CarList, RoadList,CrossList,CrossRoadDirection,Time
        global TheGraph, _PriorMore
        # postpone free car time in readyCar
        # add preset ready car
        for i in range(RoadList.__len__()):
            # postpone free car time
            for j in range(self.readyCar[i][0].__len__()):
                if CarList[self.readyCar[i][0][j][1]].isPreset() == 0:
                    self.readyCar[i][0][j][0] = Time
            for j in range(self.readyCar[i][1].__len__()):
                if CarList[self.readyCar[i][1][j][1]].isPreset() == 0:
                    self.readyCar[i][1][j][0] = Time
            for j in range(self.priorReadyCar[i][0].__len__()):
                if CarList[self.priorReadyCar[i][0][j][1]].isPreset() == 0:
                    self.priorReadyCar[i][0][j][0] = Time
            for j in range(self.priorReadyCar[i][1].__len__()):
                if CarList[self.priorReadyCar[i][1][j][1]].isPreset() == 0:
                    self.priorReadyCar[i][1][j][0] = Time
            # add preset ready car
            isBreak = False
            for j in range(self.priorCarIndex[i][0],self.priorCar[i][0].__len__()):
                if self.priorCar[i][0][j][0] <= Time:
                    self.readyCarNum += 1
                    carId = self.priorCar[i][0][j][1]
                    if CarList[carId].isChangable():
                        roadId = TheGraph.next(carId)
                        direction = CrossRoadDirection[CarList[carId].__from__()][roadId]
                        self.priorReadyCar[roadId][direction].append(self.priorCar[i][0][j])
                    else:
                        self.priorReadyCar[i][0].append(self.priorCar[i][0][j])
                else:
                    isBreak = True
                    break
            self.priorCarIndex[i][0] = j if isBreak else self.priorCar[i][0].__len__()
            isBreak = False
            for j in range(self.priorCarIndex[i][1], self.priorCar[i][1].__len__()):
                if self.priorCar[i][1][j][0] <= Time:
                    self.readyCarNum += 1
                    carId = self.priorCar[i][1][j][1]
                    if CarList[carId].isChangable():
                        roadId = TheGraph.next(carId)
                        direction = CrossRoadDirection[CarList[carId].__from__()][roadId]
                        self.priorReadyCar[roadId][direction].append(self.priorCar[i][1][j])
                    else:
                        self.priorReadyCar[i][1].append(self.priorCar[i][1][j])
                else:
                    isBreak = True
                    break
            self.priorCarIndex[i][1] = j if isBreak else self.priorCar[i][1].__len__()
            isBreak = False
            for j in range(self.carIndex[i][0],self.car[i][0].__len__()):
                if self.car[i][0][j][0]<=Time:
                    self.readyCarNum += 1
                    self.readyCar[i][0].append(self.car[i][0][j])
                else:
                    isBreak = True
                    break
            self.carIndex[i][0] = j if isBreak else self.car[i][0].__len__()
            isBreak = False
            for j in range(self.carIndex[i][1],self.car[i][1].__len__()):
                if self.car[i][1][j][0]<=Time:
                    self.readyCarNum += 1
                    self.readyCar[i][1].append(self.car[i][1][j])
                else:
                    isBreak = True
                    break
            self.carIndex[i][1] = j if isBreak else self.car[i][1].__len__()
        # time ready car
        for crossId in range(CrossList.__len__()):
            isBreak = False
            for i in range(self.freeCarIndex[crossId],self.freeCar[crossId].__len__()):
                if Time >= self.freeCar[crossId][i][0]:
                    heapq.heappush(self.timeReady[crossId],self.freeCar[crossId][i][1:])
                else:
                    isBreak = True
                    break
            self.freeCarIndex[crossId] = i if isBreak else self.freeCar[crossId].__len__()
            isBreak = False
            for i in range(self.freePriorCarIndex[crossId],self.freePriorCar[crossId].__len__()):
                if Time >= self.freePriorCar[crossId][i][0]:
                    heapq.heappush(self.priorTimeReady[crossId],self.freePriorCar[crossId][i][1:])
                else:
                    isBreak = True
                    break
            self.freePriorCarIndex[crossId] = i if isBreak else self.freePriorCar[crossId].__len__()
        # add  free ready car
        # full first
        carportCarNum = []
        for i in range(CrossList.__len__()):
            carportCarNum.append([-self.carportCarNum[i],i])
        carportCarNum.sort()
        for congestion,crossId in carportCarNum:
            #prior
            while self.priorTimeReady[crossId].__len__() > 0:
                if CarDistribution[1] + self.readyCarNum > _MaxCarNum + _PriorMore:
                    break
                runTime, carId = heapq.heappop(self.priorTimeReady[crossId])
                roadId = TheGraph.next(carId)
                direction = CrossRoadDirection[crossId][roadId]
                actualRoadCarNum = RoadList[roadId][direction].__carNum__() + \
                                   self.priorReadyCar[roadId][direction].__len__() + self.readyCar[roadId][
                                       direction].__len__()
                if actualRoadCarNum > _priorFactor * RoadList[roadId][direction].__carCapcity__():
                    heapq.heappush(self.priorTimeReady[crossId],[runTime, carId])
                    break
                self.priorReadyCar[roadId][direction].append([Time, carId])
                self.readyCarNum += 1
            # norm
            while self.timeReady[crossId].__len__() > 0:
                if CarDistribution[1] + self.readyCarNum > _MaxCarNum:
                    break
                runTime, carId = heapq.heappop(self.timeReady[crossId])
                roadId = TheGraph.next(carId)
                direction = CrossRoadDirection[crossId][roadId]
                actualRoadCarNum = RoadList[roadId][direction].__carNum__()+\
                        self.priorReadyCar[roadId][direction].__len__()+self.readyCar[roadId][direction].__len__()
                if actualRoadCarNum > factor*RoadList[roadId][direction].__carCapcity__():
                    heapq.heappush(self.timeReady[crossId], [runTime, carId])
                    break
                self.readyCar[roadId][direction].append([Time, carId])
                self.readyCarNum += 1
        # sort
        for i in range(RoadList.__len__()):
            self.readyCar[i][0].sort()
            self.readyCar[i][1].sort()
            self.priorReadyCar[i][0].sort()
            self.priorReadyCar[i][1].sort()
    def outOfCarport(self, roadId, direction, all=False):
        global Time, RoadList, CarDistribution, PriorCarDistribution, PriorStTime
        road = RoadList[roadId][direction]
        if road.__full__():
            return
        temp = []
        for i in range(self.priorReadyCar[roadId][direction].__len__()):
            time, carId = self.priorReadyCar[roadId][direction][i]
            if time > Time:
                temp.extend(self.priorReadyCar[roadId][direction][i:])
                break
            else:
                action = road.receiveCar(carId)
                if action != 0:
                    temp.append(self.priorReadyCar[roadId][direction][i])
                    continue
                self.vipCarNum[CarList[carId].__from__()] -= 1
                self.carportCarNum[CarList[carId].__from__()] -= 1
                self.readyCarNum -= 1
                # prior car start time
                if PriorStTime == -1:
                    PriorStTime = time
                PriorCarDistribution[0] -= 1
                PriorCarDistribution[1] += 1
                CarDistribution[0] -= 1
                CarDistribution[1] += 1
        self.priorReadyCar[roadId][direction] = temp
        if all:
            temp = []
            for i in range(self.readyCar[roadId][direction].__len__()):
                time, carId = self.readyCar[roadId][direction][i]
                if time > Time:
                    temp.extend(self.readyCar[roadId][direction][i:])
                    break
                else:
                    action = road.receiveCar(carId)
                    if action != 0:
                        temp.append(self.readyCar[roadId][direction][i])
                        continue
                    self.carportCarNum[CarList[carId].__from__()] -= 1
                    self.readyCarNum -= 1
                    CarDistribution[0] -= 1
                    CarDistribution[1] += 1
            self.readyCar[roadId][direction] = temp
    def __carportCarNum__(self,crossId):
        return self.carportCarNum[crossId]
    def __vipCarNum__(self,crossId):
        return self.vipCarNum[crossId]
    def __readyCarNum__(self):
        return self.readyCarNum

class Graph():
    def __init__(self):
        # cross
        self.maxX, self.maxY = None, None
        self.crossLoc = None
        self.locCross = None
        #
        self.carFlowRatio = None
        #
        self.routeMap = None
        self.routeWeight = None
        self.fullRouteMap = None
        self.matrix = None
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
        CrossList[presentCrossId].roadIdsInit(CrossInfo[presentCrossId][1:])
        for i, roadId in enumerate(CrossInfo[presentCrossId][1:]):
            if roadId != -1:
                nextCross = CrossRoadCross[presentCrossId][roadId]
                self.dfs(presentCrossId, nextCross, i % 4)
    # car flow
    def carFlowRatioGen(self):
        global RoadList,CrossList
        self.carFlowRatio = [[0,0] for i in range(RoadList.__len__())]
        for i in range(CrossList.__len__()):
            for roadP in CrossList[i].__provider__():
                flowOut = 0
                for roadR in CrossList[i].__receiver__():
                    flowOut += roadR.__carFlow__()
                self.carFlowRatio[roadP.__id__()][roadP.__direction__()] = 0.5+5*pow(roadP.__carFlow__()/flowOut-0.5,3)
    # routeMapUpdate
    def routeMapUpdate(self):
        global CrossList,TheStage
        self.routeMap,self.routeWeight = [],[]
        # far routeMap
        if TheStage ==3:
            self.distanceMatrixGen1()
        else:
            self.distanceMatrixGen()
        for crossSt in range(CrossList.__len__()):
            weight, crossPath = self.dijkstra(crossSt)
            self.routeWeight.append(weight)
            self.routeMap.append(crossPath)
    def distanceMatrixGen(self):
        global RoadList,CrossList,CrossRoadCross
        global TheCarport,CarDistribution
        global AvoidAlpha
        if self.matrix is None:
            self.matrix = {crossId: {} for crossId in range(CrossList.__len__())}
        for crossId in range(CrossList.__len__()):
            for road in CrossList[crossId].__receiver__():
                nextCrossId = CrossRoadCross[crossId][road.__id__()]
                congestion = road.__congestion__()
                carFlowRatio = self.carFlowRatio[road.__id__()][road.__direction__()]
                if PriorCarDistribution[0]<sum(PriorCarDistribution)/20:
                    vipHurryDegree = TheCarport.__vipCarNum__(crossId)/(PriorCarDistribution[0]+5)
                else:
                    vipHurryDegree = 0
                value = 20+pow(_routeMapPrarm[0] * congestion, 2) + _routeMapPrarm[1] * road.__length__() / road.__speed__() + \
                        _routeMapPrarm[2]*carFlowRatio + 500 * vipHurryDegree
                try:
                    self.matrix[crossId][nextCrossId] = self.matrix[crossId][nextCrossId] * _expSmoothRouteMap + \
                                                        value * (1-_expSmoothRouteMap)
                except:
                    self.matrix[crossId][nextCrossId] = value
    def distanceMatrixGen1(self):
        global RoadList,CrossList,CrossRoadCross
        global TheCarport,CarDistribution
        global AvoidAlpha
        if self.matrix is None:
            self.matrix = {crossId: {} for crossId in range(CrossList.__len__())}
        for crossId in range(CrossList.__len__()):
            for road in CrossList[crossId].__receiver__():
                nextCrossId = CrossRoadCross[crossId][road.__id__()]
                congestion = road.__congestion__()
                if CarDistribution[0]<sum(CarDistribution)/20:
                    hurryDegree = TheCarport.__carportCarNum__(crossId)/(CarDistribution[0]+1)
                else:
                    hurryDegree = 0
                value = 20+pow(_routeMapPrarm[0] * congestion, 2) + 500 * hurryDegree +\
                        _routeMapPrarm[1] * road.__length__() / road.__speed__()
                try:
                    self.matrix[crossId][nextCrossId] = self.matrix[crossId][nextCrossId] * _expSmoothRouteMap + \
                                                        value * (1-_expSmoothRouteMap)
                except:
                    self.matrix[crossId][nextCrossId] = value                    
    def dijkstra(self, start):
        pqueue = []
        heapq.heappush(pqueue, (0, start))
        seen = set()
        parent = {start: None}
        # init distance
        distance = {start: 0}
        for vertex in self.matrix:
            if vertex is not start:
                distance[vertex] = float("inf")
        while pqueue:
            dist, u = heapq.heappop(pqueue)  # pick the minist vertex from pqueue
            seen.add(u)
            nodes = self.matrix[u].keys()  # 列出u的邻接点
            for w in nodes:
                if w not in seen:
                    if dist + self.matrix[u][w] < distance[w]:
                        heapq.heappush(pqueue, (dist + self.matrix[u][w], w))
                        parent[w] = u
                        distance[w] = dist + self.matrix[u][w]
        path = {}
        for key in self.matrix:
            end = key
            while end != start:
                path[key] = end
                end = parent[end]
        return distance,path
    def fullRouteMapUpdate(self):
        self.fullRouteMap = [[[] for i in range(len(CrossList))] for j in range(len(CrossList))]
        for st in range(len(CrossList)):
            for end in range(len(CrossList)):
                _ = self.route2fullRoute(self.fullRouteMap, self.routeMap, st, end)
    def route2fullRoute(self,fullRouetMap,routeMap,st,end):
        global CrossCrossRoad, CrossRoadDirection
        if st == end or fullRouetMap[st][end] != []:
            return fullRouetMap[st][end]
        nextSt = routeMap[st][end]
        road = [[CrossCrossRoad[st][nextSt]]]
        road[0].append(CrossRoadDirection[st][road[0][0]])
        road.extend(self.route2fullRoute(fullRouetMap, routeMap, nextSt, end))
        fullRouetMap[st][end] = road
        return road
    def route(self,crossSt,crossEnd):
        return self.fullRouteMap[crossSt][crossEnd]
    # strategy
    def next(self,carId):
        global CarList,CrossList,RoadList,RoadDirectionCross,CrossCrossRoad
        global Avoid
        # if in carport
        if CarList[carId].__presentRoadId__() is None:
            fromCross = CarList[carId].__from__()
            nextCross = self.routeMap[fromCross][CarList[carId].__to__()]
            return CrossCrossRoad[fromCross][nextCross]
        # if next cross is terminal
        fromCross = RoadDirectionCross[CarList[carId].__presentRoadId__()][CarList[carId].__roadDirection__()]
        toCross = CarList[carId].__to__()
        if fromCross == toCross:
            return None
        if CrossCrossRoad[fromCross][self.routeMap[fromCross][toCross]] != CarList[carId].__presentRoadId__():
            # if near the terminal
            fromX, fromY = self.crossLoc[fromCross]
            toX, toY = self.crossLoc[toCross]
            absolute = abs(fromX - toX) + abs(fromY - toY)
            if absolute < 3:
                return CrossCrossRoad[fromCross][self.routeMap[fromCross][toCross]]
            # if road not in avoid
            roadId = CrossCrossRoad[fromCross][self.routeMap[fromCross][toCross]]
            direction = CrossRoadDirection[fromCross][roadId]
            if [roadId, direction] not in Avoid:
                return roadId
        # if road in avoid or turn around
        #roadId = CrossCrossRoad[fromCross][self.routeMap[fromCross][toCross]]
        validCross = []
        for road in CrossList[fromCross].__receiver__():
            if road.__id__() != CarList[carId].__presentRoadId__() and \
                    CrossRoadCross[fromCross][road.__id__()] != TheGraph.routeMap[fromCross][toCross]:
                validCross.append(CrossRoadCross[fromCross][road.__id__()])
        weight = 10000
        for crossId in validCross:
            if self.routeWeight[fromCross][crossId] + self.routeWeight[crossId][toCross] < weight:
                roadId = CrossCrossRoad[fromCross][crossId]
        return roadId
    def absolute(self,st,end):
        x,y = self.crossLoc[st]
        x_,y_ = self.crossLoc[end]
        return abs(x-x_)+abs(y-y_)

class simulation():
    def __init__(self,answer_path):
        global RoadList
        self.times = 0
        self.dead = False
        self.unfinishedCross=None
        self.deadCount = 0
        self.stageDead = 0
        self.TotalCapcity = 0
        for road in RoadList:
            for i in range(2):
                if road[i] is not None:
                    self.TotalCapcity += road[i].__carCapcity__()
        self.carNumP = [6,6,7.5,8.5]
        self.factors = [0.3,0.25,0.25,0.5]
        self.priorFactors = [0.4,0.7,0.7,0.7]
        self.add = 1600
        self.answer_path = answer_path
        self.best_score = 1000000
    def step(self):
        global CarList, RoadList, CrossList, TheCarport, TheGraph, Time
        global  CarDistribution,PriorCarDistribution,CarSpeedDistribution,_MaxCarNum
        # step1
        #print("step1")
        TheCarport.stepInit()
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
        print(Time,_MaxCarNum, TheCarport.__readyCarNum__(),CarDistribution,
              sum(CarDistribution), PriorCarDistribution, sum(PriorCarDistribution))
        print(CarSpeedDistribution)
    def simulate(self):
        global TheStage,TheRandom
        global Time, TheGraph, StageArchiveTime,StTime,PriorTime
        stageArchive(0)
        StageArchiveTime[0] = 0
        while True:
            TheStage = 0
            stageLoad(TheStage)
            while True:
                self.stageInit()
                while True:
                    Time += 1
                    self.routeMapUpdate()
                    self.archive()
                    self.step()
                    self.load()
                    self.parameterChange()
                    if PriorCarDistribution[2] == sum(PriorCarDistribution) and PriorTime == -1:
                        PriorTime = Time
                    # dead processing
                    if self.deadCount > 10:
                        if Time < StageArchiveTime[TheStage]+5:
                            self.stageDead += 2
                        else:
                            self.stageDead += 1
                        print('stageDead times:%d'%self.stageDead)
                        self.carNumP[TheStage] += 0.2
                        # stage dead(exception stage 0)
                        if self.stageDead == 4 and TheStage!=0:
                            # save zuo fei
                            StageArchiveTime[TheStage] = 10000
                            TheStage -= 1
                            self.stageDead = 0
                        stageLoad(TheStage)
                        self.deadCount = 0
                        break
                    # stage transition
                    if self.stageChangeCondition():
                        # if its last stage
                        if self.finish():
                            self.carNumP[TheStage] -= 0.5
                        else:
                            self.carNumP[TheStage] -= 0.5
                            TheStage += 1
                            stageArchive(TheStage)
                            StageArchiveTime[TheStage] = Time
                        self.deadCount = 0
                        self.stageDead = 0
                        break
                    # no better
                    if TheStage <3 and Time > StageArchiveTime[TheStage+1]:
                        if TheStage == 1:
                            self.carNumP[TheStage] += TheRandom.random(-5000, 3000) / 8000
                        else:
                            self.carNumP[TheStage] += TheRandom.random(-5000, 5000) / 10000
                        TheStage += 1
                        stageLoad(TheStage)
                        self.deadCount = 0
                        self.stageDead = 0
                        break
                    # deadLine
                    if(time.clock() - StTime>850):
                        break
                if (time.clock() - StTime > 850):
                    break
                if self.finish():
                    print("consume Time:%d"%(int(time.clock()-StTime)))
                    _ = getScore()
                    if _ < self.best_score:
                        self.best_score = _
                        self.output()
                    if self.times == 0:
                        for i in range(1,len(StageArchiveTime)):
                            StageArchiveTime[i] = 10000
                    self.times +=1
                    break
            if (time.clock() - StTime > 850):
                print(self.best_score)
                break
    #
    def routeMapUpdate(self):
        global Time, TheGraph
        if Time % _routeMapUpdateFrequency == 0:
            TheGraph.routeMapUpdate()
    def archive(self):
        global Time,Avoid,LoadTime
        global _MaxCarNum
        if Time % _archiveFrequency == 0:
            if self.dead:
                self.dead = False
            else:
                if Time > LoadTime:
                    Avoid = []
                    self.deadCount = 0
                archive()
                if _MaxCarNum > _MaxCarNumMax:
                    _MaxCarNum -= 200
                if _MaxCarNum < _MaxCarNumMin:
                    _MaxCarNum += 200
    def load(self):
        if self.dead:
            self.avoid()
            load()
            self.deadCount+=1
    def finish(self):
        global CarDistribution
        if CarDistribution[2] == sum(CarDistribution):
            return True
        else:
            return False
    # stage function
    def stageInit(self):
        global TheStage
        global _MaxCarNumMin,_MaxCarNumMax
        global factor,factorMax,factorOri,_priorFactor
        if self.times == 0:
            _MaxCarNumMax = int(self.TotalCapcity / (self.carNumP[TheStage]+2)) + self.add
        else:
            _MaxCarNumMax = int(self.TotalCapcity / self.carNumP[TheStage] ) + self.add
        _MaxCarNumMin = _MaxCarNumMax - 200
        factorOri = self.factors[TheStage]
        factor,factorMax = factorOri,factorOri+0.15
        _priorFactor = self.priorFactors[TheStage]
        print('TheStage:[%d]_MaxCarNum:[%d]'%(TheStage,_MaxCarNumMax))
    def stageChangeCondition(self):
        global TheStage, _MaxCarNum
        if TheStage == 0:
            return PriorCarDistribution[0] == 0
        elif TheStage == 1:
            return PriorCarDistribution[1] + PriorCarDistribution[0] ==0
        elif TheStage == 2:
            return CarDistribution[0] < CarDistribution[1]/2 or CarDistribution[1] < _MaxCarNum/2
        elif TheStage == 3:
            return self.finish()
    def parameterChange(self):
        global TheStage,factor,factorOri,factorMax,_priorFactor
        if TheStage == 0:
            if _MaxCarNum - CarDistribution[1] > 1000 and factor < factorMax:
                factor += 0.05
            if factor % 20 == 0:
                factor = factorOri
            if PriorCarDistribution[0] < 1000:
                _priorFactor = 0.7
            if PriorCarDistribution[0] < 300:
                _priorFactor = 0.8
            if PriorCarDistribution[0] < 100:
                _priorFactor = 1
        elif TheStage == 1:
            if _MaxCarNum - CarDistribution[1] > 1000 and factor < factorMax:
                factor += 0.05
            if factor % 20 == 0:
                factor = factorOri
        elif TheStage == 1:
            if _MaxCarNum - CarDistribution[1] > 1000 and factor < factorMax:
                factor += 0.05
            if factor % 20 == 0:
                factor = factorOri
        elif TheStage == 2:
            if _MaxCarNum - CarDistribution[1] > 1000 and factor < factorMax:
                factor += 0.05
            if Time % 20 == 0:
                factor = factorOri
    #
    def findDeadLockCircle(self):
        global CrossList
        self.deadLockCircle = []
        record = [False for i in range(CrossList.__len__())]
        randomStart = self.unfinishedCross[TheRandom.random(0,self.unfinishedCross.__len__())]
        self.DFS(randomStart,record)
        # 删除多余的部分
        for i in range(1,self.deadLockCircle.__len__()):
            if self.deadLockCircle[0] == self.deadLockCircle[i]:
                break
        self.deadLockCircle = self.deadLockCircle[:i+1]
    def DFS(self,crossId,record,presentId=None):
        global CrossList, CrossRoadCross
        # if visited
        if record[crossId]:
            self.deadLockCircle = [crossId]
            return True
        record[crossId] = True
        cross = CrossList[crossId]
        for road in cross.__receiver__():
            roadId = road.__id__()
            nextCrossId = CrossRoadCross[crossId][roadId]
            if presentId is not None and nextCrossId == presentId:
                continue
            elif nextCrossId in self.unfinishedCross and self.DFS(nextCrossId,record,crossId):
                self.deadLockCircle.append(crossId)
                return True
        return False
    def avoid(self):
        global Avoid,AvoidAlpha,CrossCrossRoad,RoadList,_MaxCarNum
        if Avoid.__len__()>10:
            Avoid=[]
        self.findDeadLockCircle()
        randomAvoid = TheRandom.random(0,self.deadLockCircle.__len__() - 1)
        roadId = CrossCrossRoad[self.deadLockCircle[randomAvoid]][self.deadLockCircle[randomAvoid+1]]
        if RoadList[roadId][0].firstPriorityCar() is not None:
            Avoid.append([roadId,0])
        if RoadList[roadId][1] is not None:
            if RoadList[roadId][1].firstPriorityCar() is not None:
                Avoid.append([roadId, 1])
        _MaxCarNum += TheRandom.random(-500,501)
    #
    def output(self):
        output = open(self.answer_path, 'w')
        for i in range(CarList.__len__()):
            if CarList[i].isPreset() == 0 or CarList[i].isChangable():
                string = '(' + str(CarInfo[i][0]) + ',' + str(CarList[i].route[0])
                for j in range(1, CarList[i].routeIndex):
                    roadId = CarList[i].route[j]
                    string += ','
                    string += str(RoadInfo[roadId][0])
                string += ')\n'
                output.writelines(string)
        output.close()

class myRandom():
    def __init__(self,seed):
        self.value = seed
        self.a = 16807
        self.m = pow(2,31) - 1
        self.b = 77
    def random(self,st,end,int=True):
        self.value = (self.value * self.a + self.b)%self.m
        if int:
            return self.value%(end-st) + st
        else:
            return (self.value%10000)/10000*(end-st)+st

#*********************************** def *************************************#
def archive():
    global CarList,RoadList,CrossList,TheCarport
    global TimeSave,CarDistributionSave,PriorCarDistributionSave,PriorStTimeSave,PriorTimeSave
    global Time, CarDistribution, PriorCarDistribution, PriorStTime, PriorTime
    global CarSpeedDistribution,CarSpeedDistributionSave
    global ArchiveIndex
    index = ArchiveIndex
    for i in range(CarList.__len__()):
        CarList[i].archive(index)
    for i in range(RoadList.__len__()):
        RoadList[i][0].archive(index)
        if RoadList[i][1] is not None:
            RoadList[i][1].archive(index)
    for i in range(CrossList.__len__()):
        CrossList[i].archive(index)
    TheCarport.archive(index)
    TimeSave[index],CarDistributionSave[index],PriorCarDistributionSave[index],PriorStTimeSave[index],PriorTimeSave[index] = \
        Time, CarDistribution.copy(), PriorCarDistribution.copy(), PriorStTime, PriorTime
    CarSpeedDistributionSave[index] = CarSpeedDistribution.copy()
    ArchiveIndex = (ArchiveIndex+1)%2

def load():
    print("loading")
    global CarList, RoadList, CrossList, TheCarport,PriorStTime, PriorTime
    global TimeSave, CarDistributionSave, PriorCarDistributionSave, PriorStTimeSave, PriorTimeSave
    global Time, CarDistribution, PriorCarDistribution,CarSpeedDistribution,CarSpeedDistributionSave
    global ArchiveIndex,LoadIndex,LoadTime
    if Time > LoadTime:
        LoadTime = Time
        LoadIndex = ArchiveIndex
        ArchiveIndex = (LoadIndex + 1) % 2
    else:
        ArchiveIndex = (LoadIndex + 1) % 2
    index = LoadIndex
    for i in range(CarList.__len__()):
        CarList[i].load(index)
    for i in range(RoadList.__len__()):
        RoadList[i][0].load(index)
        if RoadList[i][1] is not None:
            RoadList[i][1].load(index)
    for i in range(CrossList.__len__()):
        CrossList[i].load(index)
    TheCarport.load(index)
    Time, CarDistribution, PriorCarDistribution, PriorStTime, PriorTime = \
        TimeSave[index], CarDistributionSave[index].copy(), PriorCarDistributionSave[index].copy(), \
        PriorStTimeSave[index], PriorTimeSave[index]
    CarSpeedDistribution = CarSpeedDistributionSave[index].copy()
    Time -= 1
    print("load done")
    print(Time, CarDistribution, sum(CarDistribution), PriorCarDistribution, sum(PriorCarDistribution))

def stageArchive(stage):
    global CarList, RoadList, CrossList, TheCarport
    global Time_Stage, CarDistribution_Stage, PriorCarDistribution_Stage, PriorStTime_Stage, PriorTime_Stage
    global Time, CarDistribution, PriorCarDistribution, PriorStTime, PriorTime
    global CarSpeedDistribution, CarSpeedDistribution_Stage
    print('Time:[%d] stage_archive'%(Time+1))
    Time += 1
    for i in range(CarList.__len__()):
        CarList[i].stage_archive(stage)
    for i in range(RoadList.__len__()):
        RoadList[i][0].stage_archive(stage)
        if RoadList[i][1] is not None:
            RoadList[i][1].stage_archive(stage)
    for i in range(CrossList.__len__()):
        CrossList[i].stage_archive(stage)
    TheCarport.stage_archive(stage)
    Time_Stage[stage],CarDistribution_Stage[stage],PriorCarDistribution_Stage[stage],PriorStTime_Stage[stage]\
        ,PriorTime_Stage[stage] = Time, CarDistribution.copy(), PriorCarDistribution.copy(), PriorStTime, PriorTime
    CarSpeedDistribution_Stage[stage] = CarSpeedDistribution.copy()
    archive()
    archive()
    Time -= 1

def stageLoad(stage):
    print("loading stage")
    global CarList, RoadList, CrossList, TheCarport, PriorStTime, PriorTime
    global Time_Stage, CarDistribution_Stage, PriorCarDistribution_Stage, PriorStTime_Stage, PriorTime_Stage
    global Time, CarDistribution, PriorCarDistribution, CarSpeedDistribution, CarSpeedDistributionS_Stage
    global ArchiveIndex, LoadIndex, LoadTime,TheStage
    TheStage = stage
    for i in range(CarList.__len__()):
        CarList[i].stage_load(stage)
    for i in range(RoadList.__len__()):
        RoadList[i][0].stage_load(stage)
        if RoadList[i][1] is not None:
            RoadList[i][1].stage_load(stage)
    for i in range(CrossList.__len__()):
        CrossList[i].stage_load(stage)
    TheCarport.stage_load(stage)
    Time, CarDistribution, PriorCarDistribution, PriorStTime, PriorTime = \
        Time_Stage[stage], CarDistribution_Stage[stage].copy(), PriorCarDistribution_Stage[stage].copy(), \
        PriorStTime_Stage[stage], PriorTime_Stage[stage]
    CarSpeedDistribution = CarSpeedDistribution_Stage[stage].copy()
    archive()
    archive()
    LoadTime = Time-1
    Time = Time - 1
    print("load done")
    print(Time, CarDistribution, sum(CarDistribution), PriorCarDistribution, sum(PriorCarDistribution))

def getAB(CarInfo):
    global TheA,TheB
    totalCarNum, priorCarNum = 0, 0
    carSpeed, priorCarSpeed = {}, {}
    startPoints, endPoints, priorStartPoints, priorEndPoints = {}, {}, {}, {}
    minTime, maxTime, minPriorTime, maxPriorTime = 10000, 0, 10000, 0
    TheA, TheB = [0] * 5, [0] * 5
    for i in range(CarInfo.__len__()):
        id_, from_, to_, speed_, planTime_, priority_, preset_ = CarInfo[i]
        # a0,b0
        totalCarNum += 1
        # a1,b1
        try:
            carSpeed[speed_] += 1
        except:
            carSpeed[speed_] = 1
        # a2,b2
        maxTime, minTime = max(maxTime, planTime_), min(minTime, planTime_)
        # a3,b3
        try:
            startPoints[from_] += 1
        except:
            startPoints[from_] = 1
        # a4,b4
        try:
            endPoints[to_] += 1
        except:
            endPoints[to_] = 1
        if priority_ == 1:
            # a0,b0
            priorCarNum += 1
            # a1,b1
            try:
                priorCarSpeed[speed_] += 1
            except:
                priorCarSpeed[speed_] = 1
            # a2,b2
            maxPriorTime, minPriorTime = max(maxPriorTime, planTime_), min(minPriorTime, planTime_)
            # a3,b3
            try:
                priorStartPoints[from_] += 1
            except:
                priorStartPoints[from_] = 1
            # a4,b4
            try:
                priorEndPoints[to_] += 1
            except:
                priorEndPoints[to_] = 1

    TheA[0] = round(round(totalCarNum / priorCarNum, 5) * 0.05, 4)
    TheA[1] = round(
        max(carSpeed.keys()) * min(priorCarSpeed.keys()) / max(priorCarSpeed.keys()) / min(carSpeed.keys()) * 0.2375, 5)
    TheA[2] = round(round(maxTime / minTime, 5) * round(minPriorTime / maxPriorTime, 5) * 0.2375, 5)
    TheA[3] = round(len(startPoints.keys()) / len(priorStartPoints.keys()) * 0.2375, 5)
    TheA[4] = round(len(endPoints.keys()) / len(priorEndPoints.keys()) * 0.2375, 5)
    TheB[0] = round(round(totalCarNum / priorCarNum, 5) * 0.8, 5)
    TheB[1] = round(
        max(carSpeed.keys()) * min(priorCarSpeed.keys()) / max(priorCarSpeed.keys()) / min(carSpeed.keys()) * 0.05, 5)
    TheB[2] = round(round(maxTime / minTime, 5) * round(minPriorTime / maxPriorTime, 5) * 0.05, 5)
    TheB[3] = round(len(startPoints.keys()) / len(priorStartPoints.keys()) * 0.05, 5)
    TheB[4] = round(len(endPoints.keys()) / len(priorEndPoints.keys()) * 0.05, 5)
    print(sum(TheA),sum(TheB))

def getScore():
    global TheA, TheB, CarList, PriorTime, PriorStTime
    print("(%d-%d)*%f+%d=%d" % (
        PriorTime, PriorStTime, round(sum(TheA), 5), Time, round((PriorTime - PriorStTime) * round(sum(TheA), 5), 0) + Time))
    return round((PriorTime - PriorStTime) * round(sum(TheA), 5), 0) + Time

def main():
    #***********************************load .txt files***********************************#
    global TheRandom
    TheRandom = myRandom(_randomSeed)
    car_path = sys.argv[1]
    road_path = sys.argv[2]
    cross_path = sys.argv[3]
    preset_answer_path = sys.argv[4]
    answer_path = sys.argv[5]
    carData = open(car_path, 'r').read().split('\n')[1:]
    roadData = open(road_path, 'r').read().split('\n')[1:]
    crossData = open(cross_path, 'r').read().split('\n')[1:]
    presetAnswerData = open(preset_answer_path, 'r').read().split('\n')[1:]
    #********************************* preprocessing ************************************#
    global CarDistribution,PriorCarDistribution
    global CarSpeedDistribution,CarSpeedDistributionSave
    # line = (id,from,to,speed,planTime,priority_, preset_)
    PresetCarNum = 0
    for info in carData:
        id_, from_, to_, speed_, planTime_, priority_, preset_ = info.replace(' ', '').replace('\t', '')[1:-1].split(',')
        try:
            CarSpeedDistribution[int(speed_)] += 1
        except:
            CarSpeedDistribution[int(speed_)] = 1
        PresetCarNum += int(preset_)
        PriorCarDistribution[0] += int(priority_)
        CarInfo.append([int(id_), int(from_), int(to_), int(speed_), int(planTime_), int(priority_), int(preset_)])
    PresetCarNum = max(int(PresetCarNum/10)-1,0)
    CarDistribution[0] = CarInfo.__len__()
    CarSpeedDistributionSave = [CarSpeedDistribution.copy(), CarSpeedDistribution.copy()]
    # line = (id,length,speed,channel,from,to,isDuplex)
    for info in roadData:
        id_, length_, speed_, channel_, from_, to_, isDuplex_ = info.replace(' ', '').replace('\t', '')[1:-1].split(',')
        RoadInfo.append([int(id_), int(length_), int(speed_), int(channel_), int(from_), int(to_), int(isDuplex_)])
    # line = (id,north,east,south,west)
    for info in crossData:
        id_, road1, road2, road3, road4 = info.replace(' ', '').replace('\t', '')[1:-1].split(',')
        CrossInfo.append([int(id_), int(road1), int(road2), int(road3), int(road4)])
    # sort
    CarInfo.sort()
    RoadInfo.sort()
    CrossInfo.sort()
    # map
    for i, info in enumerate(CarInfo):
        CarOriId2CarId[info[0]] = i
    for i, info in enumerate(RoadInfo):
        RoadOriId2RoadId[info[0]] = i
    for i, info in enumerate(CrossInfo):
        CrossOriId2CrossId[info[0]] = i
    # rebuild
    for i in range(CarInfo.__len__()):
        CarInfo[i][1] = CrossOriId2CrossId[CarInfo[i][1]]
        CarInfo[i][2] = CrossOriId2CrossId[CarInfo[i][2]]
    for i in range(RoadInfo.__len__()):
        RoadInfo[i][4] = CrossOriId2CrossId[RoadInfo[i][4]]
        RoadInfo[i][5] = CrossOriId2CrossId[RoadInfo[i][5]]
    for i in range(CrossInfo.__len__()):
        for j in range(1, 5):
            if CrossInfo[i][j] != -1:
                CrossInfo[i][j] = RoadOriId2RoadId[CrossInfo[i][j]]
    # preset route
    for info in presetAnswerData:
        if info.__len__() < 3:
            break
        info = info[1:-1].split(',')
        temp = [CarOriId2CarId[int(info[0])], int(info[1])]
        for roadId in info[2:]:
            temp.append(RoadOriId2RoadId[int(roadId)])
        PresetAnswerInfo.append(temp)
    global CrossCrossRoad, CrossRoadCross
    CrossCrossRoad, CrossRoadCross = [{} for i in range(CrossInfo.__len__())], [{} for i in range(CrossInfo.__len__())]
    for crossId, info in enumerate(CrossInfo):
        for roadId in info[1:]:
            if roadId != -1:
                from_, to_ = RoadInfo[roadId][4:6]
                nextCrossId = from_ if from_ != crossId else to_
                CrossCrossRoad[crossId][nextCrossId] = roadId
                CrossRoadCross[crossId][roadId] = nextCrossId
    #************************************ create classes ************************************#
    global CarList,RoadList,CrossList,CrossRoadDirection,TheCarport,TheGraph
    CarList = [None] * CarInfo.__len__()
    RoadList = [None] * RoadInfo.__len__()
    CrossList = [None] * CrossInfo.__len__()
    CrossRoadDirection = [{} for i in range(CrossInfo.__len__())]
    # car class
    for carId in range(CarInfo.__len__()):
        id_, from_, to_, speed_, planTime_, priority_, preset_ = CarInfo[carId]
        for i in range(_postponeTime.__len__()):
            if priority_ == 0 and preset_ == 0:
                if speed_ == _postponeSpeed[i]:
                    if planTime_ < _postponeTime[i]:
                        planTime_ = _postponeTime[i]
        CarList[carId] = Car(carId, from_, to_, speed_, planTime_, priority_, preset_)
    # road class
    for i in range(RoadInfo.__len__()):
        RoadList[i] = [None, None]
        id_, length_, speed_, channel_, from_, to_, isDuplex_ = RoadInfo[i]
        CrossRoadDirection[from_][i] = 0
        CrossRoadDirection[to_][i] = 1
        RoadDirectionCross.append([to_, from_])
        RoadList[i][0] = Road(i, length_, speed_, channel_, from_, to_, 0)
        if isDuplex_ == 1:
            RoadList[i][1] = Road(i, length_, speed_, channel_, from_, to_, 1)
    # cross class
    for i in range(CrossInfo.__len__()):
        id_, road1, road2, road3, road4 = CrossInfo[i]
        CrossList[i] = Cross(i, road1, road2, road3, road4)
    # ************************************ simulation init ************************************#
    # graph initial
    TheGraph = Graph()
    TheGraph.graphGen()
    TheGraph.carFlowRatioGen()
    TheGraph.routeMapUpdate()
    TheGraph.fullRouteMapUpdate()
    # carport
    TheCarport = Carport()
    # preset car load route
    global _correctionP
    correctionsNormal = []
    correctionsVip = []
    for i in range(PresetAnswerInfo.__len__()):
        carId = PresetAnswerInfo[i][0]
        from_, to_ = CarList[carId].__from__(), CarList[carId].__to__()
        absolute = TheGraph.absolute(from_,to_)
        if absolute + _correctionP < len(PresetAnswerInfo[i][2:]):
            correctionsNormal.append([len(PresetAnswerInfo[i][2:]),carId])
        if CarList[carId].isPriority():
            correctionsVip.append([PresetAnswerInfo[i][1],carId])
        CarList[carId].loadRoute(PresetAnswerInfo[i][1:])
    runTimes = [0 for i in range(CarList.__len__())]
    for carId in range(CarList.__len__()):
        if CarList[carId].isPreset() == 0:
            st, end, speed = CarList[carId].__from__(), CarList[carId].__to__(), CarList[carId].__speed__()
            route = TheGraph.route(st,end)
            runTime = 0
            for roadId, direct in route:
                runTime += RoadList[roadId][0].__length__() / (min(speed, RoadList[roadId][0].__speed__()))
        else:
            speed, route = CarList[carId].__speed__(), CarList[carId].__route__()
            runTime = 0
            for roadId in route:
                runTime += RoadList[roadId][0].__length__() / (min(speed, RoadList[roadId][0].__speed__()))
        runTimes[carId] = round(1/runTime,5)
    # carport initial
    for i in range(PresetAnswerInfo.__len__()):
        TheCarport.carportInit(PresetAnswerInfo[i][0], PresetAnswerInfo[i][1], PresetAnswerInfo[i][2])
    for i in range(CarList.__len__()):
        if CarList[i].isPreset() == 0:
            TheCarport.carportInit(i, CarList[i].__planTime__(),runTime=runTimes[i])
    # correction
    correctionsNormal.sort()
    correctionsVip.sort()
    correctionsVip.reverse()
    if PresetCarNum >= correctionsNormal.__len__():
        PresetCarNum -= correctionsNormal.__len__()
    else:
        correctionsNormal = correctionsNormal[-PresetCarNum:]
        PresetCarNum = 0
    print(PresetCarNum,correctionsNormal.__len__())
    for _,carId in correctionsNormal:
        CarList[carId].setChangable()
    for _,carId in correctionsVip:
        if PresetCarNum == 0:
            break
        if CarList[carId].isChangable():
            pass
        CarList[carId].setChangable()
        PresetCarNum -= 1
    TheCarport.simulateInit()
    # simulate
    getAB(CarInfo)
    simulate = simulation(answer_path)
    simulate.simulate()

if __name__ == "__main__":
    main()

#python CodeCraft-2019.py ../config_1/car.txt ../config_1/road.txt ../config_1/cross.txt  ../config_1/presetAnswer.txt  ../config_1/answer.txt
#python CodeCraft-2019.py ../config_2/car.txt ../config_2/road.txt ../config_2/cross.txt  ../config_2/presetAnswer.txt  ../config_2/answer.txt