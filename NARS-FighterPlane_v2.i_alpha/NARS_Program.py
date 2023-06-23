import threading # 用于打开线程
import queue
import subprocess # 用于打开进程
import signal # 用于终止程序

from enum import Enum # 枚举NARS类型

"""NARS具体实现的「类型」
记录NARS具体实现时调用的类型
"""
class NARSType(Enum):
    
    OPENNARS:str = 'opennars'
    ONA:str = 'ONA'

from NARS import NARSOperation, NARSPerception # 导入操作以便打包

"""具体与纳思通信的「程序」
核心功能：负责与「NARS的具体计算机实现」沟通
- 例：封装好的NARS程序包（支持命令行交互
"""
class NARSProgram:
    
    @staticmethod
    def fromType(type:NARSType):
        if type == NARSType.OPENNARS:
            return opennars()
        if type == NARSType.ONA:
            return ONA()
    
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
        self.add_to_cmd('*volume=0')
        
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
    def parse_perception_sentence(self, perception:NARSPerception) -> str:
        "🆕解析「感知语句」"
        # TODO：将「具体语句实现」分离至Program，从而让NARSAgent无需涉及具体的语句实现
        # 并且，这也可以被后续继承的NARSProgram重载，以实现「不同NARS程序使用不同NAL语法」
        return NARSProgram.SENSE_TEMPLETE % (perception.object, perception.adjective)
    
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

    def add_to_cmd(self, cmd:str):
        "向命令行添加命令"
        self.process.stdin.write(cmd + '\n')
        self.process.stdin.flush()
    
    def add_inference_cycles(self, num:int):
        "推理循环步进"
        self.process.stdin.write(f'{num}\n')
        self.process.stdin.flush()
    
    def update_inference_cycles(self) -> None:
        "🆕更新自身推理循环"
        if self.inference_cycle_frequency: # 若大于零
            self.add_inference_cycles(self.inference_cycle_frequency)

"Java版实现：OpenNARS"
class opennars(NARSProgram):
    
    def launch_program(self):
        super().launch_program()
        # 🆕OpenNARS的实现
        self.add_to_cmd('java -Xmx1024m -jar opennars.jar')  # self.add_to_cmd('java -Xmx2048m -jar opennars.jar')
    
    def __init__(self):
        super().__init__(NARSType.OPENNARS)
        self.inference_cycle_frequency = 5

    def catch_operation_name(self, line:str) -> str:
        if line[0:3] == 'EXE': # 若为操作前缀
            subline = line.split(' ', 2)[2] # 获取EXE后语句
            # print(subline) # 操作文本：「EXE ^right([{SELF}])=null」
            return subline.split('(', 1)[0][1:] # 避免'^^opera'

"C实现：OpenNARS for Application"
class ONA(NARSProgram):
    def __init__(self):
        super().__init__(NARSType.ONA)
        self.inference_cycle_frequency = 0
    
    def launch_program(self):
        super().launch_program()
        # 🆕ONA的实现
        self.add_to_cmd('NAR shell')

    def catch_operation_name(self, line:str) -> str:
        if (line[0:1] == '^'): # 🆕避免在退出游戏时出错
            # print(line) # 操作文本：「EXE ^right executed with args」
            return line.split(' ', 1)[0][1:] # 避免'^^opera'
