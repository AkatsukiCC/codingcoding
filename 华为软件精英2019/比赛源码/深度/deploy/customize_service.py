import os
import math
print(os.path.abspath('.'))
import torch
import torch.nn as nn
from PIL import Image
from model_service.pytorch_model_service import PTServingBaseService
import torchvision.transforms as transforms
toTensor=transforms.ToTensor()



label2char = {0: '-', 1: '0', 2: '1', 3: '2', 4: '3', 5: '4', 6: '5', 7: '6', 8: '7', 9: '8',
              10: '0', 11: '1', 12: '2', 13: '3', 14: '4', 15: '5', 16: '6', 17: '7', 18: '8', 19: '9',
              20: 'A', 21: 'B', 22: 'C', 23: 'D', 24: 'E', 25: 'F', 26: 'G',
              27: 'H', 28: 'I', 29: 'J', 30: 'K', 31: 'L', 32: 'M', 33: 'N',
              34: 'O', 35: 'P', 36: 'Q', 37: 'R', 38: 'S', 39: 'T', 40: 'U',
              41: 'V', 42: 'W', 43: 'X', 44: 'Y', 45: 'Z'}

class huawei2019(PTServingBaseService):
    def __init__(self,model_name, model_path,gpu=None):
        print(model_name,model_path,)
        self.model_name = model_name
        self.model_path = model_path
        self.model = resCRNN()
        self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        self.model.eval()
    def _preprocess(self, data):
        for key in data['images'].keys():
            img_path = data['images'][key]
        img = Image.open(img_path).convert('RGB')
        img = img.resize((200,64))
        img = toTensor(img)
        #img.sub_(0.5).div_(0.5)
        img = img.unsqueeze(0)
        return img
    def _postprocess(self, preds):
        string = ''
        preds = preds.argmax(2)[:,0]
        for value in preds:
            if value != 0:
                string += label2char[int(value)]
        return string
    def _inference(self,img):
        return self.model(img)



class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self, in_planes, planes, stride=1,padding=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=1, bias=False)
        self.BN1 = nn.BatchNorm2d(planes)
        self.relu1 = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False) # outplane is not in_planes*self.expansion, is planes
        self.BN2 = nn.BatchNorm2d(planes)
        self.relu2 = nn.ReLU(inplace=True)
        self.stride = stride
        self.downsample = downsample

    def forward(self, x):
        residual = x  
        x = self.conv1(x)
        x = self.BN1(x)
        x = self.relu1(x)
        x = self.conv2(x)
        x = self.BN2(x)  
        if self.downsample is not None:
            residual = self.downsample(residual)
        x += residual
        x = self.relu2(x)
        return x

class BidirectionalLSTM(nn.Module):
    def __init__(self, nIn, nHidden, nOut):
        super(BidirectionalLSTM, self).__init__()
        self.rnn = nn.LSTM(nIn, nHidden, bidirectional=True)
        self.embedding = nn.Linear(nHidden * 2, nOut)

    def forward(self, input):
        recurrent, _ = self.rnn(input)
        T, b, h = recurrent.size()
        t_rec = recurrent.view(T * b, h)
        output = self.embedding(t_rec)  # [T * b, nOut]
        output = output.view(T, b, -1)
        return output


class ResNet(nn.Module):
    def __init__(self, block, layers):
        self.inplanes = 32 # the original channel
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(32)
        self.relu = nn.ReLU(inplace=True)
        self.max_pool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 32, layers[0],stride=(2,2))
        self.layer2 = self._make_layer(block, 64, layers[1], stride=(2,1))
        self.layer3 = self._make_layer(block, 128, layers[2], stride=(2,1))
        self.layer4 = self._make_layer(block, 256, layers[3], stride=(2,1))
        self.layer5 = self._make_layer(block, 512, layers[4], stride=(2,1))
        self.average_pool = nn.AdaptiveAvgPool2d((1,12))
        self.rnn = nn.Sequential(
            BidirectionalLSTM(512, 256, 256),
            BidirectionalLSTM(256, 256, 46))
    def _make_layer(self, block, planes, num_blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != block.expansion * planes:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, block.expansion*planes,kernel_size=3, stride=stride,padding=1,bias=False),
                nn.BatchNorm2d(block.expansion*planes)
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride=stride,downsample=downsample)) 
        self.inplanes = planes * block.expansion
        for i in range(1, num_blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.max_pool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)
        x = self.average_pool(x)
        b, c, h, w = x.size()
        x = x.squeeze(2)
        x = x.permute(2, 0, 1)  # [w, b, c]

        # rnn features
        x = self.rnn(x)
        return x

def resCRNN():
    model = ResNet(BasicBlock, [3, 4, 6, 6, 3])
    return model