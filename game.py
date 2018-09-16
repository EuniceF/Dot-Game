"""Modelling classes for Dots & Co game mode

A game (CoreDotGame) contains a grid (DotGrid)
A grid is filled with cells (AbstractCell)
Normal cells (Cell) can hold a dot (dot.AbstractDot); disabled cells (VoidCell) cannot ever contain a dot 
"""

from enum import Enum

from companion import AbstractCompanion
from factory import AbstractFactory, DotFactory, CellFactory
from modules.ee import EventEmitter
from modules.matrix import Matrix
from modules.weighted_selector import WeightedSelector

__author__ = "Benjamin Martin and Brae Webb"
__copyright__ = "Copyright 2017, The University of Queensland"
__license__ = "MIT"
__version__ = "1.1.2"


class DotGrid(Matrix):
    """Generic Dots & Co game"""

    # pylint: disable=redefined-argument-from-local
    def __init__(self, size, dot_factory, cell_factory=None, animation=True, connected=None):
        """Constructor

        Parameters:
            size (tuple<int, int>): The number of (rows, columns) in the game
            dot_factory (AbstractFactory): The dot generator
            cell_factory (AbstractFactory): Callable to generate cells for each position
            animation (bool): Whether this game animates its resolution steps
            connected (function): Called with (tile, neighbour). Returns True
                                  iff neighbour is connected to tile

        Preconditions:
            connected is reflexive (connected(a, b) == connected(b, a))
        """
        assert isinstance(dot_factory, AbstractFactory)
        assert isinstance(cell_factory, AbstractFactory)

        super().__init__(size)

        self._animation = animation
        self._factory = dot_factory
        if connected is None:
            connected = lambda cell, neighbour: cell.can_connect(neighbour) and neighbour.can_connect(cell)
        self._connected = connected

        self._fill_cells(cell_factory)

    def get_drop_connection(self, position):
        """Returns the position of the cell that would drop its dot to replace the cell at 'position'

        Parameters:
            position (tuple<int, int>): The position of the cell being replaced

        Return:
            tuple<int, int>: The position of the cell that would immediately replace it
            tuple<-1, int>: If no such cell exists (i.e. position is a top-row cell)
        """
        row, column = position

        previous = None
        for row in range(row, -1, -1):
            position = row, column
            cell = self[position]
            if not cell.is_enabled():
                continue

            if previous is not None:
                return position

            previous = position

        if previous is not None:
            return -1, column

    def get_drop_connection_down(self, position):
        """Returns the position of the cell that the cell at position would drop its dot into

        Parameters:
            position (tuple<int, int>): A cell position

        Return:
            tuple<int, int>: The position of the cell that would have its dot replaced by the one 
                             'position', if it were to be dropped
            tuple<-1, int>: If no such cell exists (i.e. position is a bottom-row cell)
        """
        row, column = position

        previous = None
        rows, _ = self.size()
        for row in range(row, rows):
            position = row, column
            cell = self[position]
            if not cell.is_enabled():
                continue

            if previous is not None:
                return position

            previous = position

        if previous is not None:
            return -1, column

    def _fill_cells(self, cell_factory):
        """Fills the grid with cells
        
        Parameters:
            cell_factory: See __init__
        """
        for position in self:
            self[position] = cell_factory.generate(position)

    def fill(self):
        """Fills all empty cells with newly generated dots"""
        for position in self:
            if self[position].is_enabled():
                self[position].set_dot(self.generate_dot(position))

    def find_connected(self, root, positions=None, connected=None):
        """Finds all cells connected to the one at given position

        Parameters:
            root (tuple<int, int>): The (row, column) position of the root cell
            positions (set<tuple<int, int>>): The set of positions to search

        Return:
            set<tuple<int, int>>: A set of (row, column) positions for each
                                  connected dot, including root
        """

        if connected is None:
            connected = self._connected

        # Default to all cells
        if not positions:
            positions = set(self)

        # Perform depth first search on matrix
        # Treat adjacent cells as having edge iff they share the same kind

        # Initialize data structures
        nodes = []
        visited = set()

        nodes.append(root)

        while len(nodes):
            node = nodes.pop()

            if node not in visited:
                visited.add(node)

                # Iterate over adjacent nodes
                for adjacent in self.get_adjacent_cells(node):

                    if adjacent not in positions:
                        continue

                    # Ensure the kind matches
                    if connected(self[root], self[adjacent]):
                        nodes.append(adjacent)

        return visited

    def generate_dot(self, position):
        """Uses the provided dot generator to generate a dot for a position"""
        return self._factory.generate(position)

    def find_all_connected(self):
        """Finds and yields all the connections within the grid

        Yield:
            set<tuple<int, int>>: A set of (row, column) positions for each
                                  connected dot, including root
        """
        positions = set(self)

        while len(positions):
            node = positions.pop()

            connected = self.find_connected(node, positions)

            if not connected:
                continue

            for cell in connected:
                if cell in positions:
                    positions.remove(cell)

            yield connected

    def replace_blanks(self):
        """Replaces any blank dots in the grid and yields at each frame"""
        replacements = self.calculate_replacements()

        # Perform drops
        max_drops = max(r[0] for r in replacements)
        for i in range(max_drops):
            if self._animation:
                yield

            for empties, column, rows in replacements:
                if i >= empties:
                    continue

                for j in range(len(rows) - 1):
                    row = rows[j]

                    position = row, column
                    cell = self[position]

                    if not cell.is_unoccupied():
                        continue

                    above_position = self.get_drop_connection(position)
                    above_cell = self[above_position]

                    if above_cell.get_dot():
                        # print("Moving {}@{} to {}@{}".format(above_cell, above_position, cell, position))
                        above_cell.move_to(cell)

                new_position = rows[-1], column
                new_dot = self.generate_dot(new_position)
                self[new_position].set_dot(new_dot)

        if self._animation:
            yield

    def get_drop_path(self, position):
        """Yields edges along the path from position dots will drop to fill cell at position
        
        Parameter:
            position (tuple<int, int>): The position to hypothetically fill
        
        Yield:
            tuple<tuple<int, int>, tuple<int, int>>:
                Pairs of (position, fill_position), where fill_position is the position of
                the cell whose dot would drop to fill the cell at position
                
                Next yield will use fill_position as position (hence the drop path), repeats
                until position is off the grid
        """
        while True:
            next_position = self.get_drop_connection(position)
            if next_position is None:
                break
            yield position, next_position
            position = next_position

    def calculate_replacements(self):
        """Calculates the drops that need to occur to replace empty dots

        Return:
            (list<tuple<int, int, int>>): A list of the drops that need to occur
                                          for a dot to be replaced. Specified
                                          by a tuple (empties, column, rows)
        """
        rows, columns = self._dim

        drops = []
        drop = []

        for column in range(columns):
            empties = 0

            # find lowest empty cell
            for row in range(rows - 1, -1, -1):
                position = row, column
                cell = self[position]
                if cell.is_unoccupied():
                    break
            else:
                # ignore rows with no changes (consisting of void/full cells)
                continue

            # since rows is positive, row must be defined at this point
            # pylint: disable=undefined-loop-variable
            for position, fill_position in self.get_drop_path((row, column)):
                row, column = position
                cell = self[position]
                dot = cell.get_dot()

                if cell.is_enabled() and dot is None:
                    empties += 1

                if fill_position[0] == -1:
                    if empties == 0:
                        # ignore full rows
                        continue

                    drop.append(row)

                    info = (empties, column, drop)

                    empties = 0
                    drop = []

                    drops.append(info)
                elif empties:
                    drop.append(row)

        return drops

    def serialize(self):
        """
        Serializes this grid

        Return:
            (list<list<tuple<str, int, *>>>): The serialized grid
        """
        grid_list = []
        for row in self.get_rows():
            row_list = []
            for tile in row:
                row_list.append((tile.get_name(), tile.get_kind()))
            grid_list.append(row_list)
        return grid_list

    def _is_border_between(self, cell1, cell2):
        """(bool) Returns True iff there is a border between cell1 & cell2"""
        return (cell1 in self and self[cell1].is_open()) != (cell2 in self and self[cell2].is_open())

    def get_borders(self, is_border_between=None):
        """Yields list of borders, where each border a list of all pairs of cells that are on the border
        
        Parameters:
            is_border_between (callable<cell1, cell2>>): 
                    Returns True iff there is a border between cell1 & cell2,
                    where cell1 & cell2 are cell positions (tuple<int, int>)
                    
        Yield:
            list<tuple<tuple<int, int>, tuple<int, int>>>: List of cell pairs on the border, for each border
        """
        if is_border_between is None:
            is_border_between = self._is_border_between

        return super().get_borders(is_border_between=is_border_between)


class ObjectiveManager:
    """Manages progress towards objectives"""

    def __init__(self, objectives):
        """Constructor
        
        Parameters:
            objectives (list<tuple<AbstractDot, int>>):
                    List of (objective, count) pairs, where count is the 
                    total number of times objective needs to be tallied
        """
        self._objective_counts = list(objectives)
        self.reset()

    def reset(self):
        """Resets the objective progress"""
        self.status = [list(objective) for objective in self._objective_counts]

    def is_complete(self):
        """(bool) Returns True iff all objectives have been reached"""
        return all(objective[1] == 0 for objective in self.status)

    def __len__(self):
        """Returns the total number of objectives (including completed)"""
        return len(self._objective_counts)

    def increase_progress(self, objective, count):
        """Increases the progress of objective by count
        
        Parameters:
            objective (AbstractDot): The objective to count progress towards
            count (int): The amount of progress towards the objective
        
        Return:
            bool: True iff the objective has been reached
        """
        for i, (current_objective, _) in enumerate(self.status):

            if isinstance(objective, type(current_objective)) and \
                            current_objective.get_kind() in (None, objective.get_kind()):
                self.status[i][1] = max(self.status[i][1] - count, 0)

                return True

        return False

    def get_status(self):
        """Returns the current objective status
        
        Return:
            list<tuple<AbstractDot, int>>:
                    List of (objective, remaining) pairs, where remaining is the amount of progress
                    remaining before the corresponding objective is reached
        """
        return self.status


class CoreDotGame(EventEmitter):
    """Simple game of Dots & Co

    Join dots together to activate & remove them
    Join dots in a loop to activate & remove all dots of that kind"""

    class GameState(Enum):
        """Represents state of game (over? won? etc.)"""
        PLAYING = 0
        WON = 1
        LOST = 2

    def __init__(self, dot_factory, size=(6, 6), dead_cells=None,
                 objectives: ObjectiveManager = None, min_group=2, moves=20, animation=True):
        """Constructor

        Parameters:
            dot_factory (AbstractFactory): Factory for creating new dots
            size (tuple<int, int>): The number of (rows, columns) in the game
            dead_cells (set<tuple<int, int>>): Set of cells that are disabled (i.e. VoidCells)
            objectives (ObjectiveManager): Objectives for the game
            min_group (int): The minimum number of dots required for a
                             connected group to be joinable
            moves (int): The number of moves allowed before game over
            animation (bool): If True, animation will be enabled
        """
        self.dot_factory = dot_factory

        super().__init__()

        self.grid = DotGrid(size, self.dot_factory, animation=animation, cell_factory=CellFactory(dead_cells))

        if objectives is None:
            # default to no objectives (infinite play)
            objectives = ObjectiveManager([
                ()
            ])

        self.objectives = objectives

        # Basic properties
        self.min_group = min_group
        self._init_moves = self._moves = moves
        self._animation = animation
        self._resolving = False
        self._connected = []

        self.reset()

    def is_resolving(self):
        """(bool) Returns True iff the game is resolving a move"""
        return self._resolving

    def get_connection_kind(self):
        """(int|str) Returns the kind of the current selection, else None"""

        for position in self._connected:
            dot = self.grid[position].get_dot()

            if dot and dot.get_kind():
                return dot.get_kind()

    def get_connection_path(self):
        """(list<tuple<int, int>>) Returns the selection path, a list of positions,
                                   in the order they were connected"""
        return self._connected

    def has_loop(self):
        """(bool) True iff the current connections have a loop"""
        if not self._connected:
            return False

        visited = set()

        for dot in self._connected:
            if dot in visited:
                return True

            visited.add(dot)
        return False

    def connect(self, position):
        """Adds the dot to the collection of currently connected dots

        Parameters:
            position (tuple<int, int>): The position of the dot to connect
            
        Return:
            bool: True iff a connection was made or removed (including undoing the most recent)
        """

        cell = self.grid[position]
        dot = cell.get_dot()

        # check for disabled cell
        if not cell.is_open():
            return False

        if len(self._connected) == 0:
            if dot and dot.can_connect():
                self._connected.append(position)
            return False

        last_position = self._connected[-1]

        if len(self._connected) >= 2 and position == self._connected[-2]:
            self.undo(position)
            return True

        elif self.grid.are_cells_adjacent(position, last_position):

            connection_kind = self.get_connection_kind()

            if dot.can_connect() and (dot.get_kind() in (connection_kind, None) or connection_kind is None):
                self.emit("connect", last_position, position)
                self._connected.append(position)
                return True

        return False

    def undo(self, dot):
        """Undo all connections up to a specific dot

        Parameters:
            dot (Dot): The new end point for the connection path
        """
        removed = []
        for connected in reversed(self._connected):
            if dot != connected:
                self._connected.pop()
                removed.append(dot)
            else:
                break
        self.emit("undo", removed)

    def get_game_state(self):
        """(GameState) Returns state of the game"""
        if self.objectives.is_complete():  # won!
            return self.GameState.WON
        elif self._moves <= 0:  # lost! (out of moves)
            return self.GameState.LOST

        # check for any possible moves
        for connected in self.grid.find_all_connected():
            if len(connected) < self.min_group:
                continue
            return self.GameState.PLAYING  # underway! (possible move exists)

        return self.GameState.LOST  # lost! (no possible moves exit)

    def reset(self):
        """Resets the game"""
        self._score = 0
        self.grid.fill()
        self.emit('reset')
        self.set_moves(self._init_moves)

    def get_score(self):
        """(int) Returns the score"""
        return self._score

    def get_moves(self):
        """(int) Returns the amount of remaining moves"""
        return self._moves

    def set_moves(self, moves):
        """Sets the amount of remaining moves"""
        self._moves = moves

    # TODO: complete serialise & deserialise
    # def serialize(self):
    #     """Serialize the game into a dictionary
    #
    #     Return:
    #         (dict): The game as a dictionary
    #     """
    #     return {
    #         "size": self.grid.size(),
    #         "min_group": self.min_group,
    #         "moves": self._moves,
    #         "animation": self._animation,
    #         "grid": self.grid.serialize()
    #     }
    #
    # @classmethod
    # def deserialize(cls, grid, dot_weights, *args, **kwargs):
    #     """
    #     Deserializes a game grid
    #
    #     Parameters:
    #         dot_weights (dict<class, float>): The weighting for picking the
    #                                           class of dot to initiate
    #         grid (list<list<tuple<int, int>>>): A serialized grid list to load
    #         *args: Extra positional arguments for the tile
    #         **kwargs: Extra keyword arguments for the tile
    #     """
    #
    #     game = cls(*args, **kwargs)
    #
    #     for row, row_data in enumerate(grid):
    #         for column, data in enumerate(row_data):
    #             name, kind, *rest = data
    #             dot = None
    #             for dot_class in dot_weights:
    #                 if dot_class.get_name() == name:
    #                     dot = dot_class(kind, *rest)
    #             game.grid[(row, column)] = dot
    #
    #     return game

    def add_positions_to_score(self, positions):
        """Updates the score based upon the positions of all dots simultaneously activated

        Parameter:
            positions (list<tuple<int, int>>): The position of the dots to be scored
        """
        dots = (self.grid[position].get_dot() for position in positions)
        self.add_dots_to_score(dots)

    def add_dots_to_score(self, dots):
        """Updates the score based upon dots

        Parameter:
            positions (list<AbstractDot>): The dots to be scored
        """
        dots = list(dot for dot in dots if dot)
        for dot in dots:
            if dot:
                self.objectives.increase_progress(dot, 1)

        self._score += self.calculate_score(dots)

    @staticmethod
    def calculate_score(connected):
        """(int) Calculates & returns the score for a list of connected positions
        
        Parameters:
            connected (list<tuple<int, int>>): (row, column) positions of connected cells
        """
        return len(connected)

    def activate_selected(self):
        """Activates all in current selection (see activate_all)
        
        Yield:
            str: step name for each step in the resulting animation
        """

        to_activate = set(self._connected)
        has_loop = len(to_activate) < len(self._connected)

        if len(to_activate) < self.min_group:
            self._connected = []
            return

        if self._moves > 0:
            self._moves -= 1

        self._resolving = True

        if has_loop:
            # if inner:
            #     score
            #     convert all to bombs

            dot_type = self.get_connection_kind()

            for position, cell in self.grid.items():
                if cell.get_dot() and cell.get_dot().get_kind() == dot_type:
                    to_activate.add(position)

        yield "ACTIVATE_SELECTED"

        yield from self.activate_all(to_activate, has_loop=has_loop)

    # This should be refactored, but doing so would increase the high-level
    # complexity of the game class, so for now it is sufficient
    # pylint: disable=too-many-nested-blocks,too-many-branches
    def activate_all(self, to_activate, has_loop=False):
        """Processes activate hook for all dots to be activated, and 
        adjacent_activated hook for all adjacent dots
        
        Parameters:
            to_activate (set<tuple<int, int>>): Set of grid positions containing dots to be activated
            has_loop (bool): Flag passed on to relevant hooks (activate & adjacent_activated)
        
        Yield:
            str: step name for each step in the resulting animation
        """

        if not isinstance(to_activate, set):
            to_activate = set(to_activate)

        self._resolving = True

        activated = set()
        activated_adjacent = set()

        # get adjacent cells to to_activate
        #  len(to_activate /\ to_activate_adjacent) == 0
        to_activate_adjacent = set()
        for position in to_activate:
            for neighbour in self.grid.get_adjacent_cells(position):
                if neighbour not in to_activate:
                    to_activate_adjacent.add(neighbour)

        # activate all appropriately

        yield "ACTIVATE_ALL"

        while True:
            if len(to_activate):
                position = to_activate.pop()
                dot = self.grid[position].get_dot()
                if not dot:
                    # print(f"No dot for {position}")
                    continue

                extra_positions = dot.activate(position, self, to_activate, has_loop=has_loop)

                activated.add(position)

            elif len(to_activate_adjacent):
                position = to_activate_adjacent.pop()
                dot = self.grid[position].get_dot()
                if not dot:
                    # print(f"No dot for {position}")
                    continue

                activated_neighbours = list(
                    neighbour for neighbour in self.grid.get_adjacent_cells(position) if neighbour in to_activate)

                extra_positions = dot.adjacent_activated(position, self, to_activate,
                                                         activated_neighbours, has_loop=has_loop)

                activated_adjacent.add(position)

            else:
                break

            if extra_positions:
                for extra_position in extra_positions:
                    if extra_position not in activated:
                        to_activate.add(extra_position)

                        for neighbour in self.grid.get_adjacent_cells(extra_position):
                            if neighbour in activated_adjacent or neighbour in to_activate or neighbour in activated:
                                continue

                            to_activate_adjacent.add(neighbour)

                        yield "ACTIVATE"

        self.add_positions_to_score(activated)

        for position in activated:
            self.grid[position].set_dot(None)
        self._connected = []

        yield "ANIMATION_BEGIN"

        for _ in self.grid.replace_blanks():
            yield "ANIMATION_STEP"

        yield "ANIMATION_DONE"

        self._resolving = False

        to_activate = self.after_resolve()

        # TODO: convert to non-recursive
        if to_activate:
            print('More cells to activate')
            yield from self.activate_all(to_activate)
        else:
            print('No more to activate')

            self.emit('complete')
            return

    def after_resolve(self):
        """Processes after_resolve hook for all dots on the grid, highest priority first
        
        Return:
            set(tuple<int, int>): A set of grid positions for all dots that need to be activated
        """
        priorities = {}

        for position, cell in self.grid.items():
            dot = cell.get_dot()

            if not dot:
                continue

            priority = dot.PRIORITY

            if priority not in priorities:
                priorities[priority] = [position]
            else:
                priorities[priority].append(position)

        positions_by_priority = sorted(priorities.items(), reverse=True)

        after_resolved_dots = set()

        for priority, positions in positions_by_priority:
            to_activate = set()

            removed = set()

            for position in positions:
                cell = self.grid[position]
                dot = cell.get_dot()
                if not dot or id(dot) in after_resolved_dots:
                    continue

                after_resolved_dots.add(id(dot))

                extra_positions = dot.after_resolved(position, self)

                if not cell.get_dot():
                    print(f'Removed {position}')
                    removed.add(position)

                if extra_positions:
                    to_activate.update(extra_positions)

            if removed:
                self.add_positions_to_score(removed)

            if to_activate:
                return to_activate

    def drop(self):
        """Drops and returns the current connections
        
        Parameters:
            callback (callable): Callback to be called when animation is complete

        Yield:
            Yields None for each frame of drops and "DONE" when the dropping
            has finished
        """

        return self.activate_selected()

    def remove(self, *positions, callback=lambda: None):
        """Attempts to remove the dot(s) at the given positions"""

        raise NotImplementedError("Deprecated as of 1.1.0")


class DotGame(CoreDotGame):
    """Simple game of Dots & Co

    Join dots together to activate & remove them
    Join dots in a loop to activate & remove all dots of that kind"""

    def __init__(self, dot_weights, kinds=(1, 2, 3), size=(6, 6), dead_cells=None,
                 objectives: ObjectiveManager = None, min_group=2, moves=20, animation=True):
        """Constructor

        Parameters:
            dot_weights (dict<class, float>): The weighting for picking the
                                              class of dot to initiate
            kinds (set<int|str>): All possible kinds that a dot could be
            size (tuple<int, int>): The number of (rows, columns) in the game
            dead_cells (set<tuple<int, int>>): Set of cells that are disabled (i.e. VoidCells)
            objectives (ObjectiveManager): Objectives for the game
            min_group (int): The minimum number of dots required for a
                             connected group to be joinable
            moves (int): The number of moves allowed before game over
            animation (bool): If True, animation will be enabled
        """
        # Tile probabilities
        self.kind_selector = WeightedSelector.from_equals(set(kinds))

        dot_selector = WeightedSelector(dot_weights)
        dot_factory = DotFactory(self.kind_selector, dot_selector)

        super().__init__(dot_factory, size=size, dead_cells=dead_cells, objectives=objectives, min_group=min_group,
                         moves=moves, animation=animation)

class CompanionGame(DotGame):
    """Simple game of Dots & Co, with a Companion

    Join dots together to activate & remove them
    Join dots in a loop to activate & remove all dots of that kind
    Activate companion dots to charge your companion
    """

    def __init__(self, dot_weights, companion: AbstractCompanion, kinds=(1, 2, 3), size=(6, 6), dead_cells=None,
                 objectives: ObjectiveManager = None, min_group=2, moves=20, animation=True):
        self.companion = companion

        super().__init__(dot_weights, kinds=kinds, size=size, dead_cells=dead_cells, objectives=objectives,
                         min_group=min_group, moves=moves, animation=animation)

    def reset(self):
        """Resets the game"""
        self.companion.reset()
        super().reset()
