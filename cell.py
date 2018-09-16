"""Modelling classes for Dots & Co grid cells"""

__author__ = "Benjamin Martin and Brae Webb"
__copyright__ = "Copyright 2017, The University of Queensland"
__license__ = "MIT"
__version__ = "1.1.2"


class AbstractCell:
    """An abstract cell in a Dot & Co grid"""

    def get_dot(self):
        """(Dot) Returns the dot on this cell"""
        raise NotImplementedError()

    def is_enabled(self):
        """(bool) Returns True iff this cell is enabled (a dot can fall into it if empty)"""
        raise NotImplementedError()

    def is_open(self):
        """(bool) Returns True iff this cell is allowed to have connections"""
        raise NotImplementedError()

    def is_unoccupied(self):
        """(bool) Returns True iff this cell is unoccupied"""
        raise NotImplementedError()

    def can_connect(self, other):
        """(bool) Returns True iff this cell can connect to other - not necessarily transitive or anti-symmetric
        
        Parameters:
            other (AbstractCell): The other cell
        """
        raise NotImplementedError()


class Cell(AbstractCell):
    """A cell in a Dot & Co grid"""

    def __init__(self, dot):
        """Constructor

        Parameters:
            dot (Dot): The dot to put in this cell
        """
        self._dot = dot
        self._enabled = True
        self._open = True

    def is_enabled(self):
        """(bool) Returns True iff this cell is enabled (a dot can fall into it if empty)"""
        return self._enabled

    def is_open(self):
        """(bool) Returns True iff this cell is allowed to have connections"""
        return self._open

    def is_unoccupied(self):
        """(bool) Returns True iff this cell is unoccupied"""
        return self.get_dot() is None

    def can_connect(self, other):
        """(bool) Returns True iff this cell can connect to other - not necessarily transitive or anti-symmetric

        Parameters:
            other (AbstractCell): The other cell
        """

        other_dot = other.get_dot()
        dot = self.get_dot()

        if dot is None or other_dot is None:
            return False

        if False in (dot.can_connect(), other_dot.can_connect()):
            return False

        if None in (dot.get_kind(), other_dot.get_kind()):
            return True

        return dot.get_kind() == other_dot.get_kind()

    def get_dot(self):
        """(Dot) Returns the dot on this cell"""
        return self._dot

    def set_dot(self, dot):
        """Sets the dot of this cell to 'dot'"""
        self._dot = dot

    def move_to(self, other):
        """Moves the contents of this cell to other

        Parameters:
            other (Cell): The other (destination) cell
        """
        other.set_dot(self.get_dot())
        self.set_dot(None)

    def swap_with(self, other):
        """Swaps the contents of this cell with other

        Parameters:
            other (Cell): The other (destination) cell
        """
        dot = self.get_dot()
        self.set_dot(other.get_dot())
        other.set_dot(dot)

    def __str__(self):
        """Returns human readable string of this cell & its dot"""
        return "{}({})".format(self.__class__.__name__, self._dot)


class VoidCell(AbstractCell):
    """A cell void in a Dots & Co grid"""

    def get_dot(self):
        """(Dot) Returns None, since no dot exists on this cell"""
        return None

    def is_enabled(self):
        """(bool) Returns False, since void cells can never contain a dot"""
        return False

    def is_open(self):
        """(bool) Returns False, since void cells can never contain a dot"""
        return False

    def is_unoccupied(self):
        """(bool) Returns False, since void cells are never unoccupied"""
        return False

    def can_connect(self, other):
        """(bool) Returns False as void cells cannot connect to anything

        Parameters:
            other (AbstractCell): The other cell
        """
        return False

    def __str__(self):
        """Returns human readable string of this cell"""
        return self.__class__.__name__ + "()"
