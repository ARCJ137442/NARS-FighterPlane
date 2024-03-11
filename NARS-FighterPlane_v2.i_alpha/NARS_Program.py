"""有关NARS智能体与「NARS具体计算机实现」的通信
- NARS种类：注册已有的「NARS具体计算机实现」类型
- NARS程序：抽象一个「NARS具体计算机实现」通信接口
"""

import threading  # 用于打开线程
import queue
import subprocess  # 用于打开进程
import signal  # 用于终止程序

from enum import Enum  # 枚举NARS类型

from NARS_Elements import *  # 导入各类元素（从命令行返回到具体NARS元素）

DEBUG: bool = True


class NARSType(Enum):
    """NARS具体实现的「类型」
    记录NARS具体实现时调用的类型
    """

    OPENNARS: str = 'opennars'
    ONA: str = 'ONA'
    ONA_OLD: str = 'ONA_old'
    PYTHON: str = 'python'

    @staticmethod
    def from_str(type_str):
        # 📝【2024-03-11 22:51:21】MagicPython扩展无法高亮这里的`match`
        match type_str.lower():
            case 'opennars':
                return NARSType.OPENNARS
            case 'ona':
                return NARSType.ONA
            case 'ona_old':
                return NARSType.ONA_OLD
            case 'python':
                return NARSType.PYTHON

    @staticmethod
    @property
    def values() -> list[str]:
        return [t.value for t in NARSType]


class NARSProgram:
    """具体与纳思通信的「程序」
    核心功能：负责与「NARS的具体计算机实现」沟通
    - 例：封装好的NARS程序包（支持命令行交互
    """

    # NAL内置对象区 #

    # 嵌入「自我」词项（必须是{专名}的形式）
    _TERM_SELF: str = '{%s}' % NARSPerception.OBJECT_SELF
    '表示「自我」的对象'

    # NAL语句模板区 #

    SENSE_TEMPLATE: str = '<{%s} --> [%s]>. :|:'
    '指示「某个对象有某个状态」'

    BABBLE_TEMPLATE: str = f'<(*,{_TERM_SELF}) --> ^%s>. :|:'  # 注意：是操作的名字
    '指示「自我正在执行某操作」（无意识操作 Babble）'

    GOAL_TEMPLATE: str = f'<{_TERM_SELF} --> [%s]>! :|:'  # ？是否一定要一个「形容词」？
    '指示「自我需要达到某个目标」'
    GOAL_TEMPLATE_NEGATIVE: str = f'(--, <{_TERM_SELF} --> [%s]>)! :|:'
    '一个「负向目标」，指导「实现其反面」'

    PRAISE_TEMPLATE: str = f'<{_TERM_SELF} --> [%s]>. :|:'
    '指示「某目标被实现」'

    PUNISH_TEMPLATE: str = f'(--,<{_TERM_SELF} --> [%s]>). :|:'
    '指示「某目标未实现」'

    OPERATION_REGISTER_TEMPLATE: str = BABBLE_TEMPLATE  # 暂时使用Babble的模板
    '指示「自我有一个可用的（基本）操作」（操作注册）'

    # 程序构造入口 #

    @staticmethod
    def fromType(type: NARSType):
        if type == NARSType.OPENNARS:
            return opennars()
        if type == NARSType.ONA:
            return ONA()
        if type == NARSType.ONA_OLD:
            return ONA(r'.\NAR_old.exe')
        if type == NARSType.PYTHON:
            return Python()

    # 程序/进程相关 #

    def __init__(self, operationHook=None):
        "初始化NARS程序：启动命令行、连接「NARS计算机实现」、启动线程"
        "推理循环频率"
        # set too large will get delayed and slow down the game
        self.inference_cycle_frequency: int = 1
        "🆕存储输出「纳思操作」的钩子：在从命令行读取到操作时，输出到对应函数中"
        self.operationHook = operationHook
        self._cached_cmds: list[str] = []  # 定义一个先进先出队列，存储待写入的指令
        self.launch_nars()
        self.launch_thread_read()
        self.launch_thread_write()

    # 用析构函数替代「process_kill」方法
    def __del__(self):
        "程序结束时，自动终止NARS"
        self.terminate()

    def terminate(self):
        try:
            self.process.send_signal(signal.CTRL_C_EVENT)
            self.process.terminate()
            self.process = None  # 空置
        except BaseException as e:
            print(f'Failed to terminate process: {e}')

    def launch_nars(self):
        """并行启动NARS
        使用cmd形式打开子进程，并根据NARS类型启动对应程序（适用于命令行打开的程序）
        创建一个子进程来执行 ls -l 命令，并将标准输出和错误输出捕获到 output 和 error 变量中。
            母进程可以继续执行其他任务，而不会被阻塞，直到需要获取子进程输出的时候再调用 process.communicate()
        """
        self.process = subprocess.Popen(["cmd"],
                                        bufsize=1,
                                        stdin=subprocess.PIPE,  # 输入管道
                                        stdout=subprocess.PIPE,  # 输出管道
                                        universal_newlines=True,  # convert bytes to text/string
                                        shell=False)
        self.launch_program()  # 「具体启动程序」交给剩下的子类实现
        self.write_line('*volume=0')

    def launch_program(self):
        "直接启动程序"
        pass

    def launch_thread(self, target, args) -> threading.Thread:
        "通用：开启线程（返回开启的线程）"
        self.read_line_thread = threading.Thread(
            target=target,
            args=args
        )

        # 将线程设置为守护线程，即在程序退出时自动终止线程
        self.read_line_thread.daemon = True

        # 启动线程
        self.read_line_thread.start()

    def launch_thread_read(self):
        "开启子线程，负责接收NARS程序的输出"
        # 创建线程对象 self.read_line_thread
        self.read_line_thread = self.launch_thread(
            target=self.read_line,  # 目标函数是 self.read_line
            # 将 self.process.stdout 作为参数传递给 self.read_line 方法
            args=(self.process.stdout,)
        )

    def launch_thread_write(self):
        "解决「写入卡顿」的方案：开启子线程，负责NAL语句的异步写入"
        # 创建线程对象 self.write_line_thread
        self.write_line_thread = self.launch_thread(
            target=self.async_write_lines,  # 目标函数是 self.write_line
            # 将 self.process.stdout 作为参数传递给 self.write_line 方法
            args=(self.process.stdin,)
        )

    # 语句相关 #
    def add_perception(self, perception: NARSPerception) -> None:
        "统一添加感知"
        self.write_line(
            self.__class__.SENSE_TEMPLATE % (
                perception.object, perception.adjective)  # 套模板
        )

    # 目标
    def put_goal(self, goalName: str, is_negative: bool = False):
        "向智能体置入目标（以NAL语句的形式）"
        self.write_line(
            (
                self.__class__.GOAL_TEMPLATE_NEGATIVE  # 根据不同类的常量决定模板
                if is_negative
                else self.__class__.GOAL_TEMPLATE
            ) % goalName
        )

    def praise_goal(self, goalName: str):
        "让智能体感到「目标被实现」，亦即「奖励」"
        self.write_line(self.__class__.PRAISE_TEMPLATE % goalName)

    def punish_goal(self, goalName: str):
        "让智能体感到「目标未实现」，亦即「惩罚」"
        self.write_line(self.__class__.PUNISH_TEMPLATE % goalName)

    @property
    def enable_babble(self) -> bool:
        return bool(self.__class__.BABBLE_TEMPLATE)

    def put_unconscious_operation(self, operation: NARSOperation):
        "强制「无意识操作」：告诉NARS程序「我执行了这个操作」"
        if self.__class__.BABBLE_TEMPLATE and (
            sentence := (self.__class__.BABBLE_TEMPLATE % operation.name)
        ):
            self.write_line(sentence)  # 置入「自己在进行什么操作」

    def register_basic_operation(self, operation: NARSOperation):
        "注册「基础操作」：告诉NARS程序「我可以执行这个操作」"
        if self.__class__.OPERATION_REGISTER_TEMPLATE and (
            sentence := (self.__class__.OPERATION_REGISTER_TEMPLATE % operation.name)
        ):
            self.write_line(sentence)  # 置入「自己在进行什么操作」

    # 运行时相关 #

    def read_line(self, out):  # read line without blocking
        "读取程序的（命令行）输出"
        for line in iter(out.readline, b'\n'):  # get operations
            if operation_name := self.catch_operation_name(line):  # 从一行语句中获得操作
                operation: NARSOperation = NARSOperation(
                    operation_name)  # 从字符串到操作（打包）
                if self.operationHook:  # 若非空
                    self.operationHook(operation)  # 直接传递一个「纳思操作」到指定位置
        out.close()  # 关闭输出流

    def catch_operation_name(self, line: str):
        "从输出的一行（语句）中获取信息，并返回截取到的「操作字符串」"
        pass

    @property
    def num_cached_cmds(self) -> int:
        "返回缓存（待输入进NARS）的命令数量"
        return len(self._cached_cmds)

    def clear_cached_cmds(self) -> None:
        "强制清除命令缓存"
        return self._cached_cmds.clear()

    def async_write_lines(self, stdin):
        "从自身指令缓冲区中读取输入，送入程序的stdin中"
        while self.process != None:  # 始终运行，读取缓冲区中的指令列表
            if self._cached_cmds:
                cmd: str = self._cached_cmds.pop(0)  # 取最开头（）
                self._add_to_cmd(cmd)  # 异步调用（不阻塞主进程）
                if (n_cmds := self.num_cached_cmds) > 0xff:
                    print(
                        f"Warning: The number of cached commands has exceeded the limit with n={n_cmds}!",
                        f'> Last cmd is: {cmd}', sep='\n'
                    )

    # @measure_time
    def write_line(self, cmd: str):
        "缓存命令到缓冲区中"
        DEBUG and print(f'add {cmd} to {self.num_cached_cmds}')
        self._cached_cmds.append(cmd)  # 存入缓冲区
        return  # 代码删除后记：不适宜「对每个输入的语句都开一个新线程」，对系统占用的开销太大

    def _add_to_cmd(self, cmd: str):
        "向命令行添加命令"
        self.process.stdin.write(cmd + '\n')  # TODO：（只能输入单行）主要代码性能卡在这行的执行时间上
        self.process.stdin.flush()
        # print(f'write: {cmd}')

    def add_inference_cycles(self, num: int):
        "推理循环步进"
        self.process.stdin.write(f'{num}\n')
        self.process.stdin.flush()

    def update_inference_cycles(self) -> None:
        "更新自身推理循环"
        if self.inference_cycle_frequency:  # 若大于零
            self.add_inference_cycles(self.inference_cycle_frequency)


class opennars(NARSProgram):
    "Java版实现：OpenNARS"

    DEFAULT_JAR_PATH: str = r'.\opennars.jar'
    "可执行文件路径"

    # 特有语法区 #

    # opennars' grammar（避免百分号歧义）
    PUNISH_TEMPLATE = f'<{NARSProgram._TERM_SELF} --> [%s]>. :|: %%0%%'

    def launch_program(self):
        super().launch_program()
        # OpenNARS的实现
        # self.add_to_cmd('java -Xmx2048m -jar opennars.jar')
        self.write_line(f'java -Xmx1024m -jar {self.jar_path}')

    def __init__(self, jar_path: str = DEFAULT_JAR_PATH):
        self.jar_path = jar_path
        super().__init__(NARSType.OPENNARS)
        self.inference_cycle_frequency = 5

    def catch_operation_name(self, line: str) -> str:
        if line[0:3] == 'EXE':  # 若为操作前缀
            sub_line = line.split(' ', 2)[2]  # 获取EXE后语句
            # print(sub_line) # 操作文本：「EXE ^right([{SELF}])=null」
            return sub_line.split('(', 1)[0][1:]  # 避免'^^opera'


class ONA(NARSProgram):
    "C实现：OpenNARS for Application"

    DEFAULT_EXE_PATH: str = r'.\NAR.exe'
    "可执行文件路径"

    # 特有语法区 #

    # ONA Babble 无效：语句「<(*,{SELF}) --> ^deactivate>. :|:」报错「OSError: [Errno 22] Invalid argument」
    BABBLE_TEMPLATE: str = None

    # ONA's grammar （注：这里使用「{"{0}"}」避免字符串歧义）
    PUNISH_TEMPLATE = f'<{NARSProgram._TERM_SELF} --> [%s]>. :|: {"{0}"}'

    # 操作注册
    OPERATION_REGISTER_TEMPLATE: str = f'(*,{NARSProgram._TERM_SELF}, ^%s). :|:'

    def __init__(self, exe_path: str = DEFAULT_EXE_PATH):
        self.exe_path = exe_path
        super().__init__(NARSType.ONA)
        self.inference_cycle_frequency = 0  # ONA会自主更新

    def launch_program(self):
        super().launch_program()
        # ONA的实现
        self.write_line(f'{self.exe_path} shell')

    def catch_operation_name(self, line: str) -> str:
        if (line[0:1] == '^'):  # 避免在退出游戏时出错
            # print(line) # 操作文本：「EXE ^right executed with args」
            return line.split(' ', 1)[0][1:]  # 避免'^^opera'


"Python实现：NARS Python（WIP）"


class Python(NARSProgram):

    DEFAULT_EXE_PATH: str = r'.\main.exe'
    "程序路径"

    # 特定模板 # 注：NARS-Python 对语句使用圆括号

    SENSE_TEMPLATE: str = '({%s} --> [%s]). :|:'
    '指示「某个对象有某个状态」'

    # 移植自NARS-Pong
    BABBLE_TEMPLATE: str = f'((*, {NARSProgram._TERM_SELF}) --> %s). :|:'
    '指示「自我正在执行某操作」（无意识操作 Babble）'

    # ？是否一定要一个「形容词」？
    GOAL_TEMPLATE: str = f'({NARSProgram._TERM_SELF} --> [%s])! :|:'
    '指示「自我需要达到某个目标」'
    # 语法来自NARS Python
    GOAL_TEMPLATE_NEGATIVE: str = f'({NARSProgram._TERM_SELF} --> (-, [%s]))! :|:'

    PRAISE_TEMPLATE: str = f'({NARSProgram._TERM_SELF} --> [%s]). :|:'
    '指示「某目标被实现」'

    PUNISH_TEMPLATE: str = f'({NARSProgram._TERM_SELF} --> [%s]). :|: %%0.00;0.90%%'
    '指示「某目标未实现」'

    OPERATION_REGISTER_TEMPLATE: str = f'((*, {NARSProgram._TERM_SELF}) --> %s). :|:'

    # 类实现 #

    def __init__(self, exe_path: str = DEFAULT_EXE_PATH):
        self.exe_path = exe_path
        super().__init__(NARSType.ONA)
        self.inference_cycle_frequency = 0  # NARS-Python 不需要更新（暂时只能输入NAL语句）

    def launch_program(self):
        super().launch_program()
        # NARS Python实现
        self.write_line(f'{self.exe_path}')

    def catch_operation_name(self, line: str) -> str:
        if 'reject' in line.lower():
            print(f'Reject: {line}')
        if 'EXE' in line:  # 若为操作前缀
            # print(f'{line}') # 操作文本：「EXE: ^left based on desirability: 0.9」
            return line.split(' ', 2)[1][1:]
