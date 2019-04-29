## 车牌识别部分。
使用不定长识别网络crnn。backbon使用resnet，参数基于resnet的crnn论文。识别率线上96左右。
## for train
### 数据存放格式
	-data
	  -train-data
	    xxx.jpg
	  -train-data-label.txt

### 本地训练：
	需要注释3到6行moxing部分，若在windows下还需要注释50和54行num_workers
	python3 train.py --data_url  data --train_url output --cuda 1 --workers 7
### 云端训练参数
	data_url = data路径
	train-url = train路径
	lr = 0.001
	cuda = 1
	workers = 7 
	
## for deploy 
	注意数据预处理要保持一致= =（预设即一致）
