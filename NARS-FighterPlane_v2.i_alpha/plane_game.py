#!/usr/bin/python3
# *-* encoding:utf8 *_*

import sys
from game_sprites import *
from NARS import *

CREATE_ENEMY_EVENT = pygame.USEREVENT
UPDATE_NARS_EVENT = pygame.USEREVENT + 1
OPENNARS_BABBLE_EVENT = pygame.USEREVENT + 2

# 🆕尝试进行数据分析
ENABLE_PERFORMANCE_PLOT:bool = False
try:
    import matplotlib.pyplot as plt
    import multiprocessing as mp
    ENABLE_PERFORMANCE_PLOT = True
    datas:list = []
except:
    pass

class PlaneGame:
    def __init__(self, nars_type:NARSType, game_speed:float = 1.0, enable_punish:bool = False):
        "初始化游戏本体"
        print("Game initialization...")
        pygame.init()
        self.game_speed = game_speed  # don't set too large, self.game_speed = 1.0 is the default speed.
        self.fps = 60 * self.game_speed
        self.nars_type = nars_type
        self.screen = pygame.display.set_mode(SCREEN_RECT.size)  # create a display surface, SCREEN_RECT.size=(480,700)
        self.clock = pygame.time.Clock()  # create a game clock
        self.font = pygame.font.SysFont('consolas', 18, True)  # display text like scores, times, etc.
        self.__create_sprites()  # sprites initialization
        self.__create_NARS(self.nars_type)
        self.__set_timer()
        self.score = 0  # hit enemy
        
        self.enable_punish = enable_punish # 🆕enable to customize whether game punish NARS

    def __set_timer(self):
        "设置定时器（用于后面的时序事件）"
        CREATE_ENEMY_EVENT_TIMER = 1000
        UPDATE_NARS_EVENT_TIMER = 200
        OPENNARS_BABBLE_EVENT_TIMER = 250
        timer_enemy = int(CREATE_ENEMY_EVENT_TIMER / self.game_speed)
        timer_update_NARS = int(UPDATE_NARS_EVENT_TIMER / self.game_speed)
        timer_babble = int(OPENNARS_BABBLE_EVENT_TIMER / self.game_speed)
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
        self.nars = NARS.create(type)
        self.remaining_babble_times = (
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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.nars.process_kill()
                PlaneGame.__game_over()
            # 🆕按键展示数据
            elif event.type == pygame.KEYDOWN:
                if ENABLE_PERFORMANCE_PLOT: #event.unicode == 'P' and 
                    mp.Process(target=plotDatas, args=(datas,)).start()
            elif event.type == CREATE_ENEMY_EVENT:
                enemy = Enemy()
                self.enemy_group.add(enemy)
            elif event.type == UPDATE_NARS_EVENT:
                self.nars.update(self.hero, self.enemy_group)  # use objects' positions to update NARS's sensors
            elif event.type == OPENNARS_BABBLE_EVENT:
                if self.remaining_babble_times == 0:
                    pygame.event.set_blocked(OPENNARS_BABBLE_EVENT)
                else:
                    self.nars.babble()
                    self.remaining_babble_times -= 1
                    print('The remaining babble times: ' + str(self.remaining_babble_times))
        self.__handle_NARS_operations()
        
    def __handle_NARS_operations(self):
        "🆕分模块：处理NARS发送的操作"
        if self.nars[NARSOperation.LEFT]:
            self.hero.speed = -4
        elif self.nars[NARSOperation.RIGHT]:
            self.hero.speed = 4
        else:
            self.hero.speed = 0
        if self.nars[NARSOperation.FIRE]:
            self.hero.fire()
            self.nars[NARSOperation.FIRE] = False

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
        self.background_group.update()
        self.background_group.draw(self.screen)
        self.enemy_group.update()
        self.enemy_group.draw(self.screen)
        self.hero_group.update()
        self.hero_group.draw(self.screen)
        self.hero.bullets.update()
        self.hero.bullets.draw(self.screen)
        self.__display_text()

    def __display_text(self):
        "内部文本内容刷新"
        current_time = pygame.time.get_ticks()
        delta_time_s = (current_time - self.start_time) / 1000
        speeding_delta_time_s = delta_time_s * self.game_speed

        # 表现
        if delta_time_s == 0:
            performance = 0
        else:
            performance = self.score / speeding_delta_time_s
        # 🆕记录历史
        if ENABLE_PERFORMANCE_PLOT:
            global datas
            datas.append(performance)

        # 操作
        if self.nars[NARSOperation.LEFT]:
            operation_text = 'move left'
        elif self.nars[NARSOperation.RIGHT]:
            operation_text = 'move right'
        else:
            operation_text = 'stay still'

        # 文本
        surface_time = self.font.render('Time(s): %d' % speeding_delta_time_s, True, [235, 235, 20])
        surface_performance = self.font.render('Performance: %.3f' % performance, True, [235, 235, 20])
        surface_score = self.font.render('Score: %d' % self.score, True, [235, 235, 20])
        surface_fps = self.font.render('FPS: %d' % self.clock.get_fps(), True, [235, 235, 20])
        surface_babbling = self.font.render('Babbling: %d' % self.remaining_babble_times, True, [235, 235, 20])
        surface_nars_type = self.font.render(self.nars_type.value, True, [235, 235, 20])
        surface_version = self.font.render('v1.0', True, [235, 235, 20])
        surface_operation = self.font.render('Operation: %s' % operation_text, True, [235, 235, 20])
        self.screen.blit(surface_operation, [20, 10])
        self.screen.blit(surface_babbling, [20, 30])
        self.screen.blit(surface_time, [20, 50])
        self.screen.blit(surface_performance, [20, 70])
        self.screen.blit(surface_score, [370, 10])
        self.screen.blit(surface_fps, [370, 30])
        self.screen.blit(surface_nars_type, [5, 680])
        self.screen.blit(surface_version, [435, 680])

    @staticmethod
    def __game_over():
        "游戏结束，程序退出"
        print("Game over...")
        exit()

def plotDatas(datas):
    "🆕展示游戏图表"
    plt.plot(datas)
    plt.show()

if __name__ == '__main__':
    #game = PlaneGame('opennars')  # input 'ONA' or 'opennars'
    # 🆕可选参数
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
    
