import threading # 用于打开线程
import queue
import subprocess # 用于打开进程
import random # 用于babble
import signal # 用于终止程序

from enum import Enum # 枚举NARS类型

"""抽象出一个「纳思操作」来：记录其名字，并方便语法嵌入
"""
class NARSOperation(): # 现在不需要枚举类
    
    def __init__(self, name:str='') -> None:
        super().__init__()
        self.name = name
        if '^' in name:
            print(f'Warn: mutiple "^" in name of operation {name}')
    
    @property
    def value(self) -> any:
        "获取其值"
        return f'^{self.name}'
    
    def __eq__(self, other: object) -> bool:
        "相等⇔名称相等"
        return self.name == other.name
    
    def __repr__(self) -> str:
        return f"<NARS Operation {self.value}>"
    
    def __str__(self) -> str:
        "字符串就是其值"
        return self.value

class NARSType(Enum):
    
    OPENNARS:str = 'opennars'
    ONA:str = 'ONA'


    """关于NARS功能的接口：抽象于「游戏本体」到「纳思本体」的「中间接口」

    主要功能：
    - 实现一个与「游戏环境」沟通的「通用框架」
        - 注册操作
        - 注册感知
        - 统一管理纳思元素：词项、操作、语句
            - 不随具体实现而变化
    - 将「具体纳思对接」与「通用纳思行动」区分开来
        - 不聚焦具体怎样调用命令
        - 不聚焦如何「注入语句」「获取回应」
    """
class NARSAgent:
    
    # 🆕去硬编码：专门存储NAL语句

    BABBLE_TEMPLETE:str = '<(*,{SELF}) --> %s>. :|:'
    BABBLE_SENTENCE = lambda enumOperation: NARSAgent.BABBLE_TEMPLETE % enumOperation.value
    
    GOAL_TEMPLETE:str = '<{SELF} --> [%s]>! :|:' # ？是否一定要一个「形容词」？
    
    PRAISE_TEMPLETE = '<{SELF} --> [%s]>. :|:'
    
    PUNISH_TEMPLETE = '(--,<{SELF} --> [%s]>). :|:'
    # '<{SELF} --> [good]>. :|: %0%' # opennars' grammar
    # '<{SELF} --> [good]>. :|: {0}' # ONA's grammar
    # 📝不同的NARS实现，可能对「反向真值」有不同的语法
    
    def __init__(self, nars_type:NARSType=None, globalGoal:str = None):  # nars_type: 'opennars' or 'ONA'
        # 🆕使用字典记录操作，并在后面重载「__getitem__」方法实现快捷读写操作
        self._operation_container:dict = dict() # 空字典
        # 定义自身用到的「NARS程序」类型
        self.type:NARSType = nars_type
        # 使用「对象复合」的形式，把「具体程序启动」的部分交给「NARSProgram」处理
        self.brain:NARSProgram = None
        if nars_type: # 🆕若没有输入nars_type，也可以后续再初始化
            self.equip_brain(nars_type)
        # 定义自身的「总目标」
        self.globalGoal:str = globalGoal
    
    @property
    def has_brain_equipped(self):
        "获取自己是否有「初始化大脑」"
        return self.brain == None
    
    @property
    def current_operations(self):
        "获取自己正在进行的操作"
        return self._operation_container.copy() # 一个新字典
    
    def equip_brain(self, nars_type:NARSType): # -> NARSProgram
        "🆕（配合disconnect可重复使用）装载自己的「大脑」：上载一个NARS程序，使得其可以进行推理"
        if self.brain: # 已经「装备」则报错
            raise "Already equipped a program!"
        self.brain:NARSProgram = NARSProgram.fromType(
            type=nars_type
        )
        # 遇到「截获的操作」：直接存储
        self.brain.operationHook = self.store_operation
    
    def disconnect_brain(self):
        "🆕与游戏「解耦」，类似「断开连接」的作用"
        del self.brain # TODO 这里的作用不甚明了……应该是「暂停程序运行」，但实际上「删掉了自己的大脑」
        self.brain = None # 空置，以便下一次定义
    
    def babble(self, probability:int=0, operations=[]):
        "随机行为，就像婴儿的牙牙学语（有概率）" # 🆕为实现「与具体实现程序形式」的分离，直接提升至Agent层次
        if not probability or random.randint(1,probability) == 1: # 几率触发
            # 随机取一个NARS操作
            operation:NARSOperation = random.choice(operations)
            self.put_nal_sentence(NARSAgent.BABBLE_SENTENCE(operation)) # 添加一个Babble
            self.store_operation(operation) # 执行Babble

    def update(self, *args, **kwargs):  # update sensors (object positions), remind goals, and make inference
        "NARS在环境中的行动：感知更新→目标提醒→推理步进"
        self.update_sensors(*args, **kwargs)
        self.put_goal(self.globalGoal) # 原「remind_goal」：时刻提醒智能体要做的事情
        self.inference_step()
    
    def update_sensors(self, *args, **kwargs):
        "留给后续继承"
        pass

    # 语句相关 #
    def put_nal_sentence(self, sentence:str) -> None:
        "🆕通用模块：向NARS体置入一个NAL语句"
        self.brain.add_to_cmd(sentence) # 实际就是向「大脑」注入，不过未来可以进一步拓展
    
    def inference_step(self) -> None:
        "🆕通用模块：让NARS体「思考一个周期」"
        self.brain.update_inference_cycles()
    
    # 目标相关 #
    def put_goal(self, goalName:str):
        "向智能体置入目标（以NAL语句的形式）"
        self.put_nal_sentence(NARSAgent.GOAL_TEMPLETE % goalName)
    
    def praise_goal(self, goalName:str):
        "让智能体感到「目标被实现」，亦即「奖励」"
        self.put_nal_sentence(NARSAgent.PRAISE_TEMPLETE % goalName)
    
    def punish_goal(self, goalName:str):
        "让智能体感到「目标未实现」，亦即「惩罚」"
        self.put_nal_sentence(NARSAgent.PUNISH_TEMPLETE % goalName)
    
    # 操作相关 #
    def __getitem__(self, operation:NARSOperation) -> bool:
        "获取自身「是否要进行某个操作」（返回bool）"
        return self._operation_container.get(operation.name, False) # 默认False
    
    def __setitem__(self, operation:NARSOperation, value:bool):
        "设置自身「需要有哪些操作」"
        self._operation_container[operation.name] = value
    
    def __contains__(self, operation:NARSOperation):
        "获取「操作是否被定义过」"
        return self._operation_container.__contains__(operation.name)
    
    def __iter__(self):
        "枚举自身的「所有操作」"
        return { # 保证遍历出来的是操作（TODO：考虑「是否多余」？）
            name: NARSOperation(name)
            for name in self._operation_container
            }.__iter__() # 返回字典的迭代器
    
    def store_operation(self, operation:NARSOperation):
        "🆕对接命令行与游戏：根据NARS程序返回的操作字符串，执行相应操作"
        self[operation] = True # 直接设置对应「要执行的操作」为真

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
    
    def __init__(self, operationHook=None):
        "初始化NARS程序：启动命令行、连接「NARS计算机实现」、启动线程"
        "推理循环频率"
        self.inference_cycle_frequency:int = 1  # set too large will get delayed and slow down the game
        "🆕存储输出「纳思操作」的钩子：在从命令行读取到操作时，输出到对应函数中"
        self.operationHook = operationHook
        self.launch_nars()
        self.launch_thread()

    # 🆕用析构函数替代「process_kill」方法
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

    def read_line(self, out):  # read line without blocking
        # TODO：这两个命令行函数需要进行「去耦合」：把命令行解析在此处处理，而处理得到的操作暴露给Agent
        "读取程序的（命令行）输出"
        for line in iter(out.readline, b'\n'):  # get operations
            if operation_name := self.catch_operation(line): # 从一行语句中获得操作
                operation:NARSOperation = NARSOperation(operation_name) # 从字符串到操作（打包）
                if self.operationHook: # 若非空
                    self.operationHook(operation) # 直接传递一个「纳思操作」到指定位置
        out.close() # 关闭输出流
    
    def catch_operation(self, line:str):
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

    def catch_operation(self, line:str) -> str:
        if line[0:3] == 'EXE': # 若为操作前缀
            subline = line.split(' ', 2)[2]
            return subline.split('(', 1)[0]

"C实现：OpenNARS for Application"
class ONA(NARSProgram):
    def __init__(self):
        super().__init__(NARSType.ONA)
        self.inference_cycle_frequency = 0
    
    def launch_program(self):
        super().launch_program()
        # 🆕ONA的实现
        self.add_to_cmd('NAR shell')

    def catch_operation(self, line:str) -> str:
        if (line[0:1] == '^'): # 🆕避免在退出游戏时出错
            return line.split(' ', 1)[0][1:] # 避免'^^opera'

# 测试代码
if __name__ == '__main__':
    agent:NARSAgent = NARSAgent(NARSType.OPENNARS)
    agent.put_nal_sentence(NARSAgent.SENSE_ENEMY_LEFT)
    agent.put_nal_sentence(NARSAgent.SENSE_ENEMY_LEFT)
    agent.put_nal_sentence(NARSAgent.SENSE_ENEMY_LEFT)
    agent.put_nal_sentence(NARSAgent.SENSE_ENEMY_LEFT)
    agent.babble() # 🆕1/2的概率babble
    import time
    time.sleep(1)
    for i in range(10):
        agent.update()
    time.sleep(1)
    print(agent._operation_container)
