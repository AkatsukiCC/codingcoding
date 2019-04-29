import torch
from torch.utils.data import Dataset
from PIL import Image
import os
import torchvision.transforms as TF


char2label = {'深': 0, '秦': 1, '京': 2,'海': 3,'成': 4, '南': 5, '杭': 6, '苏': 7, '松': 8,
              '0':9, '1':10, '2':11, '3':12, '4':13, '5':14, '6':15, '7':16, '8':17, '9':18,
              'A':19, 'B':20, 'C':21, 'D':22, 'E':23, 'F':24, 'G':25, 'H':26, 'I':27, 'J':28,
              'K':29, 'L':30, 'M':31, 'N':32, 'O':33, 'P':34, 'Q':35, 'R':36, 'S':37, 'T':38,
              'U':39, 'V':40, 'W':41, 'X':42, 'Y':43, 'Z':44}
'''
char2label = {'深': 0, '秦': 1, '京': 2,'海': 3,'成': 4, '南': 5, '杭': 6, '苏': 7, '松': 8,
              '0':0, '1':1, '2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9,
              'A':10, 'B':11, 'C':12, 'D':13, 'E':14, 'F':15, 'G':16, 'H':17, 'I':18, 'J':19,
              'K':20, 'L':21, 'M':22, 'N':23, 'O':24, 'P':25, 'Q':26, 'R':27, 'S':28, 'T':29,
              'U':30, 'V':31, 'W':32, 'X':33, 'Y':34, 'Z':35}
'''
toTensor = TF.ToTensor()

class trainDataset(Dataset):
    def __init__(self, root=None,pictures=None, transform=None):
        assert root is not None,print('root must be set!')
        self.root = os.path.join(root,'train-data')
        self.pictures = pictures
        self.length = self.pictures.__len__()
        self.labels={}
        label_path = os.path.join(root,'train-data-label.txt')
        with open(label_path,'r',encoding='utf-8') as f:
            for line in f:
                line = line.strip().replace(' ', '').split(',')
                self.labels[line[1]] = line[0]
        self.transform = transform
    def __len__(self):
        return self.length
    def __getitem__(self, index):
        global chinese2english
        assert index<self.length and index>=0,print('index out of range in dataset.__getitem__(index)')
        path = os.path.join(self.root, self.pictures[index])
        img = Image.open(path).convert('RGB')
        if self.transform is not None:
            img = self.transform(img)
        img = img.resize((200, 64))
        img = toTensor(img)
        #img.sub_(0.5).div_(0.5)
        label = self.labels[self.pictures[index]]
        label = torch.tensor([char2label[label[i]]+1 for i in range(9)])
        length = torch.tensor(9)
        return img, label, length

