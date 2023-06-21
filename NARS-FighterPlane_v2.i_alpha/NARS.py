import threading
import queue
import subprocess
import random
import signal

from enum import Enum # 🆕使用枚举类

from game_sprites import Hero, Enemy # 🆕具身AI必须知道自身与外界的信息

class NARSOperation(Enum):
    
    LEFT:str = '^left'
    RIGHT:str = '^right'
    DEACTIVATE:str = '^deactivate' # 未使用？
    FIRE:str = '^strike'

"起因是要处理在ONA中出现「^fire」而无法匹配的错误"
def get_operation_from_str(type:str) -> NARSOperation:
    if type in SPECIAL_OPERATION_DICT: # 先处理特殊情况
        return SPECIAL_OPERATION_DICT[type]
    return NARSOperation._value2member_map_.get(type) # 从「_value2member_map_」中获取数据（不会报错）

SPECIAL_OPERATION_DICT: dict = {
    '^fire': NARSOperation.FIRE, # 特殊
}

class NARSType(Enum):
    
    OPENNARS:str = 'opennars'
    ONA:str = 'ONA'


class NARS:
    
    # 🆕去硬编码：专门存储NAL语句
    
    SENSE_ENEMY_LEFT:str = '<{enemy} --> [left]>. :|:'
    SENSE_ENEMY_RIGHT:str = '<{enemy} --> [right]>. :|:'
    SENSE_ENEMY_AHEAD:str = '<{enemy} --> [ahead]>. :|:'

    BABBLE_TEMPLETE:str = '<(*,{SELF}) --> %s>. :|:'
    BABBLE_SENTENCE = lambda enumOperation: NARS.BABBLE_TEMPLETE % enumOperation.value
    
    GOAL_GOOD:str = '<{SELF} --> [good]>! :|:'
    
    PRAISE_GOOD:str = '<{SELF} --> [good]>. :|:'
    PUNISH_GOOD:str = '(--,<{SELF} --> [good]>). :|:'
    # '<{SELF} --> [good]>. :|: %0%' # opennars' grammar
    # '<{SELF} --> [good]>. :|: {0}' # ONA's grammar
    # 📝不同的NARS实现，可能对「反向真值」有不同的语法
    
    # 🆕定义新感知
    SENSE_SELF_EDGE_LEFT:str = '<{SELF} --> [edge_left]>. :|:'
    SENSE_SELF_EDGE_RIGHT:str = '<{SELF} --> [edge_right]>. :|:'
    
    @staticmethod
    def create(type:NARSType):
        if type == NARSType.OPENNARS:
            return opennars()
        if type == NARSType.ONA:
            return ONA()
    
    def __init__(self, nars_type:NARSType):  # nars_type: 'opennars' or 'ONA'
        self.inference_cycle_frequency = 1  # set too large will get delayed and slow down the game
        # 🆕使用字典记录操作，并在后面重载「__getitem__」方法实现快捷读写操作
        self._operation_container:dict = {
            key:False
            for key in NARSOperation # 只对已存在的操作进行定义
        }
        self.type = nars_type
        self.launch_nars()
        self.launch_thread()

    def launch_nars(self):
        "使用cmd打开子进程，并根据NARS类型启动对应程序"
        self.process = subprocess.Popen(["cmd"], bufsize=1,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        universal_newlines=True,  # convert bytes to text/string
                                        shell=False)
        if self.type == NARSType.OPENNARS:
            self.add_to_cmd('java -Xmx1024m -jar opennars.jar')  # self.add_to_cmd('java -Xmx2048m -jar opennars.jar')
        elif self.type == NARSType.ONA:
            self.add_to_cmd('NAR shell')
        self.add_to_cmd('*volume=0')

    def launch_thread(self):
        "开启子线程，负责对NARS程序的读写工作"
        self.read_line_thread = threading.Thread(target=self.read_line,
                                                 args=(self.process.stdout,))
        self.read_line_thread.daemon = True  # thread dies with the exit of the program
        self.read_line_thread.start()

    def read_line(self, out):  # read line without blocking
        "读取程序的（命令行）输出"
        for line in iter(out.readline, b'\n'):  # get operations
            if operation_str := self.catch_operation(line): # 从一行语句中获得操作
                operation:NARSOperation = get_operation_from_str(operation_str) # 从字符串到枚举
                if operation:
                    self.execute_operation(operation)
                else:
                    print(f'Unregistered operation {operation_str}')
        out.close() # 关闭输出流
    
    def catch_operation(self, line:str):
        "从输出的一行（语句）中获取信息，并返回截取到的「操作字符串」"
        pass

    def process_kill(self):
        "程序结束时，自动终止NARS"
        self.process.send_signal(signal.CTRL_C_EVENT)
        self.process.terminate()

    def babble(self):
        pass

    def add_to_cmd(self, str):
        "向命令行添加命令"
        self.process.stdin.write(str + '\n')
        self.process.stdin.flush()

    def add_inference_cycles(self, num):
        "推理循环步进"
        self.process.stdin.write(f'{num}\n')
        self.process.stdin.flush()

    def update(self, hero, enemy_group):  # update sensors (object positions), remind goals, and make inference
        "NARS在环境中的行动：感知更新→目标提醒→推理步进"
        self.update_sensors(hero, enemy_group)
        self.remind_goal()
        self.add_inference_cycles(self.inference_cycle_frequency)

    def __getitem__(self, operation):
        return self._operation_container.get(operation)
    
    def __setitem__(self, operation, value):
        self._operation_container[operation] = value
    
    def update_sensors(self, hero:Hero, enemy_group):
        "感知更新部分"
        
        # 自我感知

        # 感知自身「是否在边界上」
        if iae:=hero.isAtEdge:
            self.add_to_cmd(
                NARS.SENSE_SELF_EDGE_LEFT if iae<0 # 左边界
                else NARS.SENSE_SELF_EDGE_RIGHT #右边界
            )
            # self.punish() # 惩罚效果更差？
            # print(f'at edge {iae}')
            pass
        
        # 对敌感知
        
        # 💭似乎「对每一个敌机进行一次感知」的「基于单个个体的感知」比原来「基于是否有敌机的感知」更能让NARS获得「敌机（大概）在何处」的信息
        # enemy_left = False
        # enemy_right = False
        # enemy_ahead = False
        
        for enemy in enemy_group.sprites():
            if enemy.rect.right < hero.rect.centerx:
                self.add_to_cmd(NARS.SENSE_ENEMY_LEFT)
                # enemy_left = True
            elif hero.rect.centerx < enemy.rect.left:
                self.add_to_cmd(NARS.SENSE_ENEMY_RIGHT)
                # enemy_right = True
            else:  # enemy.rect.left <= hero.rect.centerx and hero.rect.centerx <= enemy.rect.right
                self.add_to_cmd(NARS.SENSE_ENEMY_AHEAD)
                # enemy_ahead = True
        return
        if enemy_left:
            self.add_to_cmd(NARS.SENSE_ENEMY_LEFT)
        if enemy_right:
            self.add_to_cmd(NARS.SENSE_ENEMY_RIGHT)
        if enemy_ahead:
            self.add_to_cmd(NARS.SENSE_ENEMY_AHEAD)

    def execute_operation(self, operation:NARSOperation):
        "🆕对接命令行与游戏：根据NARS程序返回的操作字符串，执行相应操作"
        
        if operation == NARSOperation.LEFT:  # NARS gives <(*,{SELF}) --> ^left>. :|:
            self[NARSOperation.LEFT] = True
            self[NARSOperation.RIGHT] = False
            print('move left')
        elif operation == NARSOperation.RIGHT:  # NARS gives <(*,{SELF}) --> ^right>. :|:
            self[NARSOperation.LEFT] = False
            self[NARSOperation.RIGHT] = True
            print('move right')
        elif operation == NARSOperation.DEACTIVATE:  # NARS gives <(*,{SELF}) --> ^deactivate>. :|:
            self[NARSOperation.LEFT] = False
            self[NARSOperation.RIGHT] = False
            print('stay still')
        elif operation == NARSOperation.FIRE:  # NARS gives <(*,{SELF}) --> ^strike>. :|:
            self[NARSOperation.FIRE] = True
            print('fire')

    def remind_goal(self):
        self.add_to_cmd(NARS.GOAL_GOOD)

    def praise(self):
        self.add_to_cmd(NARS.PRAISE_GOOD)

    def punish(self):
        self.add_to_cmd(NARS.PUNISH_GOOD)


class opennars(NARS):
    def __init__(self):
        super().__init__(NARSType.OPENNARS)
        self.inference_cycle_frequency = 5

    def babble(self):
        if random.randint(1,2) == 1: # 1/2 几率触发
            # 随机取一个NARS操作
            operation:NARSOperation = random.choice(list(NARSOperation))
            self.add_to_cmd(NARS.BABBLE_SENTENCE(operation)) # 添加一个Babble
            self.execute_operation(operation) # 执行Babble

    def catch_operation(self, line:str) -> str:
        if line[0:3] == 'EXE': # 若为操作前缀
            subline = line.split(' ', 2)[2]
            return subline.split('(', 1)[0]


class ONA(NARS):
    def __init__(self):
        super().__init__(NARSType.ONA)
        self.inference_cycle_frequency = 0

    def catch_operation(self, line:str) -> str:
        if (line[0:1] == '^'): # 🆕避免在退出游戏时出错
            return line.split(' ', 1)[0]
            
