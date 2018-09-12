# pytorch-kaldi-asr
由于kaldi的神经网络模块调试困难。这个项目旨在使用kaldi提取语音特征，然后利用pytorch训练神经网络，进行相关的科学研究，以便快速验证思路是否可行。
需要使用kaldi-io-for-python这一胶水库，把kaldi里的数据文件读取python。

kaldi-io库github地址：https://github.com/vesis84/kaldi-io-for-python
安装kaldi-io后记得在kaldi_io.py里设置kaldi路径以便添加环境变量

要创建自己的项目，请进入project目录，拷贝一份example_project
里面的run.sh会指导你如何使用该项目的脚本