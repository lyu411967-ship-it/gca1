import os
import random
import sys
import time
import math
from dataclasses import dataclass

import cv2
import pygame

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOVIES_DIR = os.path.join(SCRIPT_DIR, "movies")
SOUNDS_DIR = os.path.join(SCRIPT_DIR, "data", "sounds")
TEXTURES_DIR = os.path.join(SCRIPT_DIR, "data", "textures")

VIDEOS = [os.path.join(MOVIES_DIR, "Logo.mp4"), os.path.join(MOVIES_DIR, "Logo2.mp4")]
AUDIO_FILES = [os.path.join(MOVIES_DIR, "Logo.wav"), os.path.join(MOVIES_DIR, "Logo2.wav")]

pygame.init()
pygame.mixer.init()
pygame.mixer.set_num_channels(24)

SCREEN_WIDTH, SCREEN_HEIGHT = 640, 480
WORLD_WIDTH, WORLD_HEIGHT = 2200, 1600
FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Mini GTA Turbo")
clock = pygame.time.Clock()

settings = {"volume": 0.6, "show_intro": True, "difficulty": "Normal", "screen_shake": True}
pygame.mixer.music.set_volume(settings["volume"])
SOUND_MIX = {
    "city": 0.32,          # quieter bed so voice lines cut through
    "sfx": 0.95,
    "police_voice": 1.0,   # intentionally loud
    "siren": 0.9,
}

COLORS = {
    "bg": (16, 18, 20), "road": (36, 38, 45), "lane": (190, 190, 120), "building": (58, 65, 80),
    "player": (230, 56, 56), "civil": (90, 205, 130), "cop": (45, 100, 240), "green": (65, 220, 90),
    "bullet": (255, 210, 120), "rocket": (255, 145, 60), "flame": (255, 170, 70), "coin": (255, 160, 20),
    "heal": (120, 220, 170), "hud": (255, 238, 90), "white": (235, 235, 235), "phone": (230, 200, 80),
}


def clamp(v, mn, mx):
    return max(mn, min(mx, v))


def load_sound(name):
    try:
        return pygame.mixer.Sound(os.path.join(SOUNDS_DIR, name))
    except pygame.error:
        return None


def load_texture(name, size=None):
    try:
        image = pygame.image.load(os.path.join(TEXTURES_DIR, name)).convert_alpha()
        return pygame.transform.smoothscale(image, size) if size else image
    except pygame.error:
        return None


def load_frames(folder, pattern, start, end, size):
    frames = []
    for i in range(start, end + 1):
        rel = os.path.join(folder, pattern.format(i))
        frame = load_texture(rel, size)
        if frame is not None:
            frames.append(frame)
    return frames


def blit_tiled(target, tile, rect=None):
    if tile is None:
        return
    area = rect or target.get_rect()
    tw, th = tile.get_size()
    for y in range(area.top, area.bottom, th):
        for x in range(area.left, area.right, tw):
            target.blit(tile, (x, y))


move_sound = load_sound("menu_move.wav")
select_sound = load_sound("menu_select.wav")
shoot_sound = load_sound("shoot.wav")
explode_sound = load_sound("explode.wav")
skid_sound = load_sound("skid.wav")
siren_sound = load_sound("siren.wav")
city_music_sound = load_sound("City.mp3")
menu_music_sound = load_sound("menu_music.mp3")
poilce_violation_sound = load_sound("poilce_violation.wav")
poilce_liberty_city_sound = load_sound("poilce_liberty_city.wav")
poilce_code_one_sound = load_sound("poilce_code_one.wav")
poilce_code_two_sound = load_sound("poilce_code_two.wav")

menu_background = load_texture("menu_back.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
loading_background = load_texture("loading.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
asphalt_tile = load_texture("asphalt.png", (32, 32))
player_idle_frame = load_texture(os.path.join("player_frames", "run_0.png"), (28, 40))
player_run_frames = load_frames("player_frames", "run_{}.png", 1, 5, (28, 40))
police_walk_frames = load_frames("npc_police_frames", "police_walk_{}.png", 0, 7, (30, 32))
police_die_frames = load_frames("npc_police_frames", "police_die_{}.png", 0, 3, (30, 32))


def set_sound_levels():
    base = settings["volume"]
    if menu_music_sound:
        menu_music_sound.set_volume(clamp(base * 0.9, 0.0, 1.0))
    if city_music_sound:
        city_music_sound.set_volume(clamp(base * SOUND_MIX["city"], 0.0, 1.0))
    if shoot_sound:
        shoot_sound.set_volume(clamp(base * SOUND_MIX["sfx"], 0.0, 1.0))
    if explode_sound:
        explode_sound.set_volume(clamp(base * 1.0, 0.0, 1.0))
    if skid_sound:
        skid_sound.set_volume(clamp(base * 0.75, 0.0, 1.0))
    if siren_sound:
        siren_sound.set_volume(clamp(base * SOUND_MIX["siren"], 0.0, 1.0))
    for s in (poilce_violation_sound, poilce_liberty_city_sound, poilce_code_one_sound, poilce_code_two_sound):
        if s:
            s.set_volume(clamp(base * SOUND_MIX["police_voice"], 0.0, 1.0))


def play_police_voice(sound_obj):
    if sound_obj is None:
        return
    # Duck ambience while police radio talks to make it clearly audible.
    if city_music_sound:
        city_music_sound.set_volume(clamp(settings["volume"] * SOUND_MIX["city"] * 0.5, 0.0, 1.0))
    sound_obj.play()


def start_city_music():
    if city_music_sound:
        city_music_sound.set_volume(clamp(settings["volume"] * SOUND_MIX["city"], 0.0, 1.0))
        city_music_sound.play(loops=-1)


def stop_city_music():
    if city_music_sound:
        city_music_sound.stop()


def start_menu_music():
    if menu_music_sound:
        menu_music_sound.set_volume(clamp(settings["volume"] * 0.9, 0.0, 1.0))
        menu_music_sound.play(loops=-1)


def stop_menu_music():
    if menu_music_sound:
        menu_music_sound.stop()


def show_loading_transition(duration=1.0):
    steps = max(1, int(duration * 60))
    for i in range(steps):
        if loading_background:
            screen.blit(loading_background, (0, 0))
        else:
            screen.fill((0, 0, 0))
            draw_text(screen, "LOADING", 34, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, COLORS["white"], center=True)
        alpha = int(255 * (1 - i / max(1, steps - 1)))
        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        fade.fill((0, 0, 0))
        fade.set_alpha(alpha)
        screen.blit(fade, (0, 0))
        pygame.display.flip()
        clock.tick(60)


@dataclass
class Camera:
    x: float = 0.0
    y: float = 0.0

    def follow(self, tx, ty):
        self.x = clamp(tx - SCREEN_WIDTH / 2, 0, WORLD_WIDTH - SCREEN_WIDTH)
        self.y = clamp(ty - SCREEN_HEIGHT / 2, 0, WORLD_HEIGHT - SCREEN_HEIGHT)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple
    size: int

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.94
        self.vy *= 0.94
        self.life -= dt


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    ttl: float
    damage: float
    kind: str
    blast: int = 0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.ttl -= dt


class Vehicle:
    def __init__(self, x, y, color, is_cop=False, variant="civil"):
        self.x, self.y = x, y
        self.prev_x, self.prev_y = x, y
        self.color = color
        self.is_cop = is_cop
        self.variant = variant
        self.radius = 12
        self.angle = random.random() * 360
        self.speed = random.uniform(60, 110)
        self.max_speed = 160 if is_cop else 145
        self.turn_timer = random.uniform(0.7, 1.8)
        self.health = 120 if is_cop else 100
        self.roadblock = False
        self.roadblock_timer = 0.0
        self.controlled = False

    def rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def heading(self):
        return pygame.math.Vector2(1, 0).rotate(self.angle)

    def control_update(self, dt, keys):
        steer = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        throttle = int(keys[pygame.K_w]) - int(keys[pygame.K_s])
        turn = 150 if abs(self.speed) > 20 else 85
        self.angle += steer * turn * dt
        self.speed += throttle * 260 * dt
        self.speed *= 0.97
        self.speed = clamp(self.speed, -60, self.max_speed + 45)
    def ai_update(self, dt, roads, traffic, px, py, wanted):
        if self.controlled:
            return
        if self.roadblock:
            self.roadblock_timer -= dt
            self.speed *= 0.92
            if self.roadblock_timer <= 0:
                self.roadblock = False
                self.speed = random.uniform(50, 90)
            return

        self.turn_timer -= dt
        if self.is_cop and wanted > 0:
            to_player = pygame.math.Vector2(px - self.x, py - self.y)
            if to_player.length() > 0.001:
                target = to_player.as_polar()[1]
                self.angle += (target - self.angle) * 0.07
            self.speed = min(self.speed + 80 * dt, self.max_speed + 25)
        else:
            if self.turn_timer <= 0:
                self.turn_timer = random.uniform(0.7, 1.8)
                self.angle += random.uniform(-45, 45)
            self.speed = clamp(self.speed + random.uniform(-14, 14) * dt, 55, self.max_speed)

        if not point_on_any_road(self.x, self.y, roads):
            cx, cy = nearest_road_center(self.x, self.y, roads)
            to_center = pygame.math.Vector2(cx - self.x, cy - self.y)
            if to_center.length() > 0.01:
                target = to_center.as_polar()[1]
                self.angle += (target - self.angle) * 0.09

        fwd = self.heading()
        fx, fy = self.x + fwd.x * 18, self.y + fwd.y * 18
        for other in traffic:
            if other is self:
                continue
            if ((other.x - fx) ** 2 + (other.y - fy) ** 2) ** 0.5 < 26:
                self.speed *= 0.82
                break

    def move_and_collide(self, dt, blocks):
        self.prev_x, self.prev_y = self.x, self.y
        d = self.heading()
        self.x += d.x * self.speed * dt
        self.y += d.y * self.speed * dt
        self.x = clamp(self.x, 20, WORLD_WIDTH - 20)
        self.y = clamp(self.y, 20, WORLD_HEIGHT - 20)
        r = self.rect()
        for b in blocks:
            if r.colliderect(b):
                self.x, self.y = self.prev_x, self.prev_y
                self.speed *= -0.2
                return True
        return False


class Pedestrian:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.prev_x, self.prev_y = x, y
        self.radius = 6
        self.speed = random.uniform(30, 55)
        self.angle = random.uniform(0, 360)
        self.turn_timer = random.uniform(1.2, 2.8)
        self.alive = True
        self.dead_timer = 0.0
        self.anim_timer = 0.0
        self.walk_frame = 0
        self.die_frame = 0
        self.face_left = False

    def rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt, roads, blocks):
        if not self.alive:
            self.dead_timer += dt
            if police_die_frames:
                self.die_frame = min(len(police_die_frames) - 1, int(self.dead_timer * 9))
            return
        self.prev_x, self.prev_y = self.x, self.y
        self.turn_timer -= dt
        if self.turn_timer <= 0:
            self.turn_timer = random.uniform(1.2, 2.8)
            self.angle += random.uniform(-65, 65)
        if point_on_any_road(self.x, self.y, roads):
            cx, cy = nearest_road_center(self.x, self.y, roads)
            away = pygame.math.Vector2(self.x - cx, self.y - cy)
            if away.length() > 0.001:
                self.angle += (away.as_polar()[1] - self.angle) * 0.08
        d = pygame.math.Vector2(1, 0).rotate(self.angle)
        if abs(d.x) > 0.01:
            self.face_left = d.x < 0
        self.x += d.x * self.speed * dt
        self.y += d.y * self.speed * dt
        self.x = clamp(self.x, 16, WORLD_WIDTH - 16)
        self.y = clamp(self.y, 16, WORLD_HEIGHT - 16)
        for b in blocks:
            if self.rect().colliderect(b):
                self.x, self.y = self.prev_x, self.prev_y
                self.angle += 180
                break
        self.anim_timer += dt
        if police_walk_frames and self.anim_timer >= 0.09:
            self.anim_timer = 0
            self.walk_frame = (self.walk_frame + 1) % len(police_walk_frames)


class Player:
    def __init__(self):
        self.x, self.y = WORLD_WIDTH / 2, WORLD_HEIGHT / 2
        self.prev_x, self.prev_y = self.x, self.y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = 11
        self.hp = 100.0
        self.cash = 0
        self.score = 0
        self.in_vehicle = None
        self.facing = pygame.math.Vector2(1, 0)
        self.face_left = False
        self.look_angle = 0.0
        self.anim_timer = 0.0
        self.run_frame = 0
        self.current_weapon = "pistol"
        self.weapons = {
            "pistol": {"cooldown": 0.24, "projectiles": 1, "spread": 2, "speed": 560, "damage": 32, "ttl": 1.0, "kind": "bullet", "blast": 0},
            "smg": {"cooldown": 0.08, "projectiles": 1, "spread": 11, "speed": 620, "damage": 13, "ttl": 0.8, "kind": "bullet", "blast": 0},
            "rocket": {"cooldown": 0.75, "projectiles": 1, "spread": 2, "speed": 330, "damage": 90, "ttl": 1.8, "kind": "rocket", "blast": 92},
            "flame": {"cooldown": 0.05, "projectiles": 3, "spread": 22, "speed": 260, "damage": 7, "ttl": 0.32, "kind": "flame", "blast": 0},
        }
        self.weapon_cd = 0.0

    def rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt, keys, blocks):
        self.weapon_cd = max(0, self.weapon_cd - dt)
        if self.in_vehicle is not None:
            self.x, self.y = self.in_vehicle.x, self.in_vehicle.y
            self.facing = self.in_vehicle.heading()
            if abs(self.facing.x) > 0.01:
                self.face_left = self.facing.x < 0
            if self.facing.length() > 0.001:
                self.look_angle = self.facing.as_polar()[1]
            return
        self.prev_x, self.prev_y = self.x, self.y
        ax = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        ay = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
        m = pygame.math.Vector2(ax, ay)
        if m.length() > 0:
            m = m.normalize()
            self.facing = m
            if abs(m.x) > 0.01:
                self.face_left = m.x < 0
            self.look_angle = m.as_polar()[1]
            self.vx += m.x * 490 * dt
            self.vy += m.y * 490 * dt
        s = (self.vx ** 2 + self.vy ** 2) ** 0.5
        if s > 235:
            k = 235 / max(s, 0.01)
            self.vx *= k
            self.vy *= k
        self.vx *= 0.84
        self.vy *= 0.84
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x = clamp(self.x, 18, WORLD_WIDTH - 18)
        self.y = clamp(self.y, 18, WORLD_HEIGHT - 18)
        for b in blocks:
            if self.rect().colliderect(b):
                self.x, self.y = self.prev_x, self.prev_y
                self.vx, self.vy = 0, 0
                break
        move_speed = (self.vx ** 2 + self.vy ** 2) ** 0.5
        if move_speed > 20 and player_run_frames:
            self.anim_timer += dt
            if self.anim_timer >= 0.08:
                self.anim_timer = 0
                self.run_frame = (self.run_frame + 1) % len(player_run_frames)
        else:
            self.run_frame = 0
            self.anim_timer = 0
    def switch_weapon(self, name):
        if name in self.weapons:
            self.current_weapon = name

    def try_enter_vehicle(self, traffic):
        if self.in_vehicle is not None:
            return
        nearest, best = None, 99999
        for car in traffic:
            if car.roadblock:
                continue
            d = ((car.x - self.x) ** 2 + (car.y - self.y) ** 2) ** 0.5
            if d < best:
                best = d
                nearest = car
        if nearest and best < 28:
            self.in_vehicle = nearest
            nearest.controlled = True
            nearest.speed *= 0.4

    def exit_vehicle(self, blocks):
        if self.in_vehicle is None:
            return
        car = self.in_vehicle
        side = car.heading().rotate(90)
        self.x = clamp(car.x + side.x * 20, 18, WORLD_WIDTH - 18)
        self.y = clamp(car.y + side.y * 20, 18, WORLD_HEIGHT - 18)
        car.controlled = False
        self.in_vehicle = None
        for b in blocks:
            if self.rect().colliderect(b):
                self.x = clamp(car.x - side.x * 20, 18, WORLD_WIDTH - 18)
                self.y = clamp(car.y - side.y * 20, 18, WORLD_HEIGHT - 18)
                break

    def shoot(self, tx, ty):
        if self.weapon_cd > 0:
            return []
        w = self.weapons[self.current_weapon]
        self.weapon_cd = w["cooldown"]
        base = pygame.math.Vector2(tx - self.x, ty - self.y)
        if base.length() < 0.001:
            base = self.facing
        base = base.normalize() if base.length() > 0.001 else pygame.math.Vector2(1, 0)
        self.look_angle = base.as_polar()[1]
        out = []
        for _ in range(w["projectiles"]):
            spread = random.uniform(-w["spread"], w["spread"])
            d = base.rotate(spread)
            out.append(Projectile(self.x, self.y, d.x * w["speed"], d.y * w["speed"], w["ttl"], w["damage"], w["kind"], w["blast"]))
        return out


def make_roads():
    roads = []
    for y in range(190, WORLD_HEIGHT, 240):
        roads.append(pygame.Rect(0, y, WORLD_WIDTH, 84))
    for x in range(170, WORLD_WIDTH, 240):
        roads.append(pygame.Rect(x, 0, 92, WORLD_HEIGHT))
    return roads


def point_on_any_road(x, y, roads):
    return any(r.collidepoint(x, y) for r in roads)


def nearest_road_center(x, y, roads):
    best, best_d = (x, y), 10**18
    for r in roads:
        cx = clamp(x, r.left, r.right)
        cy = clamp(y, r.top, r.bottom)
        d = (cx - x) ** 2 + (cy - y) ** 2
        if d < best_d:
            best, best_d = (cx, cy), d
    return best


def sample_point_on_roads(roads):
    r = random.choice(roads)
    return random.randint(r.left + 10, r.right - 10), random.randint(r.top + 10, r.bottom - 10)


def make_buildings(roads):
    blocks, attempts = [], 380
    while attempts > 0 and len(blocks) < 138:
        attempts -= 1
        w, h = random.randint(58, 122), random.randint(58, 122)
        x, y = random.randint(22, WORLD_WIDTH - w - 22), random.randint(22, WORLD_HEIGHT - h - 22)
        r = pygame.Rect(x, y, w, h)
        if any(road.inflate(14, 14).colliderect(r) for road in roads):
            continue
        if any(b.inflate(10, 10).colliderect(r) for b in blocks):
            continue
        blocks.append(r)
    return blocks


def spawn_traffic(roads, blocks):
    cars = []
    for _ in range(14):
        x, y = sample_point_on_roads(roads)
        variant = "green" if random.random() < 0.25 else "civil"
        col = COLORS["green"] if variant == "green" else COLORS["civil"]
        cars.append(Vehicle(x, y, col, False, variant))
    for _ in range(5):
        x, y = sample_point_on_roads(roads)
        cars.append(Vehicle(x, y, COLORS["cop"], True, "cop"))
    for c in cars:
        if any(c.rect().colliderect(b) for b in blocks):
            c.x, c.y = sample_point_on_roads(roads)
    return cars


def spawn_pedestrians(roads, blocks, count=30):
    peds = []
    tries = 0
    while len(peds) < count and tries < count * 20:
        tries += 1
        x, y = random.randint(16, WORLD_WIDTH - 16), random.randint(16, WORLD_HEIGHT - 16)
        if point_on_any_road(x, y, roads):
            continue
        if any(pygame.Rect(x - 7, y - 7, 14, 14).colliderect(b) for b in blocks):
            continue
        peds.append(Pedestrian(x, y))
    return peds


def make_phone_booths(roads, count=7):
    booths = []
    for _ in range(count):
        rx, ry = sample_point_on_roads(roads)
        booths.append({"x": rx + random.choice([-26, 26]), "y": ry + random.choice([-26, 26])})
    return booths


def draw_world(base, roads, blocks):
    if asphalt_tile:
        blit_tiled(base, asphalt_tile)
    else:
        base.fill(COLORS["bg"])
    for road in roads:
        pygame.draw.rect(base, COLORS["road"], road)
    for road in roads:
        if road.width > road.height:
            for i in range(road.x + 16, road.right - 16, 34):
                pygame.draw.rect(base, COLORS["lane"], (i, road.y + road.height // 2 - 2, 16, 4))
        else:
            for i in range(road.y + 16, road.bottom - 16, 34):
                pygame.draw.rect(base, COLORS["lane"], (road.x + road.width // 2 - 2, i, 4, 16))
    for b in blocks:
        pygame.draw.rect(base, COLORS["building"], b, border_radius=5)
        pygame.draw.rect(base, (86, 96, 114), b, 2, border_radius=5)


def world_to_screen(cam, x, y):
    return int(x - cam.x), int(y - cam.y)


def draw_centered_sprite(surface, sprite, x, y, face_left=False):
    if sprite is None:
        return
    img = pygame.transform.flip(sprite, True, False) if face_left else sprite
    rect = img.get_rect(center=(x, y))
    surface.blit(img, rect)


def draw_centered_sprite_rotated(surface, sprite, x, y, angle_deg):
    if sprite is None:
        return
    rotated = pygame.transform.rotozoom(sprite, -angle_deg, 1.0)
    rect = rotated.get_rect(center=(x, y))
    surface.blit(rotated, rect)


def draw_text(s, text, size, x, y, color, center=False):
    f = pygame.font.SysFont("Consolas", size, bold=True)
    i = f.render(text, True, color)
    r = i.get_rect(center=(x, y)) if center else i.get_rect(topleft=(x, y))
    s.blit(i, r)


def get_daylight(phase):
    return (math.cos(phase * math.tau + math.pi) + 1.0) * 0.5


def draw_day_night_overlay(surface, phase, focus_x=None, focus_y=None):
    daylight = get_daylight(phase)
    darkness = 1.0 - daylight
    alpha = int(clamp(darkness * 160, 0, 170))
    if alpha <= 0:
        return

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((20, 30, 55, alpha))

    if focus_x is not None and focus_y is not None and darkness > 0.25:
        radius = int(80 + daylight * 70)
        glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(glow, (0, 0, 0, int(clamp(darkness * 100, 0, 120))), (int(focus_x), int(focus_y)), radius + 30)
        pygame.draw.circle(glow, (0, 0, 0, 0), (int(focus_x), int(focus_y)), radius)
        overlay.blit(glow, (0, 0))

    surface.blit(overlay, (0, 0))

def draw_star(surface, x, y, active):
    c = (255, 220, 90) if active else (70, 70, 70)
    pts = [(x, y - 8), (x + 3, y - 2), (x + 10, y - 2), (x + 4, y + 2), (x + 7, y + 9), (x, y + 5), (x - 7, y + 9), (x - 4, y + 2), (x - 10, y - 2), (x - 3, y - 2)]
    pygame.draw.polygon(surface, c, pts)


def draw_menu_buttons(items, selected, y0=196):
    for i, item in enumerate(items):
        y = y0 + i * 34
        col = COLORS["hud"] if i == selected else COLORS["white"]
        draw_text(screen, item, 20, SCREEN_WIDTH // 2, y, col, center=True)
        if i == selected:
            pygame.draw.line(screen, col, (SCREEN_WIDTH // 2 - 56, y + 13), (SCREEN_WIDTH // 2 + 56, y + 13), 1)


def create_explosion(x, y, particles, n=15):
    for _ in range(n):
        a = random.uniform(0, 360)
        sp = random.uniform(80, 210)
        v = pygame.math.Vector2(1, 0).rotate(a)
        col = random.choice([(255, 120, 60), (255, 170, 80), (130, 130, 130), (170, 170, 170)])
        particles.append(Particle(x, y, v.x * sp, v.y * sp, random.uniform(0.2, 0.55), col, random.randint(2, 4)))


def deploy_roadblock(traffic, player, roads):
    nearest = min(roads, key=lambda r: (clamp(player.x, r.left, r.right) - player.x) ** 2 + (clamp(player.y, r.top, r.bottom) - player.y) ** 2)
    centers = []
    if nearest.width > nearest.height:
        y = nearest.centery
        for dx in (-26, 0, 26):
            centers.append((clamp(player.x + dx, nearest.left + 16, nearest.right - 16), y))
    else:
        x = nearest.centerx
        for dy in (-26, 0, 26):
            centers.append((x, clamp(player.y + dy, nearest.top + 16, nearest.bottom - 16)))
    for cx, cy in centers:
        car = Vehicle(cx, cy, COLORS["cop"], True, "cop")
        car.roadblock = True
        car.roadblock_timer = 7.0
        car.speed = 0
        car.angle = 90 if nearest.width > nearest.height else 0
        traffic.append(car)


def respawn_vehicle(car, roads):
    car.x, car.y = sample_point_on_roads(roads)
    car.prev_x, car.prev_y = car.x, car.y
    car.speed = random.uniform(55, 95)
    car.angle = random.uniform(0, 360)
    car.health = 120 if car.is_cop else 100
    car.roadblock = False
    car.controlled = False


def start_random_mission():
    if random.random() < 0.5:
        return {"type": "destroy_green", "title": "Destroy 5 green cars", "progress": 0, "total": 5, "timer": 45.0, "target": None}
    return {"type": "reach_point", "title": "Drive to point B in 30 sec", "progress": 0, "total": 1, "timer": 30.0, "target": {"x": random.randint(120, WORLD_WIDTH - 120), "y": random.randint(120, WORLD_HEIGHT - 120)}}


def play_video(vp, ap):
    if not os.path.exists(vp):
        return
    if os.path.exists(ap):
        pygame.mixer.music.load(ap)
        pygame.mixer.music.play()
    else:
        pygame.mixer.music.stop()
    cap = cv2.VideoCapture(vp)
    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps > 0 else 30
    skip = False
    while cap.isOpened() and not skip:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
        surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.blit(surf, (0, 0))
        pygame.display.flip()
        clock.tick(fps)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                skip = True
    cap.release()
    pygame.mixer.music.stop()


def run_intro_if_needed():
    if not settings["show_intro"]:
        return
    for i in range(min(len(VIDEOS), len(AUDIO_FILES))):
        play_video(VIDEOS[i], AUDIO_FILES[i])


def main_menu():
    items, selected = ["Start", "Options", "Skip Intro", "Exit"], 0
    while True:
        screen.blit(menu_background, (0, 0)) if menu_background else screen.fill((0, 0, 0))
        draw_menu_buttons(items, selected)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "Exit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_UP: selected = (selected - 1) % len(items); move_sound and move_sound.play()
                if e.key == pygame.K_DOWN: selected = (selected + 1) % len(items); move_sound and move_sound.play()
                if e.key == pygame.K_RETURN: select_sound and select_sound.play(); pygame.time.delay(90); return items[selected]
                if e.key == pygame.K_ESCAPE: return "Exit"


def options_menu():
    items, selected = ["Volume", "Difficulty", "Shake", "Back"], 0
    while True:
        screen.blit(menu_background, (0, 0)) if menu_background else screen.fill((0, 0, 0))
        labels = [f"Volume {int(settings['volume'] * 100)}%", f"Difficulty {settings['difficulty']}", f"Shake {'ON' if settings['screen_shake'] else 'OFF'}", "Back"]
        draw_menu_buttons(labels, selected, 186)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_UP: selected = (selected - 1) % len(items)
                if e.key == pygame.K_DOWN: selected = (selected + 1) % len(items)
                if e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    key = items[selected]
                    if key == "Volume":
                        d = 0.1 if e.key == pygame.K_RIGHT else -0.1
                        settings["volume"] = clamp(settings["volume"] + d, 0.0, 1.0)
                        pygame.mixer.music.set_volume(settings["volume"])
                        set_sound_levels()
                    elif key == "Difficulty":
                        settings["difficulty"] = "Easy" if settings["difficulty"] == "Normal" else "Normal"
                    elif key == "Shake":
                        settings["screen_shake"] = not settings["screen_shake"]
                if e.key == pygame.K_RETURN and items[selected] == "Back": return
                if e.key == pygame.K_ESCAPE: return


def game_loop():
    player, cam = Player(), Camera()
    roads = make_roads()
    blocks = make_buildings(roads)
    player.x, player.y = sample_point_on_roads(roads)
    player.prev_x, player.prev_y = player.x, player.y
    booths = make_phone_booths(roads)
    bg = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT)); draw_world(bg, roads, blocks)
    traffic, peds = spawn_traffic(roads, blocks), spawn_pedestrians(roads, blocks)
    pickups, projectiles, particles = [], [], []
    wanted, wanted_timer, siren_timer, roadblock_cd, shake = 0, 0.0, 0.0, 0.0, 0.0
    day_time = random.uniform(0.0, 120.0)
    day_cycle_seconds = 120.0
    police_voice_cd = 0.0
    police_duck_timer = 0.0
    liberty_city_announced = False
    paused, mission, notice = False, None, 0.0
    set_sound_levels()
    start_city_music()

    while True:
        dt = clock.tick(FPS) / 1000.0
        day_time = (day_time + dt) % day_cycle_seconds
        day_phase = day_time / day_cycle_seconds
        notice = max(0, notice - dt)
        police_voice_cd = max(0, police_voice_cd - dt)
        police_duck_timer = max(0, police_duck_timer - dt)
        if police_duck_timer <= 0 and city_music_sound:
            city_music_sound.set_volume(clamp(settings["volume"] * SOUND_MIX["city"], 0.0, 1.0))
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                stop_city_music()
                return "Exit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: paused = not paused
                if e.key in (pygame.K_f, pygame.K_RETURN):
                    player.try_enter_vehicle(traffic) if player.in_vehicle is None else player.exit_vehicle(blocks)
                if e.key == pygame.K_1: player.switch_weapon("pistol")
                if e.key == pygame.K_2: player.switch_weapon("smg")
                if e.key == pygame.K_3: player.switch_weapon("rocket")
                if e.key == pygame.K_4: player.switch_weapon("flame")
                if e.key == pygame.K_t and mission is None:
                    if any(((player.x - b["x"]) ** 2 + (player.y - b["y"]) ** 2) ** 0.5 < 28 for b in booths):
                        mission, notice = start_random_mission(), 2.8
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not paused:
                mx, my = pygame.mouse.get_pos(); shots = player.shoot(mx + cam.x, my + cam.y)
                if shots: projectiles.extend(shots); shoot_sound and shoot_sound.play()

        if paused:
            screen.fill((0, 0, 0)); draw_text(screen, "PAUSED", 58, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, COLORS["white"], center=True); pygame.display.flip(); continue

        keys = pygame.key.get_pressed(); player.update(dt, keys, blocks)
        if player.in_vehicle is not None:
            old = player.in_vehicle.angle; player.in_vehicle.control_update(dt, keys)
            if player.in_vehicle.move_and_collide(dt, blocks): player.hp -= 6; shake = max(shake, 0.08)
            if abs(player.in_vehicle.angle - old) > 2.3 and abs(player.in_vehicle.speed) > 100 and skid_sound and random.random() < 0.03: skid_sound.play()

        for car in traffic:
            if car is player.in_vehicle: continue
            car.ai_update(dt, roads, traffic, player.x, player.y, wanted)
            if car.move_and_collide(dt, blocks): car.angle += random.uniform(120, 240)

        if player.in_vehicle is None:
            for car in traffic:
                if player.rect().colliderect(car.rect()):
                    player.hp -= (20 if car.is_cop else 13) * dt
                    wanted = min(5, wanted + (2 if car.is_cop else 1))
                    wanted_timer = 6.0
                    shake = max(shake, 0.08)
                    if police_voice_cd <= 0 and poilce_violation_sound:
                        play_police_voice(poilce_violation_sound)
                        police_voice_cd = 1.5
                        police_duck_timer = 0.9

        for p in projectiles: p.update(dt)
        next_projectiles = []
        for p in projectiles:
            if p.ttl <= 0 or not (0 < p.x < WORLD_WIDTH and 0 < p.y < WORLD_HEIGHT): continue
            probe = pygame.Rect(int(p.x - 2), int(p.y - 2), 4, 4)
            if any(probe.colliderect(b) for b in blocks):
                if p.blast > 0: create_explosion(p.x, p.y, particles, 16); shake = max(shake, 0.2); explode_sound and explode_sound.play()
                continue
            hit = False
            for car in traffic:
                if probe.colliderect(car.rect()):
                    car.health -= p.damage + (2 if p.kind == "flame" else 0)
                    if car.is_cop:
                        wanted = min(5, wanted + 1)
                        wanted_timer = 7.0
                        if police_voice_cd <= 0 and poilce_code_two_sound:
                            play_police_voice(poilce_code_two_sound)
                            police_voice_cd = 1.6
                            police_duck_timer = 0.9
                    elif police_voice_cd <= 0 and poilce_code_one_sound:
                        play_police_voice(poilce_code_one_sound)
                        police_voice_cd = 1.2
                        police_duck_timer = 0.8
                    hit = True
                    if p.blast > 0:
                        create_explosion(p.x, p.y, particles, 18); shake = max(shake, 0.24); explode_sound and explode_sound.play()
                        for other in traffic:
                            d = ((other.x - p.x) ** 2 + (other.y - p.y) ** 2) ** 0.5
                            if d < p.blast: other.health -= max(10, p.damage * (1 - d / p.blast))
                    if p.kind in ("bullet", "rocket"): break
            if (not hit) or p.kind == "flame":
                for ped in peds:
                    if ped.alive and probe.colliderect(ped.rect()):
                        ped.alive = False; wanted = min(5, wanted + 1); wanted_timer = 6.0; player.score += 40
                        if police_voice_cd <= 0 and poilce_code_one_sound:
                            play_police_voice(poilce_code_one_sound)
                            police_voice_cd = 1.2
                            police_duck_timer = 0.8
                        if random.random() < 0.5: pickups.append({"x": ped.x, "y": ped.y, "kind": "cash" if random.random() < 0.7 else "heal", "ttl": 18.0})
                        create_explosion(ped.x, ped.y, particles, 8); hit = True; break
            if (not hit) or p.kind == "flame": next_projectiles.append(p)
        projectiles = next_projectiles

        for car in traffic:
            if car.health <= 0:
                if mission and mission["type"] == "destroy_green" and car.variant == "green":
                    mission["progress"] += 1
                player.score += 75 if car.is_cop else 40
                if car.variant == "green": player.score += 30
                if car.is_cop: wanted = min(5, wanted + 2); wanted_timer = 8.0
                create_explosion(car.x, car.y, particles, 18); shake = max(shake, 0.22); explode_sound and explode_sound.play()
                if player.in_vehicle is car: player.in_vehicle = None; player.hp -= 24
                respawn_vehicle(car, roads)

        for ped in peds: ped.update(dt, roads, blocks)
        if player.in_vehicle is not None:
            vr = player.in_vehicle.rect()
            for ped in peds:
                if ped.alive and vr.colliderect(ped.rect()):
                    ped.alive = False; wanted = min(5, wanted + 1); wanted_timer = 6.0; player.score += 30
                    if police_voice_cd <= 0 and poilce_violation_sound:
                        play_police_voice(poilce_violation_sound)
                        police_voice_cd = 1.4
                        police_duck_timer = 0.9
                    if random.random() < 0.6: pickups.append({"x": ped.x, "y": ped.y, "kind": "cash", "ttl": 18.0})

        for item in pickups: item["ttl"] -= dt
        pickups = [p for p in pickups if p["ttl"] > 0]
        for item in pickups:
            if ((player.x - item["x"]) ** 2 + (player.y - item["y"]) ** 2) ** 0.5 < 18:
                item["ttl"] = 0
                if item["kind"] == "cash": player.cash += 100; player.score += 60
                else: player.hp = min(100, player.hp + 18); player.score += 20
        pickups = [p for p in pickups if p["ttl"] > 0]

        if wanted > 0:
            wanted_timer -= dt; siren_timer -= dt
            if siren_timer <= 0: siren_timer = 1.8; siren_sound and siren_sound.play()
            if wanted_timer <= 0: wanted = max(0, wanted - 1); wanted_timer = 5.6
            if (not liberty_city_announced) and poilce_liberty_city_sound and police_voice_cd <= 0:
                play_police_voice(poilce_liberty_city_sound)
                police_voice_cd = 2.2
                police_duck_timer = 1.2
                liberty_city_announced = True
        else:
            liberty_city_announced = False

        roadblock_cd -= dt
        if wanted >= 4 and roadblock_cd <= 0: deploy_roadblock(traffic, player, roads); roadblock_cd = 10.0

        if mission:
            mission["timer"] -= dt
            if mission["timer"] <= 0: mission = None; notice = 2.4
            elif mission["type"] == "reach_point" and player.in_vehicle is not None:
                tx, ty = mission["target"]["x"], mission["target"]["y"]
                if ((player.x - tx) ** 2 + (player.y - ty) ** 2) ** 0.5 < 34: player.cash += 400; player.score += 250; mission = None; notice = 2.4
            elif mission["type"] == "destroy_green" and mission["progress"] >= mission["total"]:
                player.cash += 400; player.score += 250; mission = None; notice = 2.4

        if settings["difficulty"] == "Easy": player.hp = min(100, player.hp + dt * 2.2)
        if player.hp <= 0:
            stop_city_music()
            return "GameOver"

        cam.follow(player.x, player.y)
        shake = max(0, shake - dt)
        ox = random.randint(-4, 4) if settings["screen_shake"] and shake > 0 else 0
        oy = random.randint(-4, 4) if settings["screen_shake"] and shake > 0 else 0
        screen.blit(bg, (ox - int(cam.x), oy - int(cam.y)))

        for booth in booths:
            sx, sy = world_to_screen(cam, booth["x"], booth["y"])
            pygame.draw.rect(screen, COLORS["phone"], (sx - 4 + ox, sy - 8 + oy, 8, 16), border_radius=2)
        if mission and mission["type"] == "reach_point":
            sx, sy = world_to_screen(cam, mission["target"]["x"], mission["target"]["y"])
            pygame.draw.circle(screen, (255, 80, 80), (sx + ox, sy + oy), 14, 2)
        for it in pickups:
            sx, sy = world_to_screen(cam, it["x"], it["y"])
            pygame.draw.circle(screen, COLORS["coin"] if it["kind"] == "cash" else COLORS["heal"], (sx + ox, sy + oy), 6)
        for ped in peds:
            sx, sy = world_to_screen(cam, ped.x, ped.y)
            if ped.alive:
                if police_walk_frames:
                    frame = police_walk_frames[ped.walk_frame % len(police_walk_frames)]
                    draw_centered_sprite(screen, frame, sx + ox, sy + oy, ped.face_left)
                else:
                    pygame.draw.circle(screen, (220, 220, 220), (sx + ox, sy + oy), ped.radius)
            elif police_die_frames and ped.dead_timer <= 0.6:
                frame = police_die_frames[ped.die_frame % len(police_die_frames)]
                draw_centered_sprite(screen, frame, sx + ox, sy + oy, ped.face_left)
        for car in traffic:
            sx, sy = world_to_screen(cam, car.x, car.y)
            pygame.draw.circle(screen, car.color, (sx + ox, sy + oy), car.radius)
            pygame.draw.circle(screen, (15, 15, 15), (sx + ox, sy + oy), car.radius, 2)
        for p in projectiles:
            sx, sy = world_to_screen(cam, p.x, p.y)
            col, sz = (COLORS["rocket"], 3) if p.kind == "rocket" else ((COLORS["flame"], 2) if p.kind == "flame" else (COLORS["bullet"], 2))
            pygame.draw.circle(screen, col, (sx + ox, sy + oy), sz)
        for part in particles:
            part.update(dt)
            if part.life > 0:
                sx, sy = world_to_screen(cam, part.x, part.y)
                alpha = int(clamp(part.life * 600, 0, 255))
                sf = pygame.Surface((part.size * 2, part.size * 2), pygame.SRCALPHA)
                sf.fill((*part.color[:3], alpha))
                screen.blit(sf, (sx + ox, sy + oy))
        particles = [pt for pt in particles if pt.life > 0]
        if player.in_vehicle is None:
            px, py = world_to_screen(cam, player.x, player.y)
            if player_run_frames and player_idle_frame:
                move_speed = (player.vx ** 2 + player.vy ** 2) ** 0.5
                frame = player_run_frames[player.run_frame % len(player_run_frames)] if move_speed > 20 else player_idle_frame
                draw_centered_sprite_rotated(screen, frame, px + ox, py + oy, player.look_angle)
            elif player_idle_frame:
                draw_centered_sprite_rotated(screen, player_idle_frame, px + ox, py + oy, player.look_angle)
            else:
                pygame.draw.circle(screen, COLORS["player"], (px + ox, py + oy), player.radius)
                pygame.draw.circle(screen, COLORS["white"], (px + ox, py + oy), player.radius, 2)

        focus_x = px + ox if player.in_vehicle is None else (world_to_screen(cam, player.x, player.y)[0] + ox)
        focus_y = py + oy if player.in_vehicle is None else (world_to_screen(cam, player.x, player.y)[1] + oy)
        draw_day_night_overlay(screen, day_phase, focus_x, focus_y)

        pygame.draw.rect(screen, (12, 12, 12), (10, SCREEN_HEIGHT - 43, 220, 30), border_radius=6)
        hpw = int(216 * clamp(player.hp, 0, 100) / 100)
        pygame.draw.rect(screen, (205, 52, 52), (12, SCREEN_HEIGHT - 41, hpw, 26), border_radius=5)
        draw_text(screen, f"HP {int(player.hp)}", 18, 18, SCREEN_HEIGHT - 36, COLORS["white"])
        draw_text(screen, f"$ {player.cash}", 22, 12, 10, COLORS["hud"])
        draw_text(screen, f"Score {player.score}", 20, 12, 34, COLORS["white"])
        draw_text(screen, f"Weapon {player.current_weapon}", 18, 12, 58, (180, 180, 210))
        draw_text(screen, "1 pistol 2 smg 3 rocket 4 flame", 14, 12, 78, (140, 140, 150))
        draw_text(screen, "IN CAR" if player.in_vehicle else "ON FOOT", 16, 12, 96, (180, 220, 170))
        draw_text(screen, "F/ENTER hijack or exit", 14, 12, 114, (155, 155, 165))
        draw_text(screen, "T at phone booth for mission", 14, 12, 130, (155, 155, 165))
        game_hour = int((day_phase * 24.0) % 24)
        game_min = int(((day_phase * 24.0) % 1.0) * 60)
        draw_text(screen, f"Time {game_hour:02d}:{game_min:02d}", 16, 12, 146, (170, 190, 220))
        for i in range(5): draw_star(screen, 282 + i * 22, 24, i < wanted)
        if mission:
            draw_text(screen, mission["title"], 18, 220, SCREEN_HEIGHT - 68, COLORS["white"])
            draw_text(screen, f"{mission['timer']:.1f}s", 18, 220, SCREEN_HEIGHT - 50, (255, 200, 120))
            if mission["type"] == "destroy_green": draw_text(screen, f"{mission['progress']}/{mission['total']}", 18, 370, SCREEN_HEIGHT - 50, COLORS["green"])
        if notice > 0: draw_text(screen, "MISSION UPDATED", 22, SCREEN_WIDTH // 2, 20, COLORS["phone"], center=True)
        pygame.display.flip()


def main():
    run_intro_if_needed()
    start_menu_music()
    while True:
        choice = main_menu()
        if choice == "Start":
            stop_menu_music()
            show_loading_transition(1.1)
            result = game_loop()
            if result == "GameOver":
                start_menu_music()
                while True:
                    screen.fill((0, 0, 0))
                    draw_text(screen, "WASTED", 84, SCREEN_WIDTH // 2, 178, (220, 50, 50), center=True)
                    draw_text(screen, "ENTER menu", 26, SCREEN_WIDTH // 2, 288, COLORS["white"], center=True)
                    draw_text(screen, "ESC exit", 22, SCREEN_WIDTH // 2, 322, (165, 165, 165), center=True)
                    pygame.display.flip()
                    action = None
                    for e in pygame.event.get():
                        if e.type == pygame.QUIT: action = "Exit"
                        if e.type == pygame.KEYDOWN:
                            if e.key == pygame.K_RETURN: action = "Menu"
                            if e.key == pygame.K_ESCAPE: action = "Exit"
                    if action == "Menu": break
                    if action == "Exit":
                        stop_menu_music()
                        pygame.quit()
                        sys.exit()
            elif result == "Exit":
                break
            else:
                start_menu_music()
        elif choice == "Options":
            options_menu()
        elif choice == "Skip Intro":
            settings["show_intro"] = False
        elif choice == "Exit":
            break
    stop_menu_music()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
