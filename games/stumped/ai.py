# This is where you build your AI for the Stumped game.

from joueur.base_ai import BaseAI
from math import floor, ceil
from random import random
import collections

# Simply returns a shuffled copy of an array
def shuffled(a):
    if a:
        for i in range(len(a)-1, -1, -1):
            j = floor(random() * i)
            x = a[i - 1]
            a[i - 1] = a[j]
            a[j] = x
        return a

    return None

JOBS = {}

class AI(BaseAI):
    """ The basic AI functions that are the same between games. """
    claimed_tiles = set()

    def get_name(self):
        """ This is the name you send to the server so your AI will control the player named this string.

        Returns
            str: The name of your Player.
        """
        return "woody--the-low-hanging-fruit"

    def start(self):
        """ This is called once the game starts and your AI knows its playerID and game. You can initialize your AI here.
        """
        # replace with your start logic
        for job in self.game.jobs:
            JOBS[job.title] = job

    def game_updated(self):
        """ This is called every time the game's state updates, so if you are tracking anything you can update it here.
        """
        # replace with your game updated logic

    def end(self, won, reason):
        """ This is called when the game ends, you can clean up your data and dump files here if need be.

        Args:
            won (bool): True means you won, False means you lost.
            reason (str): The human readable string explaining why you won or lost.
        """
        # replace with your end logic

    def run_turn(self):
        self.sing()
        EMPLOYED_BEAVERS = collections.defaultdict(int)
        self.claimed_tiles = set()
        for beaver in self.player.beavers:
            EMPLOYED_BEAVERS[beaver.job] += 1

        alive_beavers = len([beaver for beaver in self.player.beavers if beaver.health > 0])
        for lodge in self.player.lodges:
            if lodge.beaver: continue
            builder = JOBS['Builder']
            bulky   = JOBS['Bulky']
            cleanup = JOBS['Hungry']

            job = cleanup if EMPLOYED_BEAVERS[cleanup] < 2 else builder
            job = bulky if EMPLOYED_BEAVERS[bulky] < 3 else job
            job = builder if EMPLOYED_BEAVERS[builder] < 4 else job
            if alive_beavers < self.game.free_beavers_count or lodge.food >= job.cost:
                print('Recruiting {} to {}'.format(job, lodge))
                job.recruit(lodge)
                alive_beavers += 1

        for beaver in self.player.beavers:
            self.do_something(beaver)
        return True

    def move_beaver(self, beaver):
        MIN_PATH_LENGTH = 1
        # are sitting on our lodge or not
        if beaver.tile.lodge_owner == self.player:
            path = self.find_path_to_goal(beaver.tile, self.not_my_lodge)
            MIN_PATH_LENGTH = 0
            distpath = self.find_path_to_goal(beaver.tile, self.punching_bag)
            if len(distpath) > 10:
                if beaver.job in [JOBS['Builder'], JOBS['Hungry']]:
                    amount = min(beaver.job.carry_limit - (beaver.branches + beaver.food),
                                 beaver.tile.branches - 2)
                    if amount > 0:
                        beaver.pickup(beaver.tile, 'branches', amount)
        elif beaver.job == JOBS['Bulky']:
            path = self.find_path_to_goal(beaver.tile, self.punching_bag)
        elif beaver.job == JOBS['Hungry']:
            if beaver.branches + beaver.food < beaver.job.carry_limit:
                path = self.find_path_to_goal(beaver.tile, self.pile_of_sticks)
                if path: self.claimed_tiles.add(path[-1])
            else:
                path = self.find_path_to_goal(beaver.tile, self.friendly_builder)
        else:  # beaver.job == JOBS['Builder']
            path = self.find_path_to_goal(beaver.tile, self.source_of_sticks)
            if path: self.claimed_tiles.add(path[-1])
            if len(path) > 1:  # we are leaving, pick up your pile
                if beaver.tile.branches > 0:
                    amount = min(beaver.job.carry_limit - (beaver.branches + beaver.food),
                                 beaver.tile.branches)
                    if amount > 0:
                        beaver.pickup(beaver.tile, 'branches', amount)


        if len(path) > MIN_PATH_LENGTH:
            #print('Moving {} towards {}'.format(beaver, path[-1]))
            beaver.move(path[0])

    def do_something(self, beaver):
        if beaver and beaver.turns_distracted == 0 and beaver.health > 0:
            if beaver.moves >= 2:
                self.move_beaver(beaver)

            if beaver.actions > 0:
                # if can lodge, lodge yo
                if (beaver.branches + beaver.tile.branches) >= self.player.branches_to_build_lodge and not beaver.tile.lodge_owner and not beaver.tile.spawner:
                    print('{} building lodge'.format(beaver))
                    beaver.build_lodge()
                    return

                if beaver.job == JOBS['Bulky']:
                    self.attack(beaver)
                elif beaver.job == JOBS['Hungry']:
                    self.cleanup(beaver)
                else: # if we are a builder
                    self.harvest(beaver)

            # second chance to move, after acting
            if beaver.moves >= 2:
                self.move_beaver(beaver)


    def cleanup(self, beaver):
        load = beaver.branches + beaver.food
        # if an undistracted enemy is in range of us, priority distract
        for tile in beaver.tile.get_neighbors():
            if tile.beaver and tile.beaver.owner == self.player.opponent and tile.beaver.turns_distracted == 0:
                print('{} distracting {}'.format(beaver, tile.beaver))
                beaver.attack(tile.beaver)
                return

        # pickup
        if load < beaver.job.carry_limit:
            neighbors = beaver.tile.get_neighbors()
            neighbors.append(beaver.tile)
            pickup_tiles = shuffled(neighbors)

            for tile in pickup_tiles:
                if tile.lodge_owner == self.player:
                    continue
                # try to pickup branches
                if tile.branches > 0:
                    pick_up_amnt = min((beaver.job.carry_limit - load), tile.branches)
                    print('{} picking up {} branches'.format(beaver, pick_up_amnt))
                    beaver.pickup(tile, 'branches', pick_up_amnt)
                    break
                # try to pickup food
                elif tile.food > 0:
                    pick_up_amnt = min((beaver.job.carry_limit - load), tile.food)
                    print('{} picking up {} food'.format(beaver, pick_up_amnt))
                    beaver.pickup(tile, 'food', pick_up_amnt)
                    break
        # drop
        else:
            tile_to_drop_on = None
            neighbors = beaver.tile.get_neighbors()
            drop_tiles = shuffled(neighbors)
            for neighbor in drop_tiles:
                if self.friendly_builder(neighbor):
                    tile_to_drop_on = neighbor
                    break

            if tile_to_drop_on:
                if beaver.branches > 0:
                    print('{} dropping {} branch'.format(beaver, beaver.branches))
                    beaver.drop(tile_to_drop_on, 'branches', beaver.branches)
                elif beaver.food > 0:
                    print('{} dropping {} food'.format(beaver, beaver.food))
                    beaver.drop(tile_to_drop_on, 'food', beaver.food)


    def attack(self, beaver):
        if beaver.actions > 0:
            for neighbor in shuffled(beaver.tile.get_neighbors()):
                if self.punching_bag(neighbor):
                    print('{} attacking {}'.format(beaver, neighbor.beaver))
                    beaver.attack(neighbor.beaver)
                    break

    def harvest(self, beaver):
        if beaver.branches < beaver.job.carry_limit:
            for neighbor in shuffled(beaver.tile.get_neighbors()):
                if self.source_of_sticks(neighbor):
                    print('{} harvesting {}'.format(beaver, neighbor.spawner))
                    beaver.harvest(neighbor.spawner)
                    break
        else:
            beaver.drop(beaver.tile, 'branches', beaver.branches)

    def find_path_to_goal(self, start, predicate):
        """A more advanced path finder (but still BFS) that takes a
        predicate function. Returns a valid path from start to the closest
        tile that satisfies the predicatie function.
        """
        if predicate(start): return []

        fringe = []
        came_from = {}

        fringe.append(start)

        while fringe:
            inspect = fringe.pop(0)

            for neighbor in inspect.get_neighbors():
                if predicate(neighbor):
                    path = [neighbor]
                    while inspect != start:
                        path.insert(0, inspect)
                        inspect = came_from[inspect.id]
                    return path

                if neighbor.id not in came_from and not neighbor.beaver and not neighbor.spawner and not neighbor.lodge_owner:
                    fringe.append(neighbor)
                    came_from[neighbor.id] = inspect

        return []

    def source_of_sticks(self, t):
        """a tile where I can harvest sticks (a tree)"""
        return t.spawner and not t.spawner.has_been_harvested and t.spawner.type == 'branches'

    def pile_of_sticks(self, t):
        """or sticks lying around or a lodge"""
        return t.branches > 0 and t.beaver and t.beaver.owner != self.player and t.lodge_owner != self.player and t not in self.claimed_tiles

    # enemy beaver
    def punching_bag(self, t):
        """a tile where I can hit something"""
        return t.beaver and t.beaver.owner == self.player.opponent and t.beaver.health > 0 and t.beaver.recruited

    def friendly_builder(self, t):
        """a tile containing a friendly builder beaver"""
        return t.beaver and t.beaver.owner == self.player and t.beaver.job.title == 'Builder'

    # enemy lodge
    def bad_lodge(self, t):
        """a tile containing a hostile lodge"""
        return t.lodge_owner == self.player.opponent

    # food source
    def source_of_food(self, t):
        """a tile where I can pick up sticks"""
        return t.spawner and not t.spawner.has_been_harvested and t.spawner.type == 'food' and t not in self.claimed_tiles

    def not_my_lodge(self, t):
        """not my lodge"""
        return t.lodge_owner is None and not t.beaver and not t.spawner

    def sing(self):
        if len(self.player.beavers) < 1:
            return
        self.player.beavers[0].log(lyrics[(self.game.current_turn // 2) % len(lyrics)])

lyrics = [
    "Wynona's got herself",
    "a big brown beaver",
    "and she shows it off",
    "to all her friends.",
    "One day, you know,",
    "that beaver tried to leave her,",
    "so she caged him up",
    "with cyclone fence.",
    "Along came Lou",
    "with the old baboon and said",
    "\"I recognize that smell,",
    "Smells like seven layers,",
    "That beaver eatin' Taco Bell!\".",
    "Now Rex he was a Texan",
    "out of New Orleans",
    "and he travelled with the carnival shows.",
    "He ran bumper cars,",
    "sucked cheap cigars",
    "and he candied up his nose.",
    "He got wind of the big brown beaver",
    "So he thought he'd take himself a peek,",
    "but the beaver was quick",
    "and he grabbed him by the kiwis,",
    "and he ain't pissed for a week.",
    "(And a half!)",
    "Wynona took her big brown beaver",
    "and she stuck him up in the air,",
    "said \"I sure do love",
    "this big brown beaver",
    "and I wish I did have a pair.",
    "Now the beaver once slept",
    "for seven days",
    "And it gave us all an awful fright,",
    "So I tickled his chin",
    "and I gave him a pinch",
    "and the bastard tried to bite me.",
    "Wynona loved her big brown beaver",
    "And she stroked him all the time.",
    "She pricked her finger one day",
    "and it occurred to her",
    "she might have a porcupine.",
]