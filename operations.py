import numpy as np 
import re


def dir_to_enum(dirx, diry):
    s = ""
    if diry == 1:
        s += "Up"
    if diry == -1:
        s += "Down"
    if dirx == 1:
        s += "Right"
    if dirx == -1:
        s += "Left"
    return s

def enum_to_dir(s):
    dirx = 0
    diry = 0
    if "Up" in s:
        diry = 1
    if "Down" in s:
        diry = -1
    if "Right" in s:
        dirx = 1
    if "Left" in s:
        dirx = -1
    return dirx, diry

class MoveOperation:
    def from_engine_call(ship, engine_call):
        n = re.findall(r'(?:engine\.p_move\(&Some)\((\d+)\)(?:\))',engine_call)[0]
        return MoveOperation(ship, int(n))
    def __init__(self, ship, n):
        self.ship = ship
        self.n = n
        self.dirx = ship.internal_dirx
        self.diry = ship.internal_diry
    def execute(self):
        self.ship.trail.append((self.ship.x, self.ship.y))
        self.ship.x += self.dirx * self.n
        self.ship.y += self.diry * self.n
        self.ship.fuel -= self.ship.move_cost * self.n
        self.ship.call_count += 1
    def undo(self):
        self.ship.trail.pop()
        self.ship.x -= self.dirx * self.n
        self.ship.y -= self.diry * self.n
        self.ship.fuel += self.ship.move_cost * self.n
        self.ship.call_count -= 1
    def engine_call(self):
        return "engine.p_move(&Some({}));".format(self.n)
    def __str__(self):
        return "MoveOp n:{} ({},{})".format(self.n, self.dirx, self.diry)

class TurnOperation:
    def from_engine_call(ship, engine_call):
        dir_str = re.findall(r'(?:engine\.p_turn\(&Direction::)([a-zA-Z]+)(?:\))',engine_call)[0]
        dirx, diry = enum_to_dir(dir_str)
        ship.dirx = dirx
        ship.diry = diry
        return TurnOperation(ship)
    def __init__(self, ship):
        self.ship = ship
        self.dirx = ship.dirx
        self.diry = ship.diry
        self.old_internal_dirx = ship.internal_dirx
        self.old_internal_diry = ship.internal_diry
    def execute(self):
        self.ship.internal_dirx = self.dirx
        self.ship.internal_diry = self.diry
        self.ship.call_count += 1
        self.ship.fuel -= self.ship.turn_cost
    def undo(self):
        self.ship.dirx = self.old_internal_dirx
        self.ship.diry = self.old_internal_diry
        self.ship.internal_dirx = self.old_internal_dirx
        self.ship.internal_diry = self.old_internal_diry
        self.ship.call_count -= 1
        self.ship.fuel += self.ship.turn_cost
    def engine_call(self):
        return "engine.p_turn(&Direction::{});".format(dir_to_enum(self.dirx, self.diry))
    def __str__(self):
        return "TurnOp new({},{})".format(self.dirx, self.diry)

class ShootOperation:
    def __init__(self, ship, galaxy):
        self.ship = ship
        self.galaxy = galaxy
        self.affected_asteroids = []
        self.old_dirx = ship.dirx
        self.old_diry = ship.diry
        self.shot_pos_x = ship.x
        self.shot_pos_y = ship.y
    def execute(self):
        self.ship.fuel -= self.ship.shoot_cost
        self.ship.call_count += 1
        for (x, y), t in self.galaxy.items():
            if t != "asteroid":
                continue
            if (x,y) == self.ship.dir(0) or (x,y) == self.ship.dir(1) or (x,y) == self.ship.dir(2) or (x,y) == self.ship.dir(3):
                self.affected_asteroids.append((x, y))
                self.galaxy[x, y] = "was-asteroid"
        self.ship.score += len(self.affected_asteroids)
        for (x, y) in self.affected_asteroids:
            self.ship.shots.append((self.shot_pos_x, self.shot_pos_y, x, y))
    def undo(self):
        self.ship.fuel += self.ship.shoot_cost
        self.ship.call_count -= 1
        self.ship.score -= len(self.affected_asteroids)
        for (x, y) in self.affected_asteroids:
            self.galaxy[x, y] = "asteroid"
            self.ship.shots.pop()
    def engine_call(self):
        return "engine.p_shoot();"
    def __str__(self):
        return "ShootOp hit:{} dir({},{})".format(len(self.affected_asteroids), self.old_dirx, self.old_diry)

class RefuelOperation:
    def __init__(self, ship, galaxy):
        self.ship = ship
        self.galaxy = galaxy
        self.fuel = []
        self.old_dirx = ship.dirx
        self.old_diry = ship.diry
    def execute(self):
        self.ship.call_count += 1
        for (x, y), t in self.galaxy.items():
            if t != "fuel":
                continue
            if x == self.ship.x and y == self.ship.y:
                self.fuel.append((x, y))
                self.ship.fuel += 100
                self.galaxy[x, y] = "was-fuel"
    def undo(self):
        self.ship.call_count -= 1
        for (x, y) in self.fuel:
            self.galaxy[x, y] = "fuel"
            self.ship.fuel -= 100
    def engine_call(self):
        return "engine.p_harvest();"
    def __str__(self):
        return "RefuelOp hit:{}".format(len(self.fuel))

class UpgradeOperation:
    def __init__(self, ship):
        self.ship = ship
        self.old_dirx = ship.dirx
        self.old_diry = ship.diry
    def execute(self):
        self.ship.call_count += 1
        self.ship.score -= 5
        self.ship.shoot_cost = 2
        self.ship.move_cost = 1
        self.ship.turn_cost -= 0
    def undo(self):
        self.ship.call_count -= 1
        self.ship.score += 5
        self.ship.shoot_cost = 5
        self.ship.move_cost = 2
        self.ship.turn_cost = 1
    def engine_call(self):
        return "engine.p_upgrade();"
    def __str__(self):
        return "UpgradeOp"