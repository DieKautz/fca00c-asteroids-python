import pygame
import numpy as np

from operations import *

version = "1.6.0"

pygame.init()
d_width = 1200
d_height = 750
should_grid_size_px = 10
grid_size_px = 10
camera_x = -int(d_width / 2) + 8 * grid_size_px
camera_y = -int(d_height / 2) + 8 * grid_size_px
camera_follow = True

helpers = False
small_grid = False

pygame.font.init()
font = pygame.font.SysFont(None, 30)
font_small = pygame.font.SysFont(None, 14)
screen = pygame.display.set_mode((d_width, d_height))
pygame.display.set_caption("FCA00C - Asteroid Game v" + version)
pygame.mouse.set_visible(False)

galaxy = {}
for ast_x, ast_y in np.loadtxt("asteroids.txt", delimiter=',', dtype=int):
    galaxy[(ast_x, ast_y)] = "asteroid"
for fuel_x, fuel_y in np.loadtxt("fuel.txt", delimiter=',', dtype=int):
    galaxy[(fuel_x, fuel_y)] = "fuel"


ship_color = (144, 190, 109)
in_range_color = (249, 65, 68)
ship_next_color = (144, 190, 109)
asteroid_color = (243, 114, 44) 
fuel_color = (40, 154, 24)
background_color = (39, 125, 161)
grid_color = (38, 12, 0)
grid_bold_color = (200, 200, 200)
text_color = (50, 50, 50)

def chebychev_distance(x1, y1, x2, y2):
    return max(abs(x1 - x2), abs(y1 - y2))

def draw_circle(color, x, y, radius, width=0):
    pygame.draw.circle(screen, color, 
        (x*grid_size_px+grid_size_px/2 - camera_x, y*grid_size_px+grid_size_px/2 - camera_y),
    radius, width)
def draw_rect(color, x, y, w, h, width=0):
    pygame.draw.rect(screen, color, (x*grid_size_px - camera_x, y*grid_size_px - camera_y, w, h), width)
def draw_ellipse(color, x, y, w, h, width=0):
    pygame.draw.ellipse(screen, color, (x*grid_size_px - camera_x, y*grid_size_px - camera_y, w, h), width)
def draw_line(color, x1, y1, x2, y2, width=1):
    pygame.draw.aaline(screen, color, (x1*grid_size_px+grid_size_px/2 - camera_x, y1*grid_size_px+grid_size_px/2 - camera_y), (x2*grid_size_px+grid_size_px/2 - camera_x, y2*grid_size_px+grid_size_px/2 - camera_y), width)
def draw_lines(color, points, width=1):
    pygame.draw.aalines(screen, color, False, [(p[0]*grid_size_px+grid_size_px/2 - camera_x, p[1]*grid_size_px+grid_size_px/2 - camera_y) for p in points], width)

def draw_fuel(fuel_points):
    percent = max(0, min(1, fuel_points / 100))
    color = (
        int(min(255,512 * (1-percent))),
        int(min(255, 512 * (percent))),
        0
    )
    pygame.draw.rect(screen, color, (0, d_height-20, d_width*percent, 20))
    text = font.render(str(fuel_points), True, text_color)
    text_rect = text.get_rect(center=(d_width/2, d_height-10))
    screen.blit(text, text_rect)
def draw_text_centered(text, x, y, color=text_color, font=font):
    text = font.render(text, True, color)
    text_rect = text.get_rect(center=((x+1)*grid_size_px - camera_x, (y+1)*grid_size_px - camera_y))
    screen.blit(text, text_rect)

def draw_asteroid(x, y, width=0):
    draw_circle(asteroid_color, x, y, width=width, radius=grid_size_px/2)
def draw_fuel_pod(x, y, width=0):
    draw_ellipse(fuel_color, x+1/4, y, w=grid_size_px*1/2, h=grid_size_px, width=width)
def move_camera(x, y):
    global camera_x, camera_y
    camera_x += x
    camera_y += y
def toggle_small_grid():
    global small_grid
    small_grid = not small_grid
def toggle_camera_follow():
    global camera_follow
    camera_follow = not camera_follow
def toggle_helpers():
    global helpers
    helpers = not helpers

def camera_zoom(zoom):
    global should_grid_size_px
    should_grid_size_px = max(1, min(20, should_grid_size_px + zoom))

def print_operations(operations):
    last_dirx = 0
    last_diry = 1
    from tkinter.filedialog import asksaveasfile
    f = asksaveasfile(defaultextension=".txt")
    f.write("\n".join(list(map(lambda op: op.engine_call(), operations[1:]))))

class Ship:
    def apply_file(self, filename):
        lines = open(filename, 'r').readlines()
        for line in lines:
            op = None
            if "turn" in line:
                op = TurnOperation.from_engine_call(self, line)
                op.execute()
                self.operations.append(op)
            elif "move" in line:
                op = MoveOperation.from_engine_call(self, line)
                op.execute()
                self.operations.append(op)
            elif "shoot" in line:
                op = ShootOperation(self, galaxy)
                op.execute()
                self.operations.append(op)
            elif "harvest" in line:
                op = RefuelOperation(self, galaxy)
                op.execute()
                self.operations.append(op)
            elif "upgrade" in line:
                op = UpgradeOperation(self)
                op.execute()
                self.operations.append(op)
            else:
                print("Unknown operation: " + line)
    def __init__(self, x, y, dirx, diry):
        self.x = x
        self.y = y
        self.dirx = dirx
        self.diry = diry
        self.internal_dirx = dirx
        self.internal_diry = diry
        self.upgraded = False
        self.fuel = 50
        self.move_length = 1
        self.move_cost = 2
        self.turn_cost = 1
        self.shoot_cost = 5
        self.score = 0
        self.operations = [MoveOperation(self, 0)]
        self.trail = []
        self.shots = []
    def __str__(self):
        return "X: {} Y: {} move: +{}".format(self.x, self.y, self.move_length)
    def counters(self):
        counter = {"shoot": 0, "harvest": 0, "move": -1, "turn": 0, "upgrade": 0}
        for op in self.operations:
            if isinstance(op, ShootOperation):
                counter["shoot"] += 1
            if isinstance(op, RefuelOperation):
                counter["harvest"] += 1
            if isinstance(op, MoveOperation):
                counter["move"] += 1
            if isinstance(op, TurnOperation):
                counter["turn"] += 1
            if isinstance(op, UpgradeOperation):
                counter["upgrade"] += 1
        return counter
    def highlight_nearest_asteroids(self):
        nearest = []
        nearest_dist = 100000
        for (x, y), t in galaxy.items():
            if t == "asteroid":
                dist = chebychev_distance(self.x, self.y, x, y)
                if dist == nearest_dist:
                    nearest.append((x,y))
                if dist < nearest_dist:
                    nearest = [(x,y)]
                    nearest_dist = dist
        for (x, y) in nearest:
            draw_rect(asteroid_color, x-.2, y-.2, w=grid_size_px*1.4, h=grid_size_px*1.4, width=1)
            draw_text_centered(str(nearest_dist), x-.5, y-.5, font=font_small)
    def highlight_nearest_fuel(self):
        nearest = []
        nearest_dist = 100000
        for (x, y), t in galaxy.items():
            if t == "fuel":
                dist = chebychev_distance(self.x, self.y, x, y)
                if dist == nearest_dist:
                    nearest.append((x,y))
                if dist < nearest_dist:
                    nearest = [(x,y)]
                    nearest_dist = dist
        for (x, y) in nearest:
            draw_rect(fuel_color, x-.2, y-.2, w=grid_size_px*1.4, h=grid_size_px*1.4, width=1)
            draw_text_centered(str(nearest_dist), x-.5, y-.5, font=font_small)
    def dir(self, n):
        return (self.x + self.dirx*n, self.y + self.diry*n)
    def draw_body(self):
        draw_rect(ship_color, self.x, self.y, grid_size_px, grid_size_px)
    def draw_tracers(self):
        for d in range(1, max(4, self.move_length+1)):
            if d <= 3:
                color = in_range_color
            else:
                color = ship_next_color
            draw_circle(color, *self.dir(d), grid_size_px/4)
        draw_rect(ship_next_color, *self.dir(self.move_length), w=grid_size_px, h=grid_size_px, width=1)
    def increase_dist(self):
        self.move_length += 1
    def decrease_dist(self):
        self.move_length = max(1, self.move_length - 1)
    def draw_trail(self):
        if len(self.trail) > 0:
            draw_lines(ship_color, self.trail + [(self.x, self.y)])
            for pos_x, pos_y, ast_x, ast_y in self.shots:
                draw_line(asteroid_color, pos_x, pos_y, ast_x, ast_y, 1)
            for x, y in self.trail:
                draw_circle(background_color, x, y, 4)
    def maybe_turn(self):
        if self.dirx != self.internal_dirx or self.diry != self.internal_diry:
            op = TurnOperation(self)
            op.execute()
            self.operations.append(op)
    def upgrade_if_possible(self):
        if not self.upgraded and self.score >= 5:
            op = UpgradeOperation(self)
            op.execute()
            self.operations.append(op)
    def key_down(self, key):
        if key >= pygame.K_1 and key <= pygame.K_9 or key == pygame.K_SPACE:
            n = key - pygame.K_0
            if key == pygame.K_SPACE:
                n = self.move_length
            self.maybe_turn()
            op = MoveOperation(self, n)
            op.execute()
            self.operations.append(op)
        if key == pygame.K_RETURN:
            self.maybe_turn()
            op = ShootOperation(self, galaxy)
            op.execute()
            if len(op.affected_asteroids) == 0:
                op.undo()
            else:
                self.operations.append(op)
            self.upgrade_if_possible()
        if key == pygame.K_f:
            op = RefuelOperation(self, galaxy)
            op.execute()
            if len(op.fuel) == 0:
                op.undo()
            else:
                self.operations.append(op)
        if key == pygame.K_BACKSPACE and len(self.operations) > 1:
            op = self.operations.pop()
            op.undo()
        if key == pygame.K_a:
            if self.dirx == -1:
                self.diry = 0
            self.dirx = -1
        if key == pygame.K_d:
            if self.dirx == 1:
                self.diry = 0
            self.dirx = 1
        if key == pygame.K_w:
            if self.diry == -1:
                self.dirx = 0
            self.diry = -1
        if key == pygame.K_s:
            if self.diry == 1:
                self.dirx = 0
            self.diry = 1

        if key == pygame.K_PLUS:
            camera_zoom(1)
        if key == pygame.K_MINUS:
            camera_zoom(-1)
        
        if key == pygame.K_g:
            toggle_small_grid()
        if key == pygame.K_h:
            toggle_helpers()
        if key == pygame.K_l:
            toggle_camera_follow()
        if key == pygame.K_p:
            print_operations(self.operations)
        if key == pygame.K_i:
            from tkinter.filedialog import askopenfilename
            self.apply_file(askopenfilename())
        
        if key == pygame.K_LEFT and not camera_follow:
            move_camera(-grid_size_px, 0)
        if key == pygame.K_RIGHT and not camera_follow:
            move_camera(grid_size_px, 0)
        if key == pygame.K_UP and not camera_follow:
            move_camera(0, -grid_size_px)
        if key == pygame.K_DOWN and not camera_follow:
            move_camera(0, grid_size_px)

def game_loop(): 
    game_running = True
    ship = Ship(8, 8, 0, 1)

    while game_running:
        for event in pygame.event.get():    
            if event.type == pygame.QUIT:    
                game_running = False
            elif event.type == pygame.KEYDOWN:
                ship.key_down(event.key)
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    ship.increase_dist()
                else:
                    ship.decrease_dist()
        global should_grid_size_px, grid_size_px
        grid_size_px += (should_grid_size_px - grid_size_px)/10
        if abs(should_grid_size_px - grid_size_px) < 0.01:
            grid_size_px = should_grid_size_px
        
        camera_should_x = ship.x*grid_size_px - d_width/2
        camera_should_y = ship.y*grid_size_px - d_height/2
        global camera_x, camera_y
        if camera_follow and (abs(camera_should_x - camera_x) > 1 or abs(camera_should_y - camera_y) > 1):
            camera_x += (camera_should_x - camera_x)/10
            camera_y += (camera_should_y - camera_y)/10

        screen.fill(background_color)
        
        for (x, y) in np.ndindex((int(d_width/grid_size_px)+1, int(d_height / grid_size_px)+1)):
            x += int(camera_x/grid_size_px)
            y += int(camera_y/grid_size_px)
            if x % 17 == 0 or y % 17 == 0:
                draw_circle(grid_bold_color, x-0.5, y-0.5, 1)
            if helpers and x % 17 == 8 and y % 17 == 8:
                draw_text_centered("{:.0f}, {:.0f}".format((x-8)/17, (y-8)/17), x, y, [max(50, x-50) for x in background_color])
            if small_grid:
                draw_circle(grid_color, x, y, 1)

        ship.draw_body()        
        ship.draw_trail()

        for (x, y), t in galaxy.items():
            if t == "asteroid":
                draw_asteroid(x, y)
            elif t == "fuel":
                draw_fuel_pod(x, y)
            elif t == "was-asteroid":
                draw_asteroid(x, y, width=1)
            elif t == "was-fuel":
                draw_fuel_pod(x, y, width=1)

        ship.draw_tracers()

        if helpers:
            ship.highlight_nearest_fuel()
            ship.highlight_nearest_asteroids()
            
        if pygame.mouse.get_focused():
            (mouse_x, mouse_y) = pygame.mouse.get_pos()
            mouse_x = round((mouse_x + camera_x)/grid_size_px - 0.5)
            mouse_y = round((mouse_y + camera_y)/grid_size_px - 0.5)
            draw_rect(text_color, mouse_x-.2, mouse_y-.2, w=grid_size_px*1.4, h=grid_size_px*1.4, width=1)
            draw_text_centered("{} {}".format((mouse_x, mouse_y), chebychev_distance(ship.x, ship.y, mouse_x, mouse_y)), mouse_x+1, mouse_y+1)

        text_surface = font.render(str(ship) + " cam_lock: {}".format(camera_follow), True, text_color)
        screen.blit(text_surface, (0,0))

        text_surface = font.render(str(ship.counters()), True, text_color)
        screen.blit(text_surface, (0,20))

        text = font.render("{} points".format(ship.score), True, ship_color)
        text_rect = text.get_rect(center=(d_width/2, d_height-50))
        screen.blit(text, text_rect)

        draw_fuel(ship.fuel)
        pygame.display.flip()  

if __name__ == "__main__":
    game_loop()