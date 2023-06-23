#!/usr/bin/python3
# *-* encoding:utf8 *_*

import sys
from game_sprites import *
from NARS import NARSAgent, NARSOperation, NARSType

# 注册游戏事件
CREATE_ENEMY_EVENT = pygame.USEREVENT
UPDATE_NARS_EVENT = pygame.USEREVENT + 1
OPENNARS_BABBLE_EVENT = pygame.USEREVENT + 2
INGAME_CLOCK_EVENT = pygame.USEREVENT + 3 # 游戏内时间计数（速度可调之后）

# 尝试进行数据分析
ENABLE_GAME_DATA_PLOT:bool = False
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    import multiprocessing as mp
    ENABLE_GAME_DATA_PLOT = True
except:
    pass

"""对接游戏：具体的「战机玩家」
原理：使用继承关系，在「一般性的智能体」之上，增加「面向游戏的内容」
"""
class NARSPlanePlayer(NARSAgent):
    
    # 一些内置操作 #
    OPERATION_LEFT:NARSOperation = NARSOperation('left')
    OPERATION_RIGHT:NARSOperation = NARSOperation('right')
    OPERATION_DEACTIVATE:NARSOperation = NARSOperation('deactivate') # 未使用？
    OPERATION_FIRE:NARSOperation = NARSOperation('strike')
    
    BABBLE_OPERATION_LIST:list = [
        OPERATION_LEFT,
        OPERATION_RIGHT,
        OPERATION_DEACTIVATE,
        OPERATION_FIRE
    ]
    
    # NAL词项区 #
    # 去硬编码：专门存储NAL语句（注：此处的时态都是「现在时」）
    
    # 定义目标
    GOAL_GOOD:str = 'good'
    GOAL_BAD:str = 'bad' # 负向目标
    
    # 只需要名字，其会被自动转换为「{对象名}」
    OBJECT_ENEMY:str = 'enemy'
    
    # 只需要名字，其会被自动转换为「[状态名]」
    SENSE_LEFT:str = 'left'
    SENSE_RIGHT:str = 'right'
    SENSE_AHEAD:str = 'ahead'
    
    # 定义新感知
    SENSE_EDGE_LEFT:str = 'edge_left'
    SENSE_EDGE_RIGHT:str = 'edge_right'
    
    SENSE_STILL:str = 'still' # 🆕感知自身运动状态
    SENSE_MOVING_LEFT:str = 'moving_left'
    SENSE_MOVING_RIGHT:str = 'moving_right'
    SENSE_NEARBY:str = 'nearby' # 感知敌机垂直位置
    
    def __init__(self, nars_type: NARSType = None):
        super().__init__(
            nars_type = nars_type,
            mainGoal = NARSPlanePlayer.GOAL_GOOD,
            mainGoal_negative = NARSPlanePlayer.GOAL_BAD
            ) # 目标：「good」
    
    def handle_program_operation(self, operation:NARSOperation):
        # 操作名的「别名分发」
        
        # fire = strike
        if operation.name == 'fire':
            operation = NARSPlanePlayer.OPERATION_FIRE
        
        # 添加操作
        super().handle_program_operation(operation)
        
        # 打印操作以跟踪
        print(operation.value)
    
    def store_operation(self, operation: NARSOperation):
        "重构：处理「冲突的移动方式」"
        super().store_operation(operation)
        
        # 代码功能分离：把剩下的代码看做是某种「冲突」
        if operation == NARSPlanePlayer.OPERATION_LEFT:  # NARS gives <(*,{SELF}) --> ^left>. :|:
            self[NARSPlanePlayer.OPERATION_RIGHT] = False
            # print('move left')
        elif operation == NARSPlanePlayer.OPERATION_RIGHT:  # NARS gives <(*,{SELF}) --> ^right>. :|:
            self[NARSPlanePlayer.OPERATION_LEFT] = False
            # print('move right')
        elif operation == NARSPlanePlayer.OPERATION_DEACTIVATE:  # NARS gives <(*,{SELF}) --> ^deactivate>. :|:
            self[NARSPlanePlayer.OPERATION_LEFT] = False
            self[NARSPlanePlayer.OPERATION_RIGHT] = False
            # print('stay still')
        elif operation == NARSPlanePlayer.OPERATION_FIRE:  # NARS gives <(*,{SELF}) --> ^strike>. :|:
            # print('fire')
            pass
    
    def update_sensors(self, **sense_targets):
        "感知更新部分"
        
        # 获取参数（此处明确「感知」的含义） #
        hero:Hero = sense_targets['hero'] # 自身「英雄」状态
        enemy_group = sense_targets['enemy_group'] # 敌机s
        
        # TODO：将各个「感知模块」抽象出一个「感知目标→感知词项组」的「感知器」类，这样此处只需要遍历感知器并给予其参数
        # for sensor in self.sensors: # 一个智能体有多个「感官/知觉」
        #     senses:list[tuple[str,str]] = sensor(**sense_targets) # 直接把参数分派给各个「sensor函数」，让sensor从中提取「[主语,形容词]」的感知
        #     for obj,adj in senses: # 一个感官可能返回多个「感知语句」
        #         self.add_sense_object(obj,adj) # 统一添加「感知觉」
        
        # 自我感知 

        # 感知自身「是否在边界上」
        if iae:=hero.isAtEdge:
            self.add_sense_self(
                NARSPlanePlayer.SENSE_EDGE_LEFT if iae<0 # 左边界
                else NARSPlanePlayer.SENSE_EDGE_RIGHT #右边界
            )
            # self.punish() # 惩罚效果更差？
            # print(f'at edge {iae}')
            pass
        
        # 🆕速度感：感知自己的运动速度
        
        if hero.isAtEdge or hero.speed == 0: # 因为图形「先移动再约束」的运作方式，边界上的「速度」不为零但确实是停下来的
            self.add_sense_self(NARSPlanePlayer.SENSE_STILL)
        elif hero.speed < 0:
            self.add_sense_self(NARSPlanePlayer.SENSE_LEFT)
        elif hero.speed > 0:
            self.add_sense_self(NARSPlanePlayer.SENSE_MOVING_RIGHT)
        
        # 对敌感知 #
        
        # 敌机（总）方位
        
        # 💭似乎「对每一个敌机进行一次感知」的「基于单个个体的感知」比原来「基于是否有敌机的感知」更能让NARS获得「敌机（大概）在何处」的信息
        # enemy_left = False
        # enemy_right = False
        # enemy_ahead = False
        
        for enemy in enemy_group.sprites():
            # 敌机左右位置感知
            if enemy.rect.right < hero.rect.centerx:
                self.add_sense_object(NARSPlanePlayer.OBJECT_ENEMY, NARSPlanePlayer.SENSE_LEFT)
                # enemy_left = True
            elif hero.rect.centerx < enemy.rect.left:
                self.add_sense_object(NARSPlanePlayer.OBJECT_ENEMY, NARSPlanePlayer.SENSE_RIGHT)
                # enemy_right = True
            else:  # enemy.rect.left <= hero.rect.centerx and hero.rect.centerx <= enemy.rect.right
                self.add_sense_object(NARSPlanePlayer.OBJECT_ENEMY, NARSPlanePlayer.SENSE_AHEAD)
                # enemy_ahead = True
            # 🆕敌机前后位置感知：是否「在旁边」
            if enemy.rect.bottom < hero.rect.top: # 检查是否可能与hero有接触
                self.add_sense_object(NARSPlanePlayer.OBJECT_ENEMY, NARSPlanePlayer.SENSE_NEARBY)
        return
        if enemy_left:
            self.add_sense_object(NARSPlanePlayer.OBJECT_ENEMY,NARSPlanePlayer.SENSE_LEFT)
        if enemy_right:
            self.add_sense_object(NARSPlanePlayer.OBJECT_ENEMY,NARSPlanePlayer.SENSE_RIGHT)
        if enemy_ahead:
            self.add_sense_object(NARSPlanePlayer.OBJECT_ENEMY,NARSPlanePlayer.SENSE_AHEAD)
    
    def handle_operations(self, hero:Hero):
        "分模块：处理NARS发送的操作（返回：是否有操作被执行）"
        # 左右移动：有操作就不撤回（留给先前的「操作冲突」模块）
        if self[NARSPlanePlayer.OPERATION_LEFT]:
            hero.speed = -4
        elif self[NARSPlanePlayer.OPERATION_RIGHT]:
            hero.speed = 4
        else:
            hero.speed = 0
        # 射击：操作后自动重置状态
        if self[NARSPlanePlayer.OPERATION_FIRE]:
            hero.fire()
            self[NARSPlanePlayer.OPERATION_FIRE] = False

    def praise(self):
        "对接游戏：奖励自己"
        self.praise_goal(self.mainGoal)

    def punish(self):
        "对接游戏：惩罚自己"
        # self.punish_goal(self.mainGoal)
        self.praise_goal(self.mainGoal_negative) # 正面目标未实现⇔负面目标实现

class PlaneGame:
    
    @property
    def game_speed(self) -> float:
        "独立出「游戏速度」变量，使其可以和fps一并绑定"
        return self._game_speed
    
    @game_speed.setter
    def game_speed(self, value:float) -> None:
        if value <= 0: # 防止速度下降到非正数
            return
        self._game_speed:float = value
        self.fps:int = int(60 * self._game_speed)
        print(f'game speed = {self.game_speed:.2f}')
        self.__set_timer() # 覆盖之前的定时器
    
    def __init__(self, nars_type:NARSType, game_speed:float = 1.0, enable_punish:bool = False):
        "初始化游戏本体"
        print("Game initialization...")
        pygame.init()
        self.nars_type = nars_type
        self.screen = pygame.display.set_mode(SCREEN_RECT.size)  # create a display surface, SCREEN_RECT.size=(480,700)
        self.clock = pygame.time.Clock()  # create a game clock
        self.font = pygame.font.SysFont('consolas', 18, True)  # display text like scores, times, etc.
        self.__create_sprites()  # sprites initialization
        self.__create_NARS(self.nars_type)
        # 原「__set_timer」被移动到setter内，以便统一修改
        self.game_speed = game_speed  # don't set too large, self.game_speed = 1.0 is the default speed.
        self.auto_speed_delta:float = 0 # 🆕自动加速的加速步进大小
        self.score:int = 0  # hit enemy
        self.speeding_delta_time_s:int = 0 # 现在因「游戏速度」可动态调整，*游戏内*时间需要一个专门的时钟进行评估
        
        # enable to customize whether game punish NARS
        self.enable_punish:bool = enable_punish
        
        self.num_nars_operate:int = 0
        
        # speed melt down mechanism to prevent game stuck
        self.last_display_update_time:int = 0
        self.speed_melt_down:float = 0 # 游戏卡死时暂存的当前速度
        self.num_melt_down_before_restore:int = 0 # 游戏速度在恢复前熔断的次数
        
        # 把数据存在游戏里
        if ENABLE_GAME_DATA_PLOT:
            self.gameDatas:pd.DataFrame = pd.DataFrame(
                [],
                columns=[
                    'ingame_time',
                    'performance',
                    'sense rate',
                    'activation rate',
                ]
            )

    def collectDatas(self) -> None:
        "（同步）获取游戏运行的各项数据"
        self.gameDatas.loc[len(self.gameDatas)] = {
            'ingame_time': self.speeding_delta_time_s, # 游戏内时间
            'performance': self.performance, # 表现
            'sense rate': ( # 每（游戏内）秒送入NARS程序的感知语句数
                self.nars.total_senses / self.speeding_delta_time_s
                if self.speeding_delta_time_s # 避免除以零
                else 0
                ),
            'activation rate': ( # 每（游戏内）秒从NARS程序中送上的操作数
                self.nars.total_operates / self.speeding_delta_time_s
                if self.speeding_delta_time_s # 避免除以零
                else 0
                ),
        }

    def __set_timer(self):
        "设置定时器（用于后面的时序事件）"
        INGAME_CLOCK_EVENT_TIMER = 1000 # 设置「游戏内读秒」时钟
        CREATE_ENEMY_EVENT_TIMER = 1000
        UPDATE_NARS_EVENT_TIMER = 200
        OPENNARS_BABBLE_EVENT_TIMER = 250
        timer_ingame_clock = int(INGAME_CLOCK_EVENT_TIMER / self.game_speed)
        timer_enemy = int(CREATE_ENEMY_EVENT_TIMER / self.game_speed)
        timer_update_NARS = int(UPDATE_NARS_EVENT_TIMER / self.game_speed)
        timer_babble = int(OPENNARS_BABBLE_EVENT_TIMER / self.game_speed)
        pygame.time.set_timer(INGAME_CLOCK_EVENT, timer_ingame_clock)
        pygame.time.set_timer(CREATE_ENEMY_EVENT, timer_enemy)  # the frequency of creating an enemy
        pygame.time.set_timer(UPDATE_NARS_EVENT, timer_update_NARS)  # the activity of NARS
        pygame.time.set_timer(OPENNARS_BABBLE_EVENT, timer_babble)

    def __create_sprites(self):
        "创造图形界面"
        bg1 = Background()
        bg2 = Background(True)
        self.background_group = pygame.sprite.Group(bg1, bg2)
        self.enemy_group = pygame.sprite.Group()
        self.hero = Hero()
        self.hero_group = pygame.sprite.Group(self.hero)

    def __create_NARS(self, type:NARSType):
        "创造NARS（接口）"
        self.nars:NARSPlanePlayer = NARSPlanePlayer(type)
        # 既然在这里就凭借「NARS的程序实现」类型区分「是否babble」，那也不妨把babble看做一个「通用行为」
        self.remaining_babble_times:int = (
            200 if type == NARSType.OPENNARS
            else 0
        )

    def start_game(self):
        "开启游戏"
        print("Game start...")
        self.start_time = pygame.time.get_ticks()
        while True:
            self.__event_handler()
            self.__check_collide()
            self.__update_sprites()
            pygame.display.update()
            self.clock.tick(self.fps)

    def __event_handler(self):
        "处理事件"
        dt:int = self.speeding_delta_time_s - self.last_display_update_time
        # 熔断恢复
        if dt <= 0 and self.speed_melt_down > 0: # 卡顿后恢复
            # 恢复易卡事件
            pygame.event.set_allowed(CREATE_ENEMY_EVENT)
            pygame.event.set_allowed(UPDATE_NARS_EVENT)
            # 恢复速度
            self.game_speed = self.speed_melt_down - 0.1 * self.num_melt_down_before_restore # 在减速中恢复稳态
            print(f'Game stuck restored with speed={self.game_speed}!')
            # 实在没办法时，清理所有敌机
            if self.game_speed <= 0.1:
                self.remove_all_enemy()
            # 重置熔断数据
            self.speed_melt_down = 0
            self.num_melt_down_before_restore = 0
        # 开始处理事件
        for event in pygame.event.get():
            # 游戏退出
            if event.type == pygame.QUIT:
                self.nars.disconnect_brain() # 重定位：从「程序终止」到「断开连接」
                PlaneGame.__game_over()
            # 时钟步进（游戏内时间）
            elif event.type == INGAME_CLOCK_EVENT:
                # 自动加速
                if self.auto_speed_delta:
                    print(f'auto speed up {self.game_speed} --[+{self.auto_speed_delta}]-> {self.game_speed+self.auto_speed_delta}')
                    self.game_speed += self.auto_speed_delta
                # 避免游戏过卡：游戏速率熔断机制
                dt:int = self.speeding_delta_time_s - self.last_display_update_time
                if dt > 0: # 过度迟滞
                    print(f'Game stuck detected with dt={dt} at speed={self.game_speed}!')
                    # 屏蔽易卡事件
                    pygame.event.set_blocked(CREATE_ENEMY_EVENT)
                    pygame.event.set_blocked(UPDATE_NARS_EVENT)
                    # 存储速度
                    if self.speed_melt_down == 0: # 只存储一次
                        self.speed_melt_down = self.game_speed # 熔断-暂存速度
                    # 强制降低游戏速度
                    self.game_speed = 0.1
                    self.num_melt_down_before_restore += 1 # 增加熔断次数
                    # 停止自动加速
                    if self.auto_speed_delta:
                        self.auto_speed_delta = 0
                        print('Automatic acceleration stop.')
                # 时间计数
                self.speeding_delta_time_s += 1
            # 周期性创建敌机
            elif event.type == CREATE_ENEMY_EVENT:
                enemy = Enemy()
                self.enemy_group.add(enemy)
            # NARS 状态更新
            elif event.type == UPDATE_NARS_EVENT:
                self.nars.update(hero=self.hero, enemy_group=self.enemy_group)  # use objects' positions to update NARS's sensors
            # NARS babble
            elif event.type == OPENNARS_BABBLE_EVENT:
                if self.remaining_babble_times <= 0:
                    self.remaining_babble_times = 0 # 重置时间
                    pygame.event.set_blocked(OPENNARS_BABBLE_EVENT)
                else:
                    self.nars.babble(2, NARSPlanePlayer.BABBLE_OPERATION_LIST) # 在指定范围内babble
                    self.remaining_babble_times -= 1
                    print('The remaining babble times: ' + str(self.remaining_babble_times))
            # 键盘按键
            elif event.type == pygame.KEYUP:
                # 左右移动 PartⅡ：停止算法
                if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    self.nars.force_unconscious_operation(NARSPlanePlayer.OPERATION_DEACTIVATE)
            elif event.type == pygame.KEYDOWN:
                key:int = event.key
                key_mods:int = pygame.key.get_mods() # 键盘按键模式检测
                # +/-：调整游戏速度（不影响事件派发？）
                if key == pygame.K_EQUALS: # 是等号键
                    if key_mods & pygame.KMOD_CTRL: # 倍速
                        self.game_speed *= 2
                    elif key_mods & pygame.KMOD_ALT: # 自动加速模块
                        self.auto_speed_delta += 0.1
                        print(f'Automatic acceleration with dv={self.auto_speed_delta}')
                    else:
                        self.game_speed += 0.25
                elif key == pygame.K_MINUS:
                    if key_mods & pygame.KMOD_SHIFT: # 重置速度回1
                        self.game_speed = 1.0
                    elif key_mods & pygame.KMOD_CTRL: # 半速
                        self.game_speed *= 0.5
                    else:
                        self.game_speed -= 0.25 # 有「避免非负机制」
                # C：清除所有敌机
                elif key == pygame.K_c:
                    self.remove_all_enemy()
                # P：展示游戏数据
                elif key == pygame.K_p and ENABLE_GAME_DATA_PLOT:
                    if key_mods & pygame.KMOD_ALT:
                        mp.Process(target=saveDatas, args=(self.gameDatas,)).start()
                    else:
                        mp.Process(target=plotDatas, args=(self.gameDatas,)).start()
                # 左右移动/停止（传入NARS构成BABBLE）
                elif key == pygame.K_LEFT:
                    self.nars.force_unconscious_operation(NARSPlanePlayer.OPERATION_LEFT)
                elif key == pygame.K_RIGHT:
                    self.nars.force_unconscious_operation(NARSPlanePlayer.OPERATION_RIGHT)
                elif key == pygame.K_DOWN:
                    self.nars.force_unconscious_operation(NARSPlanePlayer.OPERATION_DEACTIVATE)
                # U：开关「是否惩罚」
                elif key == pygame.K_u:
                    self.enable_punish ^= True
                    print(f'NARS punishments {"on" if self.enable_punish else "off"}.')
                # G：操作目标
                elif key == pygame.K_g:
                    if key_mods & pygame.KMOD_CTRL: # +Ctrl: 重置目标
                        if key_mods & pygame.KMOD_SHIFT: # +Shift: 重置负向目标
                            self.nars.mainGoal_negative = input(f'Please input a new goal to replace [{self.nars.mainGoal}]: ')
                        else:
                            self.nars.mainGoal = input(f'Please input a new goal to replace [{self.nars.mainGoal}]: ')
                    else:
                        self.nars.put_goal(self.nars.mainGoal)
                        print(f'Current goals: +{self.nars.mainGoal} | -{self.nars.mainGoal_negative}')
                # N：输入NAL语句（不推荐！）
                elif key == pygame.K_n:
                    self.nars.brain.add_to_cmd(input('Please input your NAL sentence(unstable): '))
                # B：添加/移除babble
                elif key == pygame.K_b:
                    if key_mods & pygame.KMOD_ALT: # Alt+B：执行一个babble
                        self.nars.babble(1, NARSPlanePlayer.BABBLE_OPERATION_LIST)
                    else:
                        self.remaining_babble_times += (
                            -10 if key_mods & pygame.KMOD_SHIFT
                            else 10
                            ) # 可以用Shift指定加减
                        if self.remaining_babble_times <= 0:
                            self.remaining_babble_times = 0 # 莫溢出
                        else: # 重新开始监听事件
                            pygame.event.set_allowed(OPENNARS_BABBLE_EVENT)
                # E：开启/关闭NARS的感知/操作
                elif key == pygame.K_e:
                    if key_mods & pygame.KMOD_SHIFT: # 操作
                        self.nars.enable_brain_control ^= True # 异或翻转
                    else: # 感知
                        self.nars.enable_brain_sense ^= True
                # 空格/上：射击
                elif key == pygame.K_SPACE or key == pygame.K_UP:
                    self.nars.force_unconscious_operation(NARSPlanePlayer.OPERATION_FIRE)
        # NARS 执行操作（时序上依赖游戏，而非NARS程序）
        self.nars.handle_operations(self.hero) # 解耦：封装在「NARSPlanePlayer」中
        # 记录游戏数据
        ENABLE_GAME_DATA_PLOT and self.collectDatas()

    def __check_collide(self):
        "检查碰撞"
        # Several collisions may happen at the same time
        collisions = pygame.sprite.groupcollide(self.hero.bullets, self.enemy_group, True,
                                                True)  # collided=pygame.sprite.collide_circle_ratio(0.8)
        if collisions:
            self.score += len(collisions)  # len(collisions) denotes how many collisions happened
            self.nars.praise()
            print("good")
            print('score: ' + str(self.score))

        collisions = pygame.sprite.spritecollide(self.hero, self.enemy_group, True,
                                                 collided=pygame.sprite.collide_circle_ratio(0.7))
        if collisions and self.enable_punish:
            self.score -= len(collisions)
            self.nars.punish()
            print("bad")
            pass
    
    def __update_sprites(self):
        "更新图形"
        self.last_display_update_time = self.speeding_delta_time_s
        self.background_group.update()
        self.background_group.draw(self.screen)
        self.enemy_group.update()
        self.enemy_group.draw(self.screen)
        self.hero_group.update()
        self.hero_group.draw(self.screen)
        self.hero.bullets.update()
        self.hero.bullets.draw(self.screen)
        self.__display_text()

    def remove_all_enemy(self) -> None:
        "🆕移除所有敌机"
        for enemy in self.enemy_group:
            enemy.kill()
        self.enemy_group.empty()
    
    # 游戏信息：使用property封装属性
    @property
    def current_time(self) -> int:
        return pygame.time.get_ticks()
    
    @property
    def delta_time_s(self) -> float:
        "游戏从开始到现在经历的*现实*时间（秒）"
        return (self.current_time - self.start_time) / 1000
    
    @property
    def performance(self) -> float:
        "把「玩家表现」独立出来计算（依附于游戏，而非玩家）"
        return (
            0 if self.speeding_delta_time_s == 0
            else self.score / self.speeding_delta_time_s
        )
    
    def __display_text(self):
        "内部文本内容刷新"

        # 操作
        if self.nars[NARSPlanePlayer.OPERATION_LEFT]:
            operation_text = 'move left'
        elif self.nars[NARSPlanePlayer.OPERATION_RIGHT]:
            operation_text = 'move right'
        else:
            operation_text = 'stay still'

        # 文本
        surface_time = self.font.render('Time(s): %d' % self.speeding_delta_time_s, True, [235, 235, 20])
        surface_performance = self.font.render('Performance: %.3f' % self.performance, True, [235, 235, 20])
        surface_score = self.font.render('Score: %d' % self.score, True, [235, 235, 20])
        surface_fps = self.font.render('FPS: %d' % self.clock.get_fps(), True, [235, 235, 20])
        surface_babbling = self.font.render('Babbling: %d' % self.remaining_babble_times, True, [235, 235, 20])
        surface_nars_type = self.font.render(self.nars_type.value, True, [235, 235, 20])
        surface_version = self.font.render('v2.i', True, [235, 235, 20])
        surface_operation = self.font.render('Operation: %s' % operation_text, True, [235, 235, 20])
        surface_nars_perception_enable = self.font.render(f'NARS Perception: {"on" if self.nars.enable_brain_sense else "off"}', True, [235, 235, 20]) # 指示NARS能否感知
        surface_nars_operation_enable = self.font.render(f'NARS Operation: {"on" if self.nars.enable_brain_control else "off"}', True, [235, 235, 20]) # 指示NARS能否操作
        surface_game_speed = self.font.render('Speed: %.2f' % self.game_speed, True, [235, 235, 20]) # 指示游戏速度
        self.screen.blit(surface_operation, [20, 10])
        self.screen.blit(surface_babbling, [20, 30])
        self.screen.blit(surface_time, [20, 50])
        self.screen.blit(surface_performance, [20, 70])
        self.screen.blit(surface_score, [370, 10])
        self.screen.blit(surface_fps, [370, 30])
        self.screen.blit(surface_game_speed, [370, 50])
        self.screen.blit(surface_nars_type, [5, 680])
        self.screen.blit(surface_version, [435, 680])
        self.screen.blit(surface_nars_perception_enable, [20, 90])
        self.screen.blit(surface_nars_operation_enable, [20, 110])

    @staticmethod
    def __game_over():
        "游戏结束，程序退出"
        print("Game over...")
        exit()

if ENABLE_GAME_DATA_PLOT:
    
    from math import ceil
    def plotDatas(datas:pd.DataFrame):
        "展示游戏数据图表"
        
        # 处理「时间」
        timeSeries = datas['ingame_time']
        # timeSeries = timeSeries[::len(timeSeries)//10+1] # 初次均匀截取十个（暂不需要）
        timeSeries = timeSeries.drop_duplicates() # 丢掉重复值，让「游戏内时间」与索引脱离（开始不均匀）
        timeSeries = timeSeries[::len(timeSeries)//10+1] # 保留最多十个刻度（避免后续刻度太接近）
        timeRange = timeSeries.index # 获取索引值
        # datas = datas.drop(columns='ingame_time') # 去掉「时间数据」
        
        # 规划图表
        num_plots:int = len(datas.columns)
        shape_rows:int = int(num_plots**0.5)
        subplot_shape:tuple[int] = (int(shape_rows), ceil(num_plots / shape_rows)) # 自动计算尺寸
        fig, axes = plt.subplots(*subplot_shape)
        fig.suptitle('Game Datas')
        
        # 绘制图表
        for i, serieName in enumerate(datas.columns):
            ax = axes.flatten()[i] # 铺平，以便于逐个获取（在子图表超过一行时失效）
            # ax.plot(timeSeries,datas[serieName]) # 要求曲线精度够高，横轴坐标还有有可比性意义
            # print(ax,axes,i,datas[serieName],timeSeries)
            datas[serieName].plot(ax=ax)
            ax.set_title(serieName)
            # 🆕设置横轴坐标为「游戏内时间」，并能反映游戏速度的变化
            
            ax.set_xticks(timeRange) # 反映「游戏内时间到t时被记录到的索引值」
            ax.set_xticklabels(timeSeries)
            ax.set_xlabel('time')

        plt.tight_layout()
        plt.show()
    
    DATA_FILE_NAME = 'game_datas.xlsx'
    def saveDatas(datas:pd.DataFrame):
        "存储游戏数据到excel文件"
        datas.to_excel(DATA_FILE_NAME)
        print(f'Game datas are exported to {DATA_FILE_NAME}.')


if __name__ == '__main__':
    #game = PlaneGame('opennars')  # input 'ONA' or 'opennars'
    # 可选参数
    nars_type:NARSType = (
        NARSType(sys.argv[1]) if len(sys.argv)>1
        else NARSType(type)
        if (type:=input("Please input the type of NARS(opennars(default)/ONA): "))
        else NARSType.OPENNARS
    )
    game_speed:float = float(
        sys.argv[2] if len(sys.argv)>2
        else speed
        if (speed:=input("Please input game speed(default 1.0): "))
        else 1.0
    )
    enable_punish:bool = bool(
        sys.argv[3] if len(sys.argv)>3
        else input("Please input whether you want to punish NARS(empty for False): ")
    )
    game = PlaneGame(
        nars_type = nars_type, 
        game_speed = game_speed, 
        enable_punish = enable_punish, 
    )
    game.start_game()
    
