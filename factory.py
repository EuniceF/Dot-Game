"""Factory classes for Dots & Co game

While quite concise, the purpose of these classes is to manage creation of instances (of dots, etc.). By having a
class managing this process, hooking into and extending this process becomes quite simple (through inheritance). This
allows for interesting things to be done, such as rigging a factory to ensure a game can be played a certain way.
"""

#
#                         /-------------\
#                        /               \
#                       /                 \
#                      /                   \
#                      |   XXXX     XXXX   |
#                      |   XXXX     XXXX   |
#                      |   XXX       XXX   |
#                      \         X         /
#                       --\     XXX     /--
#                        | |    XXX    | |
#                        | |           | |
#                        | I I I I I I I |
#                        |  I I I I I I  |
#                         \              /
#                           --         --
#                             \-------/
#                     XXX                    XXX
#                   XXXXX                  XXXXX
#                   XXXXXXXXX         XXXXXXXXXX
#                           XXXXX   XXXXX
#                             XXXXXXX
#                           XXXXX   XXXXX
#                   XXXXXXXXX         XXXXXXXXXX
#                   XXXXX                  XXXXX
#                     XXX                    XXX
#                           **************
#                           *  BEWARE!!  *
#                           **************
#                       All ye who enter here:
#                  Most of the code in this module
#                      is twisted beyond belief!
#                         Tread carefully
#                  If you think you understand it,
#                             You Don't,
#                           So Look Again
#

from abc import ABC, abstractmethod

from cell import Cell, VoidCell
from dot import AbstractKindlessDot

__author__ = "Benjamin Martin and Brae Webb"
__copyright__ = "Copyright 2017, The University of Queensland"
__license__ = "MIT"
__version__ = "1.1.2"


class AbstractFactory(ABC):
    """Abstract factory"""

    @abstractmethod
    def generate(self, position):
        """(*) Abstract method to return a new instance

        Parameters:
            position (tuple<int, int>) The (row, column) position of the dot
        """
        raise NotImplementedError


class WeightedFactory(AbstractFactory):
    """Factory to generate instances based upon WeightedSelector value"""

    def __init__(self, selector, constructor):
        """Constructor

        Parameters:
            selector (WeightedSelector): The weighted selector to choose from
            constructor (WeightedSelector): A weighted selector to choose
                                            the constructor class from
        """
        self._selector = selector
        self._constructor = constructor

    def generate(self, position):
        """(*) Generates a new instance"""
        constructor = self._constructor.choose()
        return constructor(self._selector.choose())


class CellFactory(AbstractFactory):
    """A basic factory for grid cells determined by a set of dead cells

    Generates a VoidCell for every position in dead cells, otherwise Cell
    """

    def __init__(self, dead_cells=None):
        """
        Constructor

        Parameters:
            dead_cells (set<tuple<int, int>>): Set of cells that are disabled (i.e. VoidCells) 
        """
        if dead_cells is None:
            dead_cells = set()
        self._dead_cells = dead_cells

    def generate(self, position):
        """(*) Generates a new dot"""
        return Cell(None) if position not in self._dead_cells else VoidCell()


class DotFactory(AbstractFactory):
    """Factory to generate dot instances"""

    def __init__(self, selector, constructor):
        """Constructor

        Parameters:
            selector (WeightedSelector): The weighted selector to choose from
            constructor (WeightedSelector): A weighted selector to choose
                                            the constructor class from
        """
        self._selector = selector
        self._constructor = constructor

    def generate(self, position):
        """(*) Generates a new dot"""
        constructor = self._constructor.choose()

        if issubclass(constructor, AbstractKindlessDot):
            return constructor()

        return constructor(self._selector.choose())
