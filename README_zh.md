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

- 对原版NARS的改进
  - 新的感知渠道：「是否在边界」（分左右两个版本）
- 更通用化的Python接口代码
  - 将「智能体定义」和「与NARS程序通信」分离
  - 集中定义NAL语句，避免分散与重复
  - 更高的代码重用率
- 优化游戏的测试环境
  - 一个bat启动脚本
  - 更多启动的可选参数
    - 游戏速度
    - 是否启用「惩罚」机制
  - 游戏内「键盘操作」功能
    - 上下左右/空格：移动&射击
    - `G`：提醒NARS目标
    - `P`：根据游戏数据绘制图表
    - `B`：控制NARS的babble
      - `B`：增加10个babble时间
      - +`Shift`：减少10个babble时间
      - +`Alt`：立即发送一个babble
    - `N`：在命令行窗口直接输入NAL语句（不稳定）
      - 会暂停游戏运行
      - ！语句错误可能导致游戏崩溃
    - `E`：启用/禁用 NARS的感知/操作
      - +`Shift`：指定是「操作」否则「感知」
      - GUI有专门提示：「NARS perception/operation off/on」
      - 禁用后，NARS执行的感知/操作无法送达Agent
- ...

该存储库主要用于个人研究优化，可能会出现部分代码不完善、无法运行、与原项目差异过大的情况
