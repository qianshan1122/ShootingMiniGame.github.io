import pygame
import random
import sys
import os
import cv2
import mediapipe as mp
import math

# 初始化pygame和mediapipe
pygame.init()
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7)
cap = cv2.VideoCapture(0)

# 屏幕设置
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("枪战小游戏")

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# 游戏区域划分
GAME_WIDTH = 800
game_area = pygame.Rect(0, 0, GAME_WIDTH, SCREEN_HEIGHT)
camera_area = pygame.Rect(GAME_WIDTH, 0, SCREEN_WIDTH - GAME_WIDTH, SCREEN_HEIGHT)

# 玩家类
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # 加载玩家图片
        try:
            img_path = os.path.join(os.path.dirname(__file__), "image", "people.png")
            if os.path.exists(img_path):
                self.image = pygame.image.load(img_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (40, 40))
            else:
                raise FileNotFoundError("找不到玩家图片")
        except Exception as e:
            print(f"加载玩家图片失败: {e}")
            # 回退到纯色方块
            self.image = pygame.Surface((40, 40))
            self.image.fill(GREEN)
            
        self.rect = self.image.get_rect()
        # 确保初始位置在边界内
        # 设置初始位置在左上角安全区域
        self.rect.x = 100
        self.rect.y = 100
        # 确保不超出边界
        self.rect.x = max(0, min(GAME_WIDTH - self.rect.width, self.rect.x))
        self.rect.y = max(0, min(SCREEN_HEIGHT - self.rect.height, self.rect.y))
        self.speed = 8  # 调整为适中速度
        self.health = 100
        self.weapon = "手枪"  # 初始武器
        
    def handle_movement(self, obstacles, direction=None):
        moved = False
        
        # 独立计算x和y方向移动
        dx, dy = 0, 0
        if direction == "LEFT": dx = -self.speed
        elif direction == "RIGHT": dx = self.speed
        elif direction == "UP": dy = -self.speed
        elif direction == "DOWN": dy = self.speed
        
        # 计算新位置
        new_x = self.rect.x + dx
        new_y = self.rect.y + dy
        
        # 边界检查
        new_x = max(0, min(GAME_WIDTH - self.rect.width, new_x))
        new_y = max(0, min(SCREEN_HEIGHT - self.rect.height, new_y))
        
        # 保存原始位置
        old_x, old_y = self.rect.x, self.rect.y
        
        # 临时移动角色进行碰撞检测
        self.rect.x = new_x
        self.rect.y = new_y
        
        # 检测与墙体的碰撞
        wall_collisions = pygame.sprite.spritecollide(self, obstacles, False)
        for wall in wall_collisions:
            if isinstance(wall, Wall):  # 只检测墙体碰撞
                # 碰撞后回退到原位置
                self.rect.x = old_x
                self.rect.y = old_y
                moved = False
                break
        else:
            moved = True
            # print(f"Player moved to: {self.rect.x}, {self.rect.y}")
            
        return moved
            
        return moved

# 死亡特效类
class DeathEffect(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.particles = []
        # 创建8个方向的粒子
        for i in range(8):
            angle = random.uniform(0, math.pi*2)
            speed = random.uniform(1, 3)
            self.particles.append({
                'x': x,
                'y': y,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'life': 30,
                'color': (random.randint(200,255), random.randint(100,150), 0)
            })
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        
    def update(self):
        # 更新所有粒子
        for p in self.particles:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['life'] -= 1
            
        # 移除生命周期结束的特效
        if all(p['life'] <= 0 for p in self.particles):
            self.kill()
            
    def draw(self, surface):
        # 绘制所有粒子
        for p in self.particles:
            if p['life'] > 0:
                pygame.draw.circle(
                    surface, 
                    p['color'],
                    (int(p['x']), int(p['y'])),
                    max(1, int(p['life']/10))
                )

# 子弹类
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((10, 5))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 10
        self.direction = 1  # 1表示向右
        
    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.left > GAME_WIDTH or self.rect.right < 0:
            self.kill()

# 障碍物基类
class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# 墙类
class Wall(Obstacle):
    def __init__(self, x, y):
        super().__init__(x, y, 50, 50, (100, 100, 100))

# 水坑类
class Water(Obstacle):
    def __init__(self, x, y):
        super().__init__(x, y, 60, 60, BLUE)
        self.damage_timer = 0

# 火坑类
class Fire(Obstacle):
    def __init__(self, x, y):
        super().__init__(x, y, 60, 60, RED)
        self.damage_timer = 0

# 武器类
class Weapon(pygame.sprite.Sprite):
    def __init__(self, weapon_type):
        super().__init__()
        self.type = weapon_type
        if weapon_type == "手枪":
            self.image = pygame.Surface((20, 10))
            self.image.fill(WHITE)
            self.damage = 1
            self.fire_rate = 1.0
        elif weapon_type == "步枪":
            self.image = pygame.Surface((25, 8))
            self.image.fill((200, 200, 0))
            self.damage = 2
            self.fire_rate = 0.5
        elif weapon_type == "霰弹枪":
            self.image = pygame.Surface((30, 15))
            self.image.fill((255, 165, 0))
            self.damage = 3
            self.fire_rate = 1.5
        
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, GAME_WIDTH - 30)
        self.rect.y = random.randint(0, SCREEN_HEIGHT - 30)
        self.spawn_time = pygame.time.get_ticks()

# 敌人类
class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        try:
            img_path = os.path.join(os.path.dirname(__file__), "image", "enemy.png")
            if os.path.exists(img_path):
                original_image = pygame.image.load(img_path).convert_alpha()
                self.image = pygame.transform.scale(original_image, (30, 30))
            else:
                raise FileNotFoundError("找不到敌人图片")
        except Exception as e:
            print(f"加载敌人图片失败: {e}")
            self.image = pygame.Surface((30, 30))
            self.image.fill(RED)
            
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, GAME_WIDTH - 30)
        self.rect.y = random.randint(0, SCREEN_HEIGHT - 30)
        self.speed = 1.5
        
    def update(self, player):
        # 简单AI: 向玩家移动（使用临时变量避免修改player对象）
        target_x = player.rect.x
        target_y = player.rect.y
        
        if self.rect.x < target_x:
            self.rect.x += self.speed
        else:
            self.rect.x -= self.speed
            
        if self.rect.y < target_y:
            self.rect.y += self.speed
        else:
            self.rect.y -= self.speed

def get_hand_direction(image, results):
    """识别手势方向"""
    direction = None
    attack = False
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # 获取关键点坐标
            landmarks = hand_landmarks.landmark
            wrist = landmarks[0]
            index_tip = landmarks[8]
            middle_tip = landmarks[12]
            
            # 判断是否握拳（攻击）
            if (index_tip.y > landmarks[6].y and 
                middle_tip.y > landmarks[10].y):
                attack = True
                return None, attack
            
            # 判断食指方向
            if abs(index_tip.x - wrist.x) > abs(index_tip.y - wrist.y):
                if index_tip.x < wrist.x:
                    direction = "LEFT"
                else:
                    direction = "RIGHT"
            else:
                if index_tip.y < wrist.y:
                    direction = "UP"
                else:
                    direction = "DOWN"
                    
    return direction, attack

# 游戏主循环
def main():
    clock = pygame.time.Clock()
    player = Player()
    font = pygame.font.SysFont(None, 36)
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    weapons = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)
    
    game_started = False  # 游戏开始标志
    spawn_timer = 0       # 敌人生成计时器
    
    # 创建障碍物
    obstacles.add(Wall(200, 200))
    obstacles.add(Wall(400, 300))
    obstacles.add(Water(500, 100))
    obstacles.add(Fire(300, 400))
    
    # 初始武器
    weapons.add(Weapon("手枪"))
    
    kills = 0
    game_over = False
    running = True
    last_shot_time = pygame.time.get_ticks()  # 初始化射击时间为当前时间
    weapon_spawn_timer = 0
    
    # 初始化字体
    font = pygame.font.SysFont(None, 36)
    
    while running:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                cap.release()
                
        # 读取摄像头画面
        ret, frame = cap.read()
        if not ret:
            continue
            
        # 转换颜色空间并识别手势
        frame = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        results = hands.process(frame)
        
        # 获取手势方向
        direction, attack = get_hand_direction(frame, results)
        
        # 在画面上绘制手势骨架
        annotated_image = frame.copy()
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    annotated_image, 
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS)
        
        # 转换为PyGame可显示的格式
        annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
        annotated_image = cv2.resize(annotated_image, (400, 300))
        camera_surface = pygame.image.frombuffer(
            annotated_image.tobytes(), 
            annotated_image.shape[1::-1], 
            "BGR")
            
        # 显示识别结果
        if direction:
            direction_text = font.render(f"Direction: {direction}", True, WHITE)
        else:
            direction_text = font.render("No direction detected", True, WHITE)
        
        # 攻击检测
        if attack:
            current_time = pygame.time.get_ticks()
            if current_time - last_shot_time > 300:
                if player.weapon == "手枪":
                    bullet = Bullet(player.rect.right, player.rect.centery)
                    bullets.add(bullet)
                elif player.weapon == "步枪":
                    for _ in range(2):
                        bullet = Bullet(player.rect.right, player.rect.centery + random.randint(-10, 10))
                        bullets.add(bullet)
                elif player.weapon == "霰弹枪":
                    for _ in range(5):
                        bullet = Bullet(player.rect.right, player.rect.centery + random.randint(-15, 15))
                        bullet.speed = random.uniform(8, 12)
                        bullets.add(bullet)
                last_shot_time = current_time
            current_time = pygame.time.get_ticks()
            if current_time - last_shot_time > 300:  # 缩短射击间隔为300ms
                if player.weapon == "手枪":
                    bullet = Bullet(player.rect.right, player.rect.centery)
                    bullets.add(bullet)
                elif player.weapon == "步枪":
                    for _ in range(2):
                        bullet = Bullet(player.rect.right, player.rect.centery + random.randint(-10, 10))
                        bullets.add(bullet)
                elif player.weapon == "霰弹枪":
                    for _ in range(5):
                        bullet = Bullet(player.rect.right, player.rect.centery + random.randint(-15, 15))
                        bullet.speed = random.uniform(8, 12)
                        bullets.add(bullet)
                last_shot_time = current_time
            elif event.type == pygame.USEREVENT + 1:
                # 敌人重生（最多5个敌人）
                if len(enemies) < 5:
                    enemies.add(Enemy())
            elif event.type == pygame.USEREVENT + 2:
                # 显示游戏结束画面
                pass
        
        # 优先处理移动（确保最先执行）
        moved = player.handle_movement(obstacles, direction)
        
        # 检测首次移动
        if not game_started and moved:
            game_started = True
            # 首次移动后生成2个敌人(初始不超过3个上限)
            for _ in range(2):
                enemies.add(Enemy())
        
        # 敌人AI
        if game_started:
            for enemy in enemies:
                enemy.update(player)
            
            # 敌人生成逻辑 (最多3个敌人)
            spawn_timer += 1
            if spawn_timer >= 300 and len(enemies) < 3:  # 每5秒补充敌人，最多3个
                enemies.add(Enemy())
                spawn_timer = 0
        
        # 处理子弹
        bullets.update()
        
        # 武器生成逻辑
        current_time = pygame.time.get_ticks()
        weapon_spawn_timer += 1
        if weapon_spawn_timer >= 600:  # 每10秒生成新武器
            weapon_types = ["手枪", "步枪", "霰弹枪"]
            weapons.add(Weapon(random.choice(weapon_types)))
            weapon_spawn_timer = 0
        
        # 武器拾取检测
        weapon_hits = pygame.sprite.spritecollide(player, weapons, True)
        for weapon in weapon_hits:
            player.weapon = weapon.type
        
        # 碰撞检测：子弹和敌人
        hits = pygame.sprite.groupcollide(bullets, enemies, True, True)
        for bullet, enemy_list in hits.items():
            for enemy in enemy_list:
                # 生成死亡特效
                death_effect = DeathEffect(enemy.rect.centerx, enemy.rect.centery)
                all_sprites.add(death_effect)
        for bullet, enemy_list in hits.items():
            for enemy in enemy_list:
                # 敌人被消灭，增加击杀数
                kills += 1
                # 生成死亡特效
                death_effect = DeathEffect(enemy.rect.centerx, enemy.rect.centery)
                all_sprites.add(death_effect)
                # 立即重生新敌人（延迟200ms避免卡顿）
                pygame.time.set_timer(pygame.USEREVENT + 1, 200, True)
        
        # 障碍物碰撞检测
        if not game_over:
            # 使用副本进行碰撞检测
            player_copy = Player()
            player_copy.rect = player.rect.copy()
            
            # 水坑和火坑检测
            hazard_hits = pygame.sprite.spritecollide(player_copy, [o for o in obstacles if isinstance(o, (Water, Fire))], False)
            for hazard in hazard_hits:
                hazard.damage_timer += 1
                if hazard.damage_timer >= 180:  # 3秒(60帧/秒)
                    game_over = True
                    pygame.time.set_timer(pygame.USEREVENT + 2, 1000, True)  # 1秒后显示结束画面
            else:
                # 重置不在危险区域的计时器
                for hazard in [o for o in obstacles if isinstance(o, (Water, Fire))]:
                    if hazard not in hazard_hits:
                        hazard.damage_timer = 0
        
        # 绘制
        screen.fill(BLACK)
        
        # 绘制游戏区域（先绘制背景）
        pygame.draw.rect(screen, BLACK, game_area)  # 先填充黑色背景
        pygame.draw.rect(screen, WHITE, game_area, 1)  # 再绘制边框
        
        # 绘制摄像头区域
        screen.blit(camera_surface, (GAME_WIDTH, 0))
        screen.blit(direction_text, (GAME_WIDTH + 10, 310))
        pygame.draw.rect(screen, WHITE, camera_area, 1)
        
        # 绘制游戏元素
        obstacles.draw(screen)
        weapons.draw(screen)
        screen.blit(player.image, player.rect)
        enemies.draw(screen)
        bullets.draw(screen)
        
        # 显示当前武器
        weapon_text = font.render(f"Weapon: {player.weapon}", True, WHITE)
        screen.blit(weapon_text, (10, 50))
        
        # 显示击杀数
        kill_text = font.render(f"Kills: {kills}", True, WHITE)
        screen.blit(kill_text, (10, 10))
        
        # 游戏结束画面
        if game_over:
            # 半透明遮罩
            overlay = pygame.Surface((GAME_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            
            # 游戏结束文字
            game_over_text = font.render("Game Over", True, RED)
            score_text = font.render(f"Your Score: {kills}", True, WHITE)
            restart_text = font.render("Press R to Restart", True, GREEN)
            
            screen.blit(game_over_text, (GAME_WIDTH//2 - game_over_text.get_width()//2, SCREEN_HEIGHT//2 - 50))
            screen.blit(score_text, (GAME_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2))
            screen.blit(restart_text, (GAME_WIDTH//2 - restart_text.get_width()//2, SCREEN_HEIGHT//2 + 50))
        
        pygame.display.flip()
        # 恢复正常帧率
        clock.tick(60)  # 恢复60FPS
        # 保留关键位置信息
        if moved:
            print(f"Player moved to: {player.rect.x}, {player.rect.y}")
        
        # 游戏结束后检测重新开始
        if game_over and keys[pygame.K_r]:
            return main()  # 重新开始游戏
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
