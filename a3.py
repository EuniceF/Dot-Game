"""
CSSE1001 Assignment 3
Semester 2, 2017
"""

# There are a number of jesting comments in the support code
# They should not be taken seriously. Keep it fun folks :D
# Students are welcome to add their own source code humour, provided it remains civil

import tkinter as tk
from tkinter.messagebox import showinfo
import os
import random
from tkinter import messagebox


try:
    from PIL import ImageTk, Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
import pygame, sys
from pygame.locals import *
from view import GridView, ObjectivesView
from game import DotGame, ObjectiveManager, CompanionGame
from dot import BasicDot, AbstractDot, WildcardDot
from util import create_animation, ImageManager
from companion import AbstractCompanion

# Fill these in with your details
__author__ = "Chen Fang (s4463367)"
__email__ = "chen.fang@uqconnect.edu.au"
__date__ = "24 October, 2017"

__version__ = "1.1.1"


def load_image_pil(image_id, size, prefix, suffix='.png'):
    """Returns a tkinter photo image

    Parameters:
        image_id (str): The filename identifier of the image
        size (tuple<int, int>): The size of the image to load
        prefix (str): The prefix to prepend to the filepath (i.e. root directory
        suffix (str): The suffix to append to the filepath (i.e. file extension)
    """
    width, height = size
    file_path = os.path.join(prefix, f"{width}x{height}", image_id + suffix)
    return ImageTk.PhotoImage(Image.open(file_path))


def load_image_tk(image_id, size, prefix, suffix='.gif'):
    """Returns a tkinter photo image

    Parameters:
        image_id (str): The filename identifier of the image
        size (tuple<int, int>): The size of the image to load
        prefix (str): The prefix to prepend to the filepath (i.e. root directory
        suffix (str): The suffix to append to the filepath (i.e. file extension)
    """
    width, height = size
    file_path = os.path.join(prefix, f"{width}x{height}", image_id + suffix)
    return tk.PhotoImage(file=file_path)


# This allows you to simply load png images with PIL if you have it,
# otherwise will default to gifs through tkinter directly
load_image = load_image_pil if HAS_PIL else load_image_tk  # pylint: disable=invalid-name

DEFAULT_ANIMATION_DELAY = 0  # (ms)
ANIMATION_DELAYS = {
    # step_name => delay (ms)
    'ACTIVATE_ALL': 50,
    'ACTIVATE': 100,
    'ANIMATION_BEGIN': 300,
    'ANIMATION_DONE': 0,
    'ANIMATION_STEP': 200
}


# Define your classes here
# You may edit as much of DotsApp as you wish
class DotsApp:
    """Top level GUI class for simple Dots & Co game"""

    def __init__(self, master):
        """Constructor

        Parameters:
            master (tk.Tk|tk.Frame): The parent widget
        """
        self._master = master
        self._master.title('Dot')
        self._playing = True
        self._image_manager = ImageManager('images/dots/', loader=load_image)

        # initialize pygame
        pygame.init()

        # load background music
        pygame.mixer.music.load('bgm2.ogg')
        pygame.mixer.music.play(-1, 0.0)
        pygame.mixer.music.set_volume(0.3)

        # create an instance of InfoPanel
        self.info_panel=InfoPanel(master)
        self.info_panel.pack()

        # create an instance of IntervalBar
        self.interval_bar=IntervalBar(master)
        self.interval_bar.pack()

        # create an instance of ActionBar
        self.action_bar=ActionBar(master)
        self.action_bar.pack(side=tk.BOTTOM)

        # add command to two button
        self.action_bar.companion_charge().config(command=self.com_button)
        self.action_bar.colour_remove().config(command=self.colour_activate)

        # File menu
        menubar=tk.Menu(self._master)
        # tell master what it's menu is
        self._master.config(menu=menubar)
        filemenu=tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label="New Game(companion)", command=self.reset_with_com)
        filemenu.add_command(label="New Game(no-companion)", command=self.reset_without_com)
        filemenu.add_command(label="Exit", command=self.exit)

        # Game
        counts = [10, 15, 25, 25]
        random.shuffle(counts)
        # randomly pair counts with each kind of dot
        objectives = zip([BasicDot(1), BasicDot(2), BasicDot(4), BasicDot(3)], counts)
        self._objectives = ObjectiveManager(list(objectives))
        # show the objectives
        self._obj=self.info_panel.set_object()
        self._obj.draw(self._objectives.get_status())

        # Game
        dead_cells = {(2, 2), (2, 3), (2, 4),
                      (3, 2), (3, 3), (3, 4),
                      (4, 2), (4, 3), (4, 4),
                      (0, 7), (1, 7), (6, 7), (7, 7)}
        self._game = CompanionGame({BasicDot:1, CompanionDot:1}, companion=EskimoCompanion(),
                                   objectives=self._objectives,kinds=(1, 2, 3, 4), size=(8, 8), dead_cells=dead_cells)

        # show the remaining moves
        moves=self.info_panel.remain_moves()
        moves.config(text=str(self._game.get_moves()))
        # show the scores
        scores=self.info_panel.set_scores()
        scores.config(text=str(self._game.get_score()))

        # control the reset type(with/without companion)
        self._play_with_com = True

        # Grid View
        self._grid_view = GridView(master, size=self._game.grid.size(), image_manager=self._image_manager)
        self._grid_view.pack()
        self._grid_view.draw(self._game.grid)
        self.draw_grid_borders()

        # Events
        self.bind_events()

        # Set initial score again to trigger view update automatically
        self._refresh_status()

    def draw_grid_borders(self):
        """Draws borders around the game grid"""

        borders = list(self._game.grid.get_borders())

        # this is a hack that won't work well for multiple separate clusters
        outside = max(borders, key=lambda border: len(set(border)))

        for border in borders:
            self._grid_view.draw_border(border, fill=border != outside)

    def bind_events(self):
        """Binds relevant events"""
        self._grid_view.on('start_connection', self._drag)
        self._grid_view.on('move_connection', self._drag)
        self._grid_view.on('end_connection', self._drop)

        self._game.on('reset', self._refresh_status)
        self._game.on('complete', self._drop_complete)

        self._game.on('connect', self._connect)
        self._game.on('undo', self._undo)

    def _animation_step(self, step_name):
        """Runs for each step of an animation
        
        Parameters:
            step_name (str): The name (type) of the step    
        """

        # add sound effect
        sound = pygame.mixer.Sound('boble1.wav')
        sound.play()

        print(step_name)
        self._refresh_status()
        self.draw_grid()

    def animate(self, steps, callback=lambda: None):
        """Animates some steps (i.e. from selecting some dots, activating companion, etc.
        
        Parameters:
            steps (generator): Generator which yields step_name (str) for each step in the animation
        """

        if steps is None:
            steps = (None for _ in range(1))

        animation = create_animation(self._master, steps,
                                     delays=ANIMATION_DELAYS, delay=DEFAULT_ANIMATION_DELAY,
                                     step=self._animation_step, callback=callback)
        animation()

    def _drop(self, position):  # pylint: disable=unused-argument
        """Handles the dropping of the dragged connection

        Parameters:
            position (tuple<int, int>): The position where the connection was
                                        dropped
        """
        if not self._playing:
            return

        if self._game.is_resolving():
            return

        self._grid_view.clear_dragged_connections()
        self._grid_view.clear_connections()

        self.animate(self._game.drop())

    def _connect(self, start, end):
        """Draws a connection from the start point to the end point

        Parameters:
            start (tuple<int, int>): The position of the starting dot
            end (tuple<int, int>): The position of the ending dot
        """

        # add sound effect when two connects
        sound = pygame.mixer.Sound('cartoon-boing.ogg')
        sound.play()

        if self._game.is_resolving():
            return
        if not self._playing:
            return
        self._grid_view.draw_connection(start, end,
                                        self._game.grid[start].get_dot().get_kind())

    def _undo(self, positions):
        """Removes all the given dot connections from the grid view

        Parameters:
            positions (list<tuple<int, int>>): The dot connects to remove
        """
        for _ in positions:
            self._grid_view.undo_connection()

    def _drag(self, position):
        """Attempts to connect to the given position, otherwise draws a dragged
        line from the start

        Parameters:
            position (tuple<int, int>): The position to drag to
        """

        if self._game.is_resolving():
            return
        if not self._playing:
            return

        tile_position = self._grid_view.xy_to_rc(position)

        if tile_position is not None:
            cell = self._game.grid[tile_position]
            dot = cell.get_dot()

            if dot and self._game.connect(tile_position):
                self._grid_view.clear_dragged_connections()
                return

        kind = self._game.get_connection_kind()

        if not len(self._game.get_connection_path()):
            return

        start = self._game.get_connection_path()[-1]

        if start:
            self._grid_view.draw_dragged_connection(start, position, kind)

    @staticmethod
    def remove(*_):
        """Deprecated in 1.1.0"""
        raise DeprecationWarning("Deprecated in 1.1.0")

    def draw_grid(self):
        """Draws the grid"""
        self._grid_view.draw(self._game.grid)

    def reset_without_com(self):
        """Resets the game"""

        # initialize pygame
        pygame.init()
        # load background music
        pygame.mixer.music.load('bgm2.ogg')
        pygame.mixer.music.play(-1, 0.0)
        pygame.mixer.music.set_volume(0.3)

        counts = [10, 15, 25, 25]
        random.shuffle(counts)
        # randomly pair counts with each kind of dot
        objectives = zip([BasicDot(1), BasicDot(2), BasicDot(4), BasicDot(3)], counts)
        self._objectives = ObjectiveManager(list(objectives))

        dead_cells = {(2, 2), (2, 3), (2, 4),
                      (3, 2), (3, 3), (3, 4),
                      (4, 2), (4, 3), (4, 4),
                      (0, 7), (1, 7), (6, 7), (7, 7)}
        self._game = DotGame({BasicDot: 1}, objectives=self._objectives, kinds=(1, 2, 3, 4), size=(8, 8),
                             dead_cells=dead_cells)

        # reset the game(score, move)
        self._game.reset()
        # reset the score
        scores = self.info_panel.set_scores()
        scores.config(text=str(self._game.get_score()))
        # reset the move
        moves = self.info_panel.remain_moves()
        moves.config(text=str(self._game.get_moves()))

        # reset the objectives
        self._obj.draw(self._objectives.get_status())

        # reset the grid
        self.draw_grid()

        # reset the interval bar
        self.interval_bar.progress_bar(0)
        self.interval_bar.com_charge_bar_reset()

        # player choose to play without companion
        self._play_with_com = False
        # reset the companion charge button as disable
        self.action_bar.companion_charge().config(state='disable')
        # reset the color remover button
        self.action_bar.colour_remove().config(state='normal')

    def reset_with_com(self):
        # initialize pygame
        pygame.init()
        # load background music
        pygame.mixer.music.load('bgm2.ogg')
        pygame.mixer.music.play(-1, 0.0)
        pygame.mixer.music.set_volume(0.3)

        counts = [10, 15, 25, 25]
        random.shuffle(counts)
        # randomly pair counts with each kind of dot
        objectives = zip([BasicDot(1), BasicDot(2), BasicDot(4), BasicDot(3)], counts)
        self._objectives = ObjectiveManager(list(objectives))

        # reset the objectives
        self._obj.draw(self._objectives.get_status())

        dead_cells = {(2, 2), (2, 3), (2, 4),
                      (3, 2), (3, 3), (3, 4),
                      (4, 2), (4, 3), (4, 4),
                      (0, 7), (1, 7), (6, 7), (7, 7)}
        self._game = CompanionGame({BasicDot: 1, CompanionDot: 1}, companion=EskimoCompanion(),
                                   objectives=self._objectives, kinds=(1, 2, 3, 4), size=(8, 8),
                                   dead_cells=dead_cells)
        # reset the game(score, move)
        self._game.reset()

        # reset the grid
        self.draw_grid()

        # reset the score
        scores = self.info_panel.set_scores()
        scores.config(text=str(self._game.get_score()))
        # reset the move
        moves = self.info_panel.remain_moves()
        moves.config(text=str(self._game.get_moves()))

        # reset the interval bar
        self.interval_bar.progress_bar(0)
        self._game.companion.reset()
        # reset the companion bar
        self.interval_bar.com_charge_bar_reset()
        # reset the companion charge button
        self.action_bar.companion_charge().config(state='normal')
        # reset the color remover button
        self.action_bar.colour_remove().config(state='normal')

    def check_game_over(self):
        """Checks whether the game is over and shows an appropriate message box if so"""
        state = self._game.get_game_state()

        if state == self._game.GameState.WON:
            # load the gamewin music
            pygame.mixer.music.load('breaking slient.ogg')
            pygame.mixer.music.play()
            showinfo("Game Over!", "You won!!!")
            self._playing = False
        elif state == self._game.GameState.LOST:
            # load the gameover music
            pygame.mixer.music.load('gameOver.wav')
            pygame.mixer.music.play()
            showinfo("Game Over!",
                     f"You didn't reach the objective(s) in time. You connected {self._game.get_score()} points")

            self._playing = False

    def _drop_complete(self):
        """Handles the end of a drop animation"""

        # Need to check whether the game is over
        # check whether the game is over
        self.check_game_over()

    def _refresh_status(self):
        """Handles change in score"""

        # Normally, this should raise the following error:
        # raise NotImplementedError()
        # But so that the game can work prior to this method being implemented,
        # we'll just print some information
        # Sometimes I believe Python ignores all my comments :(

        # show the remaining objectives using get_status() function
        self._obj.draw(self._objectives.get_status())

        # show the interval bar(max==6)
        bar_num = (20 - self._game.get_moves()) % 6
        self.interval_bar.progress_bar(bar_num)

        # show the current score
        scores = self.info_panel.set_scores()
        scores.config(text=str(self._game.get_score()))

        # show the remaining moves
        moves = self.info_panel.remain_moves()
        moves.config(text=str(self._game.get_moves()))

        # if player choose to play without companion, then undo the following part
        if self._play_with_com == True:
            charge_num = self._game.companion.get_charge()
            for i in range(charge_num):
                self.interval_bar.com_charge_bar(i)
            # reset the companion when fully-charged
            if self._game.companion.is_fully_charged():
                self._game.companion.reset()
                steps = self._game.companion.activate(self._game)
                self._refresh_status()
                return self.animate(steps)

        score = self._game.get_score()
        print("Score is now {}.".format(score))

    # exit function
    def exit(self):
        """Ask exit or not when click exit button"""

        ans=messagebox.askokcancel('Verify exit', 'Really exit?')
        if ans:
            # close the game window
            self._master.destroy()

    def com_button(self):
        """Immediately activates the companion"""

        # set the button disabled after first use
        self.action_bar.companion_charge().config(state='disable')
        # charge the companion dot for 6 times to activate the companion
        self._game.companion.charge(6)
        charge_num = self._game.companion.get_charge()
        # change the interval bar
        for i in range(charge_num):
            self.interval_bar.com_charge_bar(i)
        self._game.companion.reset()
        steps = self._game.companion.activate(self._game)
        self._refresh_status()
        return self.animate(steps)

    def colour_activate(self):
        """Immediately activates (& removes) all dots of a random kind (colour)"""

        # set the button disabled after first use
        self.action_bar.colour_remove().config(state='disable')
        # generate a random kind
        kind = random.randint(1,4)
        dead_cells = {(2, 2), (2, 3), (2, 4),
                      (3, 2), (3, 3), (3, 4),
                      (4, 2), (4, 3), (4, 4),
                      (0, 7), (1, 7), (6, 7), (7, 7)}
        # create a set to save all the positions to be activated
        to_activate = set()
        for i in range(0,8):
            for j in range(0,8):
                # generate a random position
                position = (i,j)
                # the position is not in dead_cells and its kind is the random kind
                if position not in dead_cells and self._game.grid[position].get_dot().get_kind()==kind:
                    # add the position into set
                    to_activate.add(position)
        # activate all the position in set
        steps = self._game.activate_all(to_activate)
        return self.animate(steps)


# InfoPanel class
class InfoPanel(tk.Frame):
    """show remaining moves, score, companion and objectives"""

    def __init__(self, parent):
        super().__init__(parent)
        
        # remaining moves of the game
        self._moves=tk.Label(self, font='Helvetica 30')
        self._moves.pack(side=tk.LEFT, anchor=tk.NW)

        # show the score
        self._scores=tk.Label(self, font='Helvetica 20', fg="grey")
        self._scores.pack(side=tk.LEFT, anchor=tk.SW, padx=20)

        # show the image
        img=tk.PhotoImage(file="images/companions/images.png")
        self._image = tk.Label(self, image=img)
        self._image.img=img
        self._image.pack(side=tk.LEFT, anchor=tk.CENTER)

        # show the objectives
        self._image_manager = ImageManager('images/dots/', loader=load_image)
        self._object=ObjectivesView(self,image_manager=self._image_manager)
        self._object.pack(side=tk.RIGHT, pady=50)

    # get the current moves
    def remain_moves(self):
        return self._moves

    # get object
    def set_object(self):
        return self._object

    # get the current score
    def set_scores(self):
        return self._scores


# IntervalBar
class IntervalBar(tk.Canvas):
    """show two interval bar"""
    def __init__(self, parent):
        super().__init__(parent)

        # Basic objectives interval bar
        self.pack(side=tk.TOP)
        self._canvas = []
        for i in range(6):
            self.ca=tk.Canvas(self, width=60, height=25, bg='white')
            self.ca.pack(side=tk.LEFT,anchor=tk.CENTER)
            self._canvas.append(self.ca)
        self._canvas[0].config(bg='blue')

        # Companion objectives interval bar
        self._canvas2 = tk.Canvas(parent)
        self._canvas2.pack(side=tk.TOP)
        self._com_canvas = []
        for i in range(6):
            self.comca = tk.Canvas(self._canvas2, width=60, height=25, bg='white')
            self.comca.pack(side=tk.LEFT,anchor=tk.CENTER)
            self._com_canvas.append(self.comca)

    def progress_bar(self, i):
        """Basic dot progress bar"""
        if i == 0:
            for bar in self._canvas[1:]:
                bar.config(bg='white')
        self._canvas[i].config(bg='blue')

    def com_charge_bar(self, i):
        """companion dot charge bar"""
        if i == 0:
            # turn back if fully-charged
            for bar in self._com_canvas:
                bar.config(bg='white')
        self._com_canvas[i].config(bg='yellow')

    def com_charge_bar_reset(self):
        """reset companion dot charge bar"""
        for bar in self._com_canvas:
            bar.config(bg='white')


# ActionBar class
class ActionBar(tk.Frame):
    """show two action button"""
    def __init__(self, parent):
        super().__init__(parent)
        # create a companion charge button
        self._com_button=tk.Button(self, text="companion")
        self._com_button.pack(side=tk.LEFT)
        # create a colour remover button
        self._color_button=tk.Button(self, text="Colour Remover")
        self._color_button.pack(side=tk.LEFT)

    def companion_charge(self):
        return self._com_button

    def colour_remove(self):
        return self._color_button


# CompanionDot class
class CompanionDot(AbstractDot):
    """A companion dot"""
    DOT_NAME = "companion"

    def activate(self, position, game, activated, has_loop=False):
        self._expired = True
        # Once a companion dot is activated, the companion will be charged once
        game.companion.charge()

    def adjacent_activated(self, position, game, activated, activated_neighbours, has_loop=False):
        pass

    def after_resolved(self, position, game):
        pass

    def get_view_id(self):
        return "{}/{}".format(self.get_name(), +self.get_kind())

    def can_connect(self):
        return True


# SwirlDot class
class SwirlDot(AbstractDot):
    """A swirl dot"""
    DOT_NAME = 'swirl'

    def get_view_id(self):
        return "{}/{}".format(self.DOT_NAME, +self.get_kind())

    def adjacent_activated(self, position, game, activated, activated_neighbours, has_loop=False):
        pass

    def activate(self, position, game, activated, has_loop=False):
        """change the kind (colour) of adjacent dots to its kind."""
        self._expired = True
        dead_cells = {(2, 2), (2, 3), (2, 4),
                      (3, 2), (3, 3), (3, 4),
                      (4, 2), (4, 3), (4, 4),
                      (0, 7), (1, 7), (6, 7), (7, 7)}
        # get the kind of the swirldot
        kind = game.grid[position].get_dot().get_kind()
        x, y = position
        for i in range(x-1, x+2):
            for j in range(y-1, y+2):
                pos = i, j
                # positions are not in dead_cells and in the range between 0 and 7
                if pos not in dead_cells and i<8 and j<8 and i>=0 and j>=0:
                    # set dots kind as swirl dot kind
                    game.grid[pos].get_dot().set_kind(kind)

    def after_resolved(self, position, game):
        pass

    def can_connect(self):
        return True


# EskimoCompanion class
class EskimoCompanion(AbstractCompanion):
    """randomly places a swirl dot on the grid"""
    NAME = 'eskimo'

    def activate(self, game):
        dead_cells = {(2, 2), (2, 3), (2, 4),
                      (3, 2), (3, 3), (3, 4),
                      (4, 2), (4, 3), (4, 4),
                      (0, 7), (1, 7), (6, 7), (7, 7)}
        while True:
            # generate a position randomly
            position = (random.randint(0, 7), random.randint(0, 7))
            if position not in dead_cells:
                # put a swirl dot on this position
                game.grid[position].set_dot(SwirlDot(random.randint(1, 4)))
                break


def main():
    """Sets-up the GUI for Dots & Co"""
    # Write your GUI instantiation code here
    root = tk.Tk()
    dot = DotsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
