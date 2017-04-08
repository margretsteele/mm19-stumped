# This is where you build your AI for the Stumped game.

from joueur.base_ai import BaseAI
from math import floor, ceil
from random import random
import collections

# Simply returns a random element of an array
def random_element(items):
    if items:
        return items[floor(random()*len(items))]

    return None

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
        EMPLOYED_BEAVERS = collections.defaultdict(int)
        for beaver in self.player.beavers:
            EMPLOYED_BEAVERS[beaver.job] += 1

        for lodge in self.player.lodges:
            if lodge.beaver: continue
            alive_beavers = len([beaver for beaver in self.player.beavers if beaver.health > 0])
            builder = JOBS['Builder']
            fighter = JOBS['Fighter']

            job = fighter if EMPLOYED_BEAVERS[fighter] < 3 else builder
            if alive_beavers < self.game.free_beavers_count or lodge.food >= job.cost:
                print('Recruiting {} to {}'.format(job, lodge))
                job.recruit(lodge)

        for beaver in self.player.beavers:
            self.do_something(beaver)
        return True

    def do_something(self, beaver):
        if beaver and beaver.turns_distracted == 0 and beaver.health > 0:
            if beaver.moves >= 2:
                if beaver.job == JOBS['Fighter']:
                    path = self.find_path_to_goal(beaver.tile, self.punching_bag)
                else:
                    path = self.find_path_to_goal(beaver.tile, self.source_of_sticks)
                if beaver.tile.lodge_owner == self.player:
                    path = self.find_path_to_goal(beaver.tile, self.not_my_lodge)
                    if len(path) > 0:
                        beaver.move(path[0])
                if len(path) > 1:
                    print('Moving {} towards {}'.format(beaver, path[-1]))
                    beaver.move(path[0])


            if beaver.actions > 0:
                load = beaver.branches + beaver.food

                # if can lodge, lodge yo
                if (beaver.branches + beaver.tile.branches) >= self.player.branches_to_build_lodge and not beaver.tile.lodge_owner:
                    print('{} building lodge'.format(beaver))
                    beaver.build_lodge()

                # Do a random action!
                action = random_element(['pickup', 'drop', 'harvest'])
                if beaver.job == JOBS['Fighter']:
                    action = 'attack'

                if action == 'attack':
                    for neighbor in shuffled(beaver.tile.get_neighbors()):
                        if neighbor.beaver and neighbor.beaver.owner == self.player.opponent:
                            print('{} attacking {}'.format(beaver, neighbor.beaver))
                            beaver.attack(neighbor.beaver)
                            break

                elif action == 'pickup':
                    neighbors = beaver.tile.get_neighbors()
                    neighbors.append(beaver.tile)
                    pickup_tiles = shuffled(neighbors)

                    if load < beaver.job.carry_limit:
                        for tile in pickup_tiles:
                            if tile.lodge_owner == self.player:
                                continue
                            # try to pickup branches
                            if tile.branches > 0:
                                print('{} picking up branches'.format(beaver))
                                beaver.pickup(tile, 'branches', 1)
                                break
                            # try to pickup food
                            elif tile.food > 0:
                                print('{} picking up food'.format(beaver))
                                beaver.pickup(tile, 'food', 1)
                                break

                elif action == 'drop':
                    neighbors = beaver.tile.get_neighbors()
                    neighbors.append(beaver.tile)
                    drop_tiles = shuffled(neighbors)

                    tile_to_drop_on = None
                    for tile in drop_tiles:
                        if not tile.spawner:
                            tile_to_drop_on = tile
                            break

                    if tile_to_drop_on:
                        if beaver.branches > 0:
                            print('{} dropping 1 branch'.format(beaver))
                            beaver.drop(tile_to_drop_on, 'branches', 1)
                        elif beaver.food > 0:
                            print('{} dropping 1 food'.format(beaver))
                            beaver.drop(tile_to_drop_on, 'food', 1)

                elif action == 'harvest':
                    if load < beaver.job.carry_limit:
                        for neighbor in shuffled(beaver.tile.get_neighbors()):
                            if neighbor.spawner and neighbor.lodge_owner != self.player:
                                print('{} harvesting {}'.format(beaver, neighbor.spawner))
                                beaver.harvest(neighbor.spawner)
                                break

    def find_path_to_tile(self, start, goal):
        def p(t):
            return t == goal
        return self.find_path_to_goal(start, p)

    def find_path_to_goal(self, start, predicate):
        """A more advanced path finder that (but still BFS) that takes a
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

                if neighbor and neighbor.id not in came_from and neighbor.is_pathable() and neighbor.lodge_owner != self.player:
                    fringe.append(neighbor)
                    came_from[neighbor.id] = inspect

        return []

    def source_of_sticks(self, t):
        """a tile where I can pick up sticks"""
        return t.spawner and not t.spawner.has_been_harvested and t.spawner.type == 'branches'

    # enemy beaver
    def punching_bag(self, t):
        """a tile where I can hit something"""
        return t.beaver and t.beaver.owner == self.player.opponent

    # enemy lodge
    def bad_lodge(self, t):
        """a tile containing a hostile lodge"""
        return t.lodge_owner == self.player.opponent

    # food source
    def source_of_food(self, t):
        """a tile where I can pick up sticks"""
        return t.spawner and not t.spawner.has_been_harvested and t.spawner.type == 'food'

    def not_my_lodge(self, t):
        """not my lodge"""
        return t.lodge_owner != self.player