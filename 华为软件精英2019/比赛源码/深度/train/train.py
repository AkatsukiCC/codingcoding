import os

os.system("rm /home/work/anaconda3/lib/libmkldnn.so")
os.system("rm /home/work/anaconda3/lib/libmkldnn.so.0")
import moxing as mox
mox.file.shift('os', 'mox')


import torch.optim as optim
import torch.utils.data
from torch.nn import CTCLoss


from model import myCRNN,resCRNN
import dataset
import utils
from sklearn.model_selection import train_test_split
import argparse



parser = argparse.ArgumentParser()
parser.add_argument('--data_url', type=str, default='')
parser.add_argument('--train_url', type=str, default='')
parser.add_argument('--workers', type=int,default=2)
parser.add_argument('--cuda',  type=int, default=0)
parser.add_argument('--maxEpoch', type=int, default=1000)
parser.add_argument('--lr', type=float, default=0.001)
parser.add_argument('--batchSize', type=int, default=64)
opt, unkown = parser.parse_known_args()



if torch.cuda.is_available() and opt.cuda != 1:
    print("CUDA device is available!")


picture_path = os.path.join(opt.data_url,'train-data')
pictures = os.listdir(picture_path)
trainPictures,valPictures=train_test_split(pictures,test_size=0.2,random_state=951022)

trainDataTransform = utils.trainDataTransform()

train_dataset = dataset.trainDataset(root=opt.data_url,pictures=trainPictures,
                                     transform = trainDataTransform)
val_dataset = dataset.trainDataset(root=opt.data_url,pictures=valPictures)
train_loader = torch.utils.data.DataLoader(
    train_dataset, batch_size=opt.batchSize,
    shuffle=True,
    num_workers= opt.workers
    )
val_loader = torch.utils.data.DataLoader(
    val_dataset, batch_size=opt.batchSize,
    num_workers= opt.workers
    )


huawei2019 = resCRNN()
huawei2019.apply(utils.weights_init)



optimizer = optim.Adam(huawei2019.parameters(), lr=opt.lr,
                           betas=(0.8, 0.99))
criterion = CTCLoss()
evalMethod = utils.evalMethod()
if opt.cuda == 1:
    criterion = criterion.cuda()
    huawei2019 = huawei2019.cuda()

valBestAcc = 0.5
for epoch in range(opt.maxEpoch):
    train_iter = iter(train_loader)
    val_iter = iter(val_loader)
    for p in huawei2019.parameters():
        p.requires_grad = True
    huawei2019.train()
    evalMethod.reset()
    for i in range(0,len(train_loader)):
        data = train_iter.next()
        images,label,label_length = data
        batch_size = images.size(0)
        if opt.cuda == 1:
            images=images.cuda()
            label = label.cuda()
        preds = huawei2019(images)
        pred_length = torch.IntTensor([preds.size(0)] * batch_size)
        loss = criterion(preds, label, pred_length, label_length) / batch_size
        huawei2019.zero_grad()
        loss.backward()
        optimizer.step()
        _,_ = evalMethod.evalStep(preds,label,loss.cpu().data*batch_size)
    print("*" * 10, "[epoch:%d]train dataset"%epoch, "*" * 10)
    print("[%d]pred:"% epoch,preds[:,0,:].max(1)[1])
    print("[%d]label:"% epoch,label[0])
    print(evalMethod.eval())
    for p in huawei2019.parameters():
        p.requires_grad = False
    huawei2019.eval()
    evalMethod.reset()
    for i in range(0,len(val_loader)):
        data = val_iter.next()
        images,label,label_length = data
        batch_size = images.size(0)
        if opt.cuda == 1:
            images = images.cuda()
            label = label.cuda()
        preds = huawei2019(images)
        pred_length = torch.IntTensor([preds.size(0)] * batch_size)
        loss = criterion(preds, label, pred_length, label_length) / batch_size
        _, _ = evalMethod.evalStep(preds, label, loss.cpu().data * batch_size)
    print("*"*10,"[epoch:%d]val dataset"%epoch,"*"*10)
    print("[%d]pred:"%epoch,preds[:, 0,:].max(1)[1])
    print("[%d]label:"%epoch,label[0])
    print(evalMethod.eval())
    _, acc = evalMethod.eval()
    if acc > valBestAcc:
        valBestAcc = acc
        torch.save(
            huawei2019.state_dict(), '{0}/netCRNN_{1}_{2}_{3}.pth'.format(opt.train_url, epoch, i,acc))
    elif epoch % 20 == 19:
        torch.save(
            huawei2019.state_dict(), '{0}/netCRNN_{1}_{2}_{3}.pth'.format(opt.train_url, epoch, i, acc))

