# NARS-FighterPlane (Windows)

NARS-FighterPlane 是一个以 *NARS* 作为AI玩家，操纵战机迎击敌机的游戏。

## Preparation 预备

1. 安装Python 3（原存储库使用3.8版本）与pygame库。若需在命令行使用Python，需要将其添加进环境变量`PATH`如`C:\Python\Python38-32\`
2. 要启动ONA，需要安装cygwin，并将其添加进环境变量`PATH`如`C:\cygwin64\bin`
3. 要启动OpenNARS，需要安装Java，并将其添加进环境变量`PATH`如`C:\Program Files\Java\jdk-14.0.2\bin`

## Launch 启动

在目录`NARS-FighterPlane_v1.0`或`NARS-FighterPlane_v2.0`打开命令窗口，并运行命令`python plane_game.py opennars`（使用OpenNARS）或`python plane_game.py ONA`（使用ONA）

## References 参考

OpenNARS: https://github.com/opennars/opennars

ONA: https://github.com/opennars/OpenNARS-for-Applications

NARS-Pong in Unity3D: https://github.com/ccrock4t/NARS-Pong

## Some tests 测试案例

![NARS-Fighter v2 gif](https://github.com/Noctis-Xu/images/blob/main/NARS-FighterPlane_v2.0.gif)
![NARS-Fighter v2 png](https://github.com/Noctis-Xu/images/blob/main/NARS-FighterPlane_v2.0.png)

## 译者注

该存储库主要用于个人研究优化，可能会出现部分代码不完善、无法运行的情况
该存储库现使用版本为**Python 3.11**
