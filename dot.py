"""Dot classes for Dots & Co game mode"""

# To understand recursion, see the bottom of this file

from abc import ABC, abstractmethod

__author__ = "Benjamin Martin and Brae Webb"
__copyright__ = "Copyright 2017, The University of Queensland"
__license__ = "MIT"
__version__ = "1.1.2"


class AbstractDot(ABC):
    """Abstract representation of a dot"""
    DOT_NAME = "abstract"
    PRIORITY = 0

    def __init__(self, kind):
        """Constructor

        Parameters:
             kind (*): The dot's kind
        """
        self._kind = kind
        self._expired = False

    def get_kind(self):
        """(*) Returns the kind of this dot"""
        return self._kind

    def set_kind(self, kind):
        """Sets the kind of the dot, unless the kind cannot be changed

        Parameters:
            kind (*): The kind to set the dot to
        """
        if self._kind is not None:
            self._kind = kind

    @abstractmethod
    def get_view_id(self):
        """(str) Returns a unique identifier for the view (i.e. an image path)"""
        raise NotImplementedError()

    @classmethod
    def get_name(cls):
        """Returns the name of this dot"""
        return cls.DOT_NAME

    # Note:
    #   The activated & activated neighbours parameters should really be an
    #   ordered set, to retain order *and* efficient lookup (position in set
    #   vs. position in list), but for simplicity, a list has been used
    @abstractmethod
    def activate(self, position, game, activated, has_loop=False):
        """
        Called when this dot is activated

        Parameters:
            position (tuple<int, int>): The current position of the dot
            game (AbstractGame): The game currently being played
            activated (list<tuple<int, int>>): A list of all neighbouring dots that were activated
            has_loop (bool): True iff the cell was activated as part of a looped selection
             
        Return:
            list<tuple<int, int>>: Returns a list of positions for all dots to be activated & removed
                                   Dots will only be activated if they haven't been activated already
                                   Can return None
        """
        raise NotImplementedError

    @abstractmethod
    def adjacent_activated(self, position, game, activated, activated_neighbours, has_loop=False):
        """
        Called when an adjacent dot(s) is activated

        Parameters:
            position (tuple<int, int>): The current position of the dot
            game (AbstractGame): The game currently being played
            activated (list<tuple<int, int>>): A list of all neighbouring dots that were activated
            activated_neighbours (list<tuple<int, int>>): A list of all neighbouring dots that were activated
            has_loop (bool): True iff the cell was activated as part of a looped selection
             
        Return:
            list<tuple<int, int>>: Returns a list of positions for all dots to be removed
                                   Dots will only be activated if they haven't been activated already
                                   Can return None
        """
        raise NotImplementedError

    @abstractmethod
    def after_resolved(self, position, game):
        """
        Called after grid has resolved

        Parameters:
            position (tuple<int, int>): The current position of the dot
            game (AbstractGame): The game currently being played
            activated (list<tuple<int, int>>): A list of all neighbouring dots that were activated
            activated_neighbours (list<tuple<int, int>>): A list of all neighbouring dots that were activated
             
        Return:
            list<tuple<int, int>>: Returns a list of positions for all dots to be removed
                                   Dots will only be activated if they haven't been activated already
                                   Can return None
        """
        raise NotImplementedError()

    def will_be_removed(self):
        """(bool) Returns True iff dot has been used and is about to be removed"""
        return self._expired

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self._kind)

    def __str__(self):
        return self.__repr__()

    def can_connect(self):
        """Returns True iff this dot is able to connect to others"""
        raise NotImplementedError()


class BasicDot(AbstractDot):
    """A basic dot"""

    DOT_NAME = "basic"

    def activate(self, position, game, activated, has_loop=False):
        self._expired = True

    def adjacent_activated(self, position, game, activated, activated_neighbours, has_loop=False):
        pass

    def after_resolved(self, position, game):
        pass

    def get_view_id(self):
        """(str) Returns a string to identify the image for this dot"""
        return "{}/{}".format(self.get_name(), + self.get_kind())

    def can_connect(self):
        return True


class AbstractKindlessDot(AbstractDot):
    """Abstract class for a dot without a kind"""
    DOT_NAME = "abstract_kindless"

    _kind = None

    def __init__(self):
        super().__init__(None)

    def set_kind(self, kind):
        pass

    def can_connect(self):
        return False


class WildcardDot(AbstractKindlessDot):
    """A dot without a kind that can join to any other kind of dot"""
    DOT_NAME = 'wildcard'

    def get_view_id(self):
        return "{0}/{0}".format(self.DOT_NAME)

    def adjacent_activated(self, position, game, activated, activated_neighbours, has_loop=False):
        pass

    def activate(self, position, game, activated, has_loop=False):
        self._expired = True

    def after_resolved(self, position, game):
        pass

    def can_connect(self):
        return True

# To understand recursion, see the top of this file
