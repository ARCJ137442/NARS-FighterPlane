import random # 用于babble

"""抽象出一个「纳思操作」来
主要功能：记录其名字，并方便语法嵌入
TODO 后续可扩展：操作参数
"""
class NARSOperation(): # 现在不需要枚举类
    
    def __init__(self, name:str='') -> None:
        # 警惕「忘去除前缀」的现象
        if name[0] == '^':
            self.name = name[1:] # 去头
            print(f'Warning: mutiple "^" in name of operation {name}')
        else: # 否则默认设置
            self.name = name
    
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

"""抽象出一个「NARS感知」出来
主要功能：作为NARS感知的处理单位
- 记录其「主语」「表语」
"""
class NARSPerception(): # 现在不需要枚举类
    
    def __init__(self, objective:str, adjective:str) -> None:
        self.object:str = objective
        self.adjective:str = adjective
    
    def __eq__(self, other) -> bool:
        "相等⇔名称相等"
        return (
            self.object == other.objective
            and self.adjective == other.adjective
        )
    
    def __repr__(self) -> str:
        return "<NARS Perception: {%s} --> [%s] >" % (self.object, self.adjective)
    
    def __str__(self) -> str:
        "字符串就是其「语句」（一般NAL语法）"
        return "<{%s} --> [%s]>." % (self.object, self.adjective)
    

# 避免循环导入
from NARS_Program import NARSType, NARSProgram

"""关于NARS功能的接口：抽象于「游戏本体」到「纳思本体」的「中间接口」

主要功能：
- 实现一个与「游戏环境」沟通的「通用框架」
    - 注册操作
    - 注册感知
    - 统一管理纳思元素：词项、操作、语句
        - 不随具体实现而变化
        - TODO：下放「具体NAL模板」到各自的NARS程序实现中
- 将「具体纳思对接」与「通用纳思行动」区分开来
    - 不聚焦具体怎样调用命令
    - 不聚焦如何「注入语句」「获取回应」
"""
class NARSAgent:
    
    # NAL内置对象区 #
    
    '表示「自我」的对象'
    OBJECT_SELF:str = 'SELF'
    SELF:str = '{%s}' % OBJECT_SELF # 嵌入「自我」词项（必须是{专名}的形式）
    
    # NAL语句模板区 #

    '指示「自我正在执行某操作」'
    BABBLE_TEMPLETE:str = f'<(*,{SELF}) --> %s>. :|:'
    
    '指示「某个对象有某个状态」'
    SENSE_TEMPLETE:str = '<{%s} --> [%s]>. :|:'
    
    '指示「自我需要达到某个目标」'
    GOAL_TEMPLETE:str = f'<{SELF} --> [%s]>! :|:' # ？是否一定要一个「形容词」？
    GOAL_TEMPLETE_NEGATIVE:str = f'(--, <{SELF} --> [%s]>)! :|:' # 一个「负向目标」，指导「实现其反面」
    
    '指示「某目标被实现」'
    PRAISE_TEMPLETE = f'<{SELF} --> [%s]>. :|:'
    
    '指示「某目标未实现」'
    PUNISH_TEMPLETE = f'(--,<{SELF} --> [%s]>). :|:'
    # '<{SELF} --> [good]>. :|: %0%' # opennars' grammar
    # '<{SELF} --> [good]>. :|: {0}' # ONA's grammar
    # 📝不同的NARS实现，可能对「反向真值」有不同的语法
    
    def __init__(self, nars_type:NARSType=None, mainGoal:str = None, mainGoal_negative:str = None):  # nars_type: 'opennars' or 'ONA'
        # 🆕使用字典记录操作，并在后面重载「__getitem__」方法实现快捷读写操作
        self._operation_container:dict[NARSOperation:bool] = dict() # 空字典
        # 使用「对象复合」的形式，把「具体程序启动」的部分交给「NARSProgram」处理
        self.brain:NARSProgram = None
        self.enable_brain_control:bool = True # 决定是否「接收NARS操作」
        self.enable_brain_sense:bool = True # 决定是否「接收外界感知」
        if nars_type: # 🆕若没有输入nars_type，也可以后续再初始化
            self.equip_brain(nars_type)
        # 定义自身的「总目标」
        self.mainGoal:str = mainGoal
        self.mainGoal_negative:str = mainGoal_negative
        # 感知相关
        self._total_sense_inputs:int = 0 # 从外界获得的感知输入量
        # 操作相关
        self._total_initiative_operates:int = 0 # 从NARS程序接收的操作总数
    
    # 程序实现相关 #
    
    @property
    def has_brain_equipped(self):
        "获取自己是否有「初始化大脑」"
        return self.brain != None
    
    def equip_brain(self, nars_type:NARSType): # -> NARSProgram
        "🆕（配合disconnect可重复使用）装载自己的「大脑」：上载一个NARS程序，使得其可以进行推理"
        # 定义自身用到的「NARS程序」类型
        self.type:NARSType = nars_type
        if self.brain: # 已经「装备」则报错
            raise "Already equipped a program!"
        self.brain:NARSProgram = NARSProgram.fromType(
            type=nars_type
        )
        # 遇到「截获的操作」：交给专门函数处理
        self.brain.operationHook = self.handle_program_operation
    
    def disconnect_brain(self):
        "🆕与游戏「解耦」，类似「断开连接」的作用"
        del self.brain # TODO 这里的作用不甚明了……应该是「暂停程序运行」，但实际上「删掉了自己的大脑」
        self.brain = None # 空置，以便下一次定义
    
    def babble(self, probability:int=1, operations=[]):
        "随机行为，就像婴儿的牙牙学语（有概率）" # 🆕为实现「与具体实现程序形式」的分离，直接提升至Agent层次
        if not probability or random.randint(1,probability) == 1: # 几率触发
            # 随机取一个NARS操作
            operation:NARSOperation = random.choice(operations)
            self.force_unconscious_operation(operation) # 相当于「强制无意识操作」

    def update(self, *args, **kwargs):  # update sensors (object positions), remind goals, and make inference
        "NARS在环境中的行动：感知更新→目标提醒→推理步进"
        self.update_sensors(*args, **kwargs)
        self.put_goal(self.mainGoal) # 原「remind_goal」：时刻提醒智能体要做的事情
        self.put_goal(self.mainGoal_negative, True) # 🆕时刻提醒智能体*不要做*的事情
        self._inference_step()
    
    # 语句相关 #
    def _put_nal_sentence(self, sentence:str) -> None:
        "🆕通用模块：向NARS体置入一个NAL语句（不建议直接使用）"
        self.brain.add_to_cmd(sentence) # 实际就是向「大脑」注入，不过未来可以进一步拓展
    
    def _inference_step(self) -> None:
        "🆕通用模块：让NARS体「思考一个周期」"
        self.brain.update_inference_cycles()
    
    # 感知相关 #
    def update_sensors(self, *args, **kwargs):
        "留给后续继承"
        pass
    
    def add_sense(self, perception:NARSPerception) -> None:
        return self.add_sense_object(perception)
    
    def add_sense_object(self, objectName:str, stateName:str) -> None:
        "🆕统一添加感知"
        if not self.enable_brain_sense: # 若没「启用大脑感知」，直接返回
            return
        self._put_nal_sentence(NARSAgent.SENSE_TEMPLETE % (objectName, stateName)) # 套模板
        self._total_sense_inputs += 1 # 计数
    
    def add_sense_self(self, stateName:str) -> None:
        "添加自我感知"
        return self.add_sense_object(objectName=NARSAgent.OBJECT_SELF, stateName=stateName)

    @property
    def total_senses(self) -> int:
        "获取从外界获得的感知次数"
        return self._total_sense_inputs
    
    # 目标相关 #
    def put_goal(self, goalName:str, is_negative:bool = False):
        "向智能体置入目标（以NAL语句的形式）"
        self._put_nal_sentence(
            (
                NARSAgent.GOAL_TEMPLETE_NEGATIVE
                if is_negative
                else NARSAgent.GOAL_TEMPLETE
            ) % goalName
        )
    
    def praise_goal(self, goalName:str):
        "让智能体感到「目标被实现」，亦即「奖励」"
        self._put_nal_sentence(NARSAgent.PRAISE_TEMPLETE % goalName)
    
    def punish_goal(self, goalName:str):
        "让智能体感到「目标未实现」，亦即「惩罚」"
        self._put_nal_sentence(NARSAgent.PUNISH_TEMPLETE % goalName)
    
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
    
    def force_unconscious_operation(self, operation:NARSOperation):
        "强制「无意识操作」：让智能体执行，仅告诉NARS程序「我执行了这个操作」"
        # TODO 问题：这样的语句对ONA不起效（输入后程序报错，游戏闪退），可能是「不同程序实现」的语法问题（是否要分离到具体的Program？）
        if self.type != NARSType.ONA: # ONA无效：语句「<(*,{SELF}) --> ^deactivate>. :|:」报错「OSError: [Errno 22] Invalid argument」
            self._put_nal_sentence(NARSAgent.BABBLE_TEMPLETE % operation.value) # 置入「自己在进行什么操作」
        self.store_operation(operation) # 智能体：执行操作
    
    def store_operation(self, operation:NARSOperation):
        "存储对应操作，更新自身状态"
        self[operation] = True # 直接设置对应「要执行的操作」为真
    
    def handle_program_operation(self, operation:NARSOperation):
        "对接命令行与游戏：根据NARS程序返回的操作字符串，存储相应操作"
        if not self.enable_brain_control: # 若没「启用大脑操作」，直接返回
            return
        self.store_operation(operation) # 存储操作
        self._total_initiative_operates += 1 # 增加接收的操作次数
    
    @property
    def stored_operation_names(self) -> dict[NARSOperation:bool]:
        "获取自己存储的操作字典（复制新对象）"
        return self._operation_container.copy() # 一个新字典
    
    @property
    def stored_operation_names(self) -> dict[NARSOperation:bool]:
        "获取自己存储的所有操作名（迭代器）"
        return self._operation_container.keys() # 一个新字典
    
    @property
    def active_operations(self):
        "获取被激活的操作（迭代器）"
        return (
            operation
            for operation,isActive in self._operation_container.items()
            if isActive
        )
    
    @property
    def total_operates(self) -> int:
        "获取从「NARS计算机实现」中截获的操作次数"
        return self._total_initiative_operates
