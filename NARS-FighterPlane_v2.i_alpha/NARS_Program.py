"""有关NARS智能体与「NARS具体计算机实现」的通信
- NARS种类：注册已有的「NARS具体计算机实现」类型
- NARS程序：抽象一个「NARS具体计算机实现」通信接口
"""

import threading # 用于打开线程
import queue
import subprocess # 用于打开进程
import signal # 用于终止程序

from enum import Enum # 枚举NARS类型

from NARS_Elements import *
from NARS_Elements import NARSPerception # 导入各类元素（从命令行返回到具体NARS元素）

"""NARS具体实现的「类型」
记录NARS具体实现时调用的类型
"""
class NARSType(Enum):
    
    OPENNARS:str = 'opennars'
    ONA:str = 'ONA'
    PYTHON:str = 'python'

"""具体与纳思通信的「程序」
核心功能：负责与「NARS的具体计算机实现」沟通
- 例：封装好的NARS程序包（支持命令行交互
"""
class NARSProgram:
    
    # NAL内置对象区 #
    
    '表示「自我」的对象'
    _TERM_SELF:str = '{%s}' % NARSPerception.OBJECT_SELF # 嵌入「自我」词项（必须是{专名}的形式）
    
    # NAL语句模板区 #
    
    '指示「某个对象有某个状态」'
    SENSE_TEMPLETE:str = '<{%s} --> [%s]>. :|:'

    '指示「自我正在执行某操作」（无意识操作 Babble）'
    BABBLE_TEMPLETE:str = f'<(*,{_TERM_SELF}) --> ^%s>. :|:' # 注意：是操作的名字
    
    '指示「自我需要达到某个目标」'
    GOAL_TEMPLETE:str = f'<{_TERM_SELF} --> [%s]>! :|:' # ？是否一定要一个「形容词」？
    GOAL_TEMPLETE_NEGATIVE:str = f'(--, <{_TERM_SELF} --> [%s]>)! :|:' # 一个「负向目标」，指导「实现其反面」
    
    '指示「某目标被实现」'
    PRAISE_TEMPLETE = f'<{_TERM_SELF} --> [%s]>. :|:'
    
    '指示「某目标未实现」'
    PUNISH_TEMPLETE = f'(--,<{_TERM_SELF} --> [%s]>). :|:'
    # '<{SELF} --> [good]>. :|: %0%' # opennars' grammar
    # '<{SELF} --> [good]>. :|: {0}' # ONA's grammar
    # 📝不同的NARS实现，可能对「反向真值」有不同的语法
    
    # 程序构造入口 #
    
    @staticmethod
    def fromType(type:NARSType):
        if type == NARSType.OPENNARS:
            return opennars()
        if type == NARSType.ONA:
            return ONA()
        if type == NARSType.PYTHON:
            return Python()
    
    # 程序/进程相关 #
    
    def __init__(self, operationHook=None):
        "初始化NARS程序：启动命令行、连接「NARS计算机实现」、启动线程"
        "推理循环频率"
        self.inference_cycle_frequency:int = 1  # set too large will get delayed and slow down the game
        "🆕存储输出「纳思操作」的钩子：在从命令行读取到操作时，输出到对应函数中"
        self.operationHook = operationHook
        self.launch_nars()
        self.launch_thread()

    # 用析构函数替代「process_kill」方法
    def __del__(self):
        "程序结束时，自动终止NARS"
        self.process.send_signal(signal.CTRL_C_EVENT)
        self.process.terminate()

    def launch_nars(self):
        "使用cmd形式打开子进程，并根据NARS类型启动对应程序（适用于命令行打开的程序）"
        self.process = subprocess.Popen(["cmd"], bufsize=1,
                                        stdin=subprocess.PIPE, # 输入管道
                                        stdout=subprocess.PIPE, # 输出管道
                                        universal_newlines=True,  # convert bytes to text/string
                                        shell=False)
        self.launch_program() # 🆕「具体启动程序」交给剩下的子类实现
        self._add_to_cmd('*volume=0')
        
    def launch_program(self):
        "直接启动程序"
        pass

    def launch_thread(self):
        "开启子线程，负责对NARS程序的读写工作"
        self.read_line_thread = threading.Thread(
            target=self.read_line,
            args=(self.process.stdout,)
        )
        self.read_line_thread.daemon = True  # thread dies with the exit of the program
        self.read_line_thread.start()
    
    # 语句相关 #
    
    def add_perception(self, perception:NARSPerception) -> None:
        "统一添加感知"
        self._add_to_cmd(
            self.__class__.SENSE_TEMPLETE % (perception.object, perception.adjective) # 套模板
        )
    
    # 目标
    def put_goal(self, goalName:str, is_negative:bool = False):
        "向智能体置入目标（以NAL语句的形式）"
        self._add_to_cmd(
            (
                self.__class__.GOAL_TEMPLETE_NEGATIVE # 根据不同类的常量决定模板
                if is_negative
                else self.__class__.GOAL_TEMPLETE
            ) % goalName
        )
    
    def praise_goal(self, goalName:str):
        "让智能体感到「目标被实现」，亦即「奖励」"
        self._add_to_cmd(self.__class__.PRAISE_TEMPLETE % goalName)
    
    def punish_goal(self, goalName:str):
        "让智能体感到「目标未实现」，亦即「惩罚」"
        self._add_to_cmd(self.__class__.PUNISH_TEMPLETE % goalName)

    @property
    def enable_babble(self) -> bool:
        return bool(self.__class__.BABBLE_TEMPLETE)
    
    def put_unconscious_operation(self, operation:NARSOperation):
        "强制「无意识操作」：告诉NARS程序「我执行了这个操作」"
        if self.__class__.BABBLE_TEMPLETE and (sentence := (self.__class__.BABBLE_TEMPLETE % operation.name)):
            self._add_to_cmd(sentence) # 置入「自己在进行什么操作」
    
    # 运行时相关 #

    def read_line(self, out):  # read line without blocking
        "读取程序的（命令行）输出"
        for line in iter(out.readline, b'\n'):  # get operations
            if operation_name := self.catch_operation_name(line): # 从一行语句中获得操作
                operation:NARSOperation = NARSOperation(operation_name) # 从字符串到操作（打包）
                if self.operationHook: # 若非空
                    self.operationHook(operation) # 直接传递一个「纳思操作」到指定位置
        out.close() # 关闭输出流
    
    def catch_operation_name(self, line:str):
        "从输出的一行（语句）中获取信息，并返回截取到的「操作字符串」"
        pass

    def _add_to_cmd(self, cmd:str):
        "向命令行添加命令"
        self.process.stdin.write(cmd + '\n')
        self.process.stdin.flush()
    
    def add_inference_cycles(self, num:int):
        "推理循环步进"
        self.process.stdin.write(f'{num}\n')
        self.process.stdin.flush()
    
    def update_inference_cycles(self) -> None:
        "更新自身推理循环"
        if self.inference_cycle_frequency: # 若大于零
            self.add_inference_cycles(self.inference_cycle_frequency)


"Java版实现：OpenNARS"
class opennars(NARSProgram):
    
    "可执行文件路径"
    DEFAULT_JAR_PATH:str = r'.\opennars.jar'
    
    # 特有语法区 #
    
    PUNISH_TEMPLETE = f'<{NARSProgram._TERM_SELF} --> [%s]>. :|: %0%' # opennars' grammar
    
    def launch_program(self):
        super().launch_program()
        # OpenNARS的实现
        self._add_to_cmd(f'java -Xmx1024m -jar {self.jar_path}')  # self.add_to_cmd('java -Xmx2048m -jar opennars.jar')
    
    def __init__(self, jar_path:str = DEFAULT_JAR_PATH):
        self.jar_path = jar_path
        super().__init__(NARSType.OPENNARS)
        self.inference_cycle_frequency = 5

    def catch_operation_name(self, line:str) -> str:
        if line[0:3] == 'EXE': # 若为操作前缀
            subline = line.split(' ', 2)[2] # 获取EXE后语句
            # print(subline) # 操作文本：「EXE ^right([{SELF}])=null」
            return subline.split('(', 1)[0][1:] # 避免'^^opera'

"C实现：OpenNARS for Application"
class ONA(NARSProgram):
    
    "可执行文件路径"
    DEFAULT_EXE_PATH:str = r'.\NAR.exe'
    
    # 特有语法区 #
    
    BABBLE_TEMPLETE:str = None # ONA Babble 无效：语句「<(*,{SELF}) --> ^deactivate>. :|:」报错「OSError: [Errno 22] Invalid argument」
    
    PUNISH_TEMPLETE = f'<{NARSProgram._TERM_SELF} --> [%s]>. :|: {"{0}"}' # ONA's grammar （注：这里使用「{"{0}"}」避免字符串歧义）
    
    def __init__(self, exe_path:str = DEFAULT_EXE_PATH):
        self.exe_path = exe_path
        super().__init__(NARSType.ONA)
        self.inference_cycle_frequency = 0
    
    def launch_program(self):
        super().launch_program()
        # ONA的实现
        self._add_to_cmd(f'{self.exe_path} shell')

    def catch_operation_name(self, line:str) -> str:
        if (line[0:1] == '^'): # 避免在退出游戏时出错
            # print(line) # 操作文本：「EXE ^right executed with args」
            return line.split(' ', 1)[0][1:] # 避免'^^opera'

"Python实现：NARS Python（WIP）"
class Python(NARSProgram):
    
    "程序路径"
    DEFAULT_EXE_PATH:str = r'.\main.exe'
    
    # 特定模板 # 注：NARS-Python 对语句使用圆括号
    
    '指示「某个对象有某个状态」'
    SENSE_TEMPLETE:str = '({%s} --> [%s]). :|:'

    '指示「自我正在执行某操作」（无意识操作 Babble）'
    BABBLE_TEMPLETE:str = '((*, {SELF}) --> %s)! :|:' # 移植自NARS-Pong
    
    '指示「自我需要达到某个目标」'
    GOAL_TEMPLETE:str = f'({NARSProgram._TERM_SELF} --> [%s])! :|:' # ？是否一定要一个「形容词」？
    GOAL_TEMPLETE_NEGATIVE:str = f'({NARSProgram._TERM_SELF} --> (-, [%s]))! :|:' # 语法来自NARS Python
    
    '指示「某目标被实现」'
    PRAISE_TEMPLETE = f'({NARSProgram._TERM_SELF} --> [%s]). :|:'
    
    '指示「某目标未实现」'
    PUNISH_TEMPLETE = f'({NARSProgram._TERM_SELF} --> [%s]). :|: %0.00;0.90%'
    
    # 类实现 #
    
    def __init__(self, exe_path:str = DEFAULT_EXE_PATH):
        self.exe_path = exe_path
        super().__init__(NARSType.ONA)
        self.inference_cycle_frequency = 0
    
    def launch_program(self):
        super().launch_program()
        # NARS Python实现
        self._add_to_cmd(f'{self.exe_path}')

    def catch_operation_name(self, line:str) -> str:
        if 'reject' in line.lower():
            print(f'Reject: {line}')
        # self.put_unconscious_operation(NARSOperation('test')) # python babble
        if 'EXE' in line: # 若为操作前缀
            # print(f'{line}') # 操作文本：「EXE: ^left based on desirability: 0.9」
            return line.split(' ', 2)[1][1:]
 