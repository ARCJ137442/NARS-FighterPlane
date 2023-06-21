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

(原repo) NARS-FighterPlane by Boyang Xu: https://github.com/Noctis-Xu/NARS-FighterPlane

## Some tests 测试案例

![NARS-Fighter v2 gif](https://github.com/Noctis-Xu/images/blob/main/NARS-FighterPlane_v2.0.gif)
![NARS-Fighter v2 png](https://github.com/Noctis-Xu/images/blob/main/NARS-FighterPlane_v2.0.png)

## 译者注

该存储库现使用版本为**Python 3.11**

主要修改的项目文件夹：`NARS-FighterPlane_v2.i_alpha`

`v2.i_alpha` 基于原项目添加的新特性/修改：
- 新的感知渠道：「是否在边界」（分左右两个版本）
- 一个bat启动脚本
- 更多启动的可选参数
  - 游戏速度
  - 是否启用「惩罚」机制
- 更通用化的Python接口代码
  - 将「智能体定义」和「与NARS程序通信」分离
  - 集中定义NAL语句，避免分散与重复
  - 更高的代码重用率
  - ...

该存储库主要用于个人研究优化，可能会出现部分代码不完善、无法运行、与原项目差异过大的情况
