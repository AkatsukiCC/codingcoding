
import torchvision.transforms as TF



def trainDataTransform(colorJitter=False,rotation=False,crop=False,grayscale=False):
    #randomResizeCrop = TF.RandomResizedCrop(size=(148,35),scale=(0.9,1.0),ratio=(0.9,1.1))
    return TF.Compose([
        TF.RandomGrayscale(p=0.05),
        TF.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.2),
        TF.RandomRotation(10)
    ])





def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        m.weight.data.normal_(0.0, 0.02)
    elif classname.find('BatchNorm') != -1:
        m.weight.data.normal_(1.0, 0.02)
        m.bias.data.fill_(0)



class evalMethod():
    def __init__(self):
        self.charNum = 0
        self.rightCharNum = 0
        self.loss = 0
        self.num = 0
    def reset(self):
        self.charNum = 0
        self.rightCharNum = 0
        self.loss = 0
        self.num = 0
    def evalStep(self,pred,label,loss):
        pred = pred.max(2)[1]
        count = 0
        for i in range(pred.size()[1]):
            k = 0
            for j in range(pred.size()[0]):
                if k == 9:
                    break
                if pred[j][i] != 0:
                    if pred[j][i] == label[i][k]:
                        count += 1
                    k += 1
        self.rightCharNum += count
        self.charNum += float(label.size()[0]*label.size()[1])
        self.loss += loss.cpu().data
        self.num += float(label.size()[0])
        return loss.cpu().data/float(label.size()[0]),count/float(label.size()[0]*label.size()[1])
    def eval(self):
        return self.loss/self.num,self.rightCharNum/self.charNum
