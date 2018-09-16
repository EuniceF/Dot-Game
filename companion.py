"""Companion classes for Dots & Co game mode"""

__author__ = "Benjamin Martin and Brae Webb"
__copyright__ = "Copyright 2017, The University of Queensland"
__license__ = "MIT"
__version__ = "1.1.2"


class AbstractCompanion:
    """Abstract representation of a companion"""
    NAME = 'abstract'
    _charge = None  # initialised in reset

    def __init__(self, max_charge=6):
        """Constructor
        
        Parameters:
            max_charge (int): The amount of charge required to activate the companion
        """
        self.reset()
        self._max_charge = max_charge

    def reset(self):
        """Resets the companion"""
        self._charge = 0

    def charge(self, charge=1):
        """Charges the companion

        Parameters:
            charge (int): Charge to add to the companion's charge
        """
        self._charge += charge

        if self._charge > self._max_charge:
            self._charge = self._max_charge

    def get_charge(self):
        """(int) Returns the total charge of the companion"""
        return self._charge

    def get_max_charge(self):
        """(int) Returns the maximum charge of the companion"""
        return self._max_charge

    def is_fully_charged(self):
        """(bool) Returns True iff the companion is fully charged"""
        return self._charge >= self._max_charge

    @classmethod
    def get_name(cls):
        """(str) Returns the name of this companion"""
        return cls.NAME

    def activate(self, game):
        """Activates the companion's ability

        Parameters:
            game (DotGame): The game being player
            
        Yield:
            None: Once for each step in an animation
            
        Notes:
            Typically, this method will return:
                - game.activate_all(positions): If positions need to be activated
                - None: If no animation needs to occur
        """
        raise NotImplementedError()


class UselessCompanion(AbstractCompanion):
    """A simple companion that does nothing"""

    NAME = 'useless'

    def activate(self, game):
        """Activates the companion's ability

        Parameters:
            game (DotGame): The game being player
        """
        print("Hey! It looks like you’re writing a letter!")
