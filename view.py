"""Contains view components for Dots & Co"""

#                                                  ,  ,
#                                                / \/ \
#                                               (/ //_ \_
#      .-._                                      \||  .  \
#       \  '-._                            _,:__.-"/---\_ \
#  ______/___  '.    .--------------------'~-'--.)__( , )\ \
# `'--.___  _\  /    |             Here        ,'    \)|\ `\|
#      /_.-' _\ \ _:,_          Be Dragons           " ||   (
#    .'__ _.' \'-/,`-~`                                |/
#        '. ___.> /=,|  Abandon hope all ye who enter  |
#         / .-'/_ )  '---------------------------------'
#         )'  ( /(/
#              \\ "
#               '=='

import tkinter as tk
from collections import ChainMap

from modules.ee import EventEmitter

from modules.colours import VIBRANT_COLOURS
from util import ImageManager

__author__ = "Benjamin Martin and Brae Webb"
__copyright__ = "Copyright 2017, The University of Queensland"
__license__ = "MIT"
__version__ = "1.1.2"

class GridView(EventEmitter, tk.Canvas):
    """View component for grid in a game of Dots & Co
    
    Extension of tkinter Canvas"""

    # The colour of each tile type
    COLOURS = {
        'blank': VIBRANT_COLOURS['cream'],
        None: VIBRANT_COLOURS['grey'],
        1: VIBRANT_COLOURS['red'],
        2: VIBRANT_COLOURS['blue'],
        3: VIBRANT_COLOURS['yellow'],
        4: VIBRANT_COLOURS['blue_purple'],
        5: VIBRANT_COLOURS['pink'],
        6: VIBRANT_COLOURS['orange'],
        7: VIBRANT_COLOURS['dark_grey'],
        8: VIBRANT_COLOURS['green'],
        9: VIBRANT_COLOURS['brown'],
        10: VIBRANT_COLOURS['dark_blue'],
        11: VIBRANT_COLOURS['pale_blue'],
        12: VIBRANT_COLOURS['beige'],
        13: VIBRANT_COLOURS['lime']
    }

    def __init__(self, master, size=(6, 6), dot_size=40,
                 border=(20, 20), colours=None,
                 image_manager: ImageManager = None,
                 **kwargs):
        """
        Constructs a GridView inside the tkinter master widget

        Parameters:
            master (tk.Tk|tk.Frame): The parent widget
            size (tuple<int, int>): The (row, column) size of the grid, in pixels
            dot_size (int): The size of each dot in the game, in pixels
            border (tuple<int, int>): Size of the gap between dots in pixels
            colours (dict): Map between the tile type and the colour to display
                            Extends COLOURS property on class
            image_manager (ImageManager): An image manager (for caching, etc.)
            **kwargs: Any other keyword arguments for the Canvas constructor
        """

        if image_manager is None:
            raise ValueError("Parameter image_manager is required")

        # Set dimensions
        self.size = size
        self.dot_size = dot_size
        self.border = border

        self._image_manager = image_manager

        # Override default colours
        if colours is None:
            colours = {}
        colours = ChainMap(colours, self.COLOURS)

        # Super inits
        EventEmitter.__init__(self)

        width, height = self.calculate_size()
        tk.Canvas.__init__(self, master, width=width, height=height,
                           **kwargs, highlightthickness=0)
        self._master = master

        self._dots = {}
        self._colours = colours

        # items to be removed from the canvas
        self._connections = []
        self._dragged = []

        self.bind("<Button-1>", self._start_connection)
        self.bind("<B1-Motion>", self._move_connection)
        self.bind("<ButtonRelease-1>", self._end_connection)

    def draw_border(self, border_pairs, fill=True):
        """Draws a border around some cells
        
        Parameters:
            border_pairs (list<tuple<tuple<int, int>, tuple<int, int>>>): 
                        List of pairs of cells, each of which share a border along the path
            fill (bool): Border is filled-in iff True
            
        Notes:
            1* Border pairs of [((0, 0), (0, 1))] would signify the following border: 
            (0, 0) | (0, 1)
            
            2* Similarly, [((5, 3), (4, 3)), ((4, 4), (4, 3))]
             (4, 3) | (4, 4)
            --------|
             (5, 3) 
             
            Sequential border pairs do not need to be ordered such that pair[0][1] == pair[1][0] (see e.g. 2*) 
        """
        all_coords = []

        # General idea of the algorithm is to construct a list of coordinates for the border by iterating over border
        # pairs and calculating common points on each cell of the pair
        # But it's a *real* crap fest - welcome to the jungle
        for cell1, cell2 in border_pairs:
            (c1_l, c1_t), _, (c1_r, c1_b) = self.calculate_bounds(cell1, include_padding=True)
            (c2_l, c2_t), _, (c2_r, c2_b) = self.calculate_bounds(cell2, include_padding=True)

            point1 = c1_l, c1_t, c1_r, c1_b
            point2 = c2_l, c2_t, c2_r, c2_b

            coords = [c1 if c1 == c2 else None for c1, c2 in zip(point1, point2)]

            for i, value in enumerate(coords):
                if value is None:
                    value = point1[i] if point1[i] == point2[i + 2] else point1[i + 2]

                    coords[i] = value
                    coords[i + 2] = value

                    break

            p1x, p1y, p2x, p2y = coords
            point1 = p1x, p1y
            point2 = p2x, p2y

            if not all_coords:
                all_coords.extend((point1, point2))
            else:
                if all_coords[-2] in (point1, point2):
                    all_coords[-2], all_coords[-1] = all_coords[-1], all_coords[-2]

                if all_coords[-1] == point1:
                    all_coords.append(point2)
                else:
                    all_coords.append(point1)

        all_coords.append(all_coords[0])

        self.create_polygon(*all_coords, fill=self._colours['blank'] if fill else '', outline='black')

    def calculate_size(self):
        """(tuple<int, int>) Returns the widget's required xy dimensions"""
        rows, columns = self.size
        radius = self.dot_size
        pad_x, pad_y = self.border
        width = columns * radius + (columns + 1) * pad_x
        height = rows * radius + (rows + 1) * pad_y

        return width, height

    def xy_to_rc(self, xy_position):
        """(tuple<int, int>) Converts xy position into row-column position"""
        x, y = xy_position
        radius = self.dot_size
        pad_x, pad_y = self.border

        column = x // (pad_x + radius)
        on_column_padding = x % (pad_x + radius) < pad_x
        row = y // (pad_y + radius)
        on_row_padding = y % (pad_y + radius) < pad_y
        bounds = self.calculate_size()
        out_of_bounds = x < 0 or y < 0 or x >= bounds[0] or y >= bounds[1]

        if on_column_padding or on_row_padding or out_of_bounds:
            return None

        return row, column

    def _start_connection(self, event):
        """Handles the event where a dot is clicked to start drawing a
        connection

        Parameters:
            event (tk.MouseEvent): The event caused by a mouse click
        """
        position = self.xy_to_rc((event.x, event.y))

        if position is None:
            return

        self.emit("start_connection", position)

    def _move_connection(self, event):
        """Handles the event where the mouse is dragged and treats the event
        as moving a connection

        Parameters:
            event (tk.MouseEvent): The event caused by dragging the mouse
        """
        self.emit("move_connection", (event.x, event.y))

    def _end_connection(self, event):
        """Handles the release of the mouse

        Parameters:
            event (tk.MouseEvent): The event caused by releasing the mouse
        """
        position = self.xy_to_rc((event.x, event.y))

        self.emit("end_connection", position)

    def calculate_bounds(self, position, include_padding=False):
        """Calculates the bounds of a dot at the given position in the grid

        Parameters:
            position (tuple<int, int>): The (row, column) position of the dot
            include_padding (bool): Padding is included in the bounds iff True

        Return:
            (tuple<int, int, int>): The top left, middle and bottom right
                                    position of the tile on the GridView
        """

        row, column = position

        radius = self.dot_size
        pad_x, pad_y = self.border

        top = row * (pad_y + radius) + pad_y
        left = column * (pad_x + radius) + pad_x
        bottom = top + radius
        right = left + radius

        top_left = left, top
        bottom_right = right, bottom

        middle = left + radius // 2, top + radius // 2

        if include_padding:
            return ((left - pad_x // 2), (top - pad_x // 2)), middle, ((right + pad_x // 2), (bottom + pad_x // 2))

        return top_left, middle, bottom_right

    def _draw_connection(self, start, end, connection_type):
        """Draws a connection between two dots in the grid

        Parameters:
            start (tuple<int, int>): An x and y position to draw from
            end (tuple<int, int>): An x and y position to draw to
            connection_type (int): The type of the connection to draw

        Returns:
            (int): The canvas identifier of the connecting line
        """
        colour = self._colours[connection_type]

        return self.create_line(start, end, width=10, fill=colour)

    def draw_connection(self, start, end, connection_type):
        """Draws a connection between a start dot and and end dot based on the
        colour of the dots

        Parameters:
            start (tuple<int, int>): The position of the start dot in the grid
            end (tuple<int, int>): The position of the end dot in the grid
            connection_type (int): The type of the connection to draw

        Returns:
            (int): The canvas identifier of the connecting line
        """
        # find the x and y position of the given dot
        _, start, _ = self.calculate_bounds(start)
        _, end, _ = self.calculate_bounds(end)

        line = self._draw_connection(start, end, connection_type)
        self._connections.append(line)

        return line

    def clear_connections(self):
        """Removes all the connections drawn between dots"""
        for line in self._connections + self._dragged:
            self.delete(line)

    def undo_connection(self):
        """Removes the last connection the was drawn"""
        self.delete(self._connections[-1])
        self._connections.pop()

    def draw_dragged_connection(self, start, position, connection_type):
        """Draws a temporary connection between the start dot and a position

        Parameters:
            start (tuple<int, int>): The position of the starting dot
            position (tuple<int, int>): An x and y position to draw to
            connection_type (int): The type of connection to draw
        """
        self.clear_dragged_connections()

        _, start, _ = self.calculate_bounds(start)
        self._dragged.append(self._draw_connection(start, position,
                                                   connection_type))

    def clear_dragged_connections(self):
        """Removes all the dragged connections"""
        for dragged in self._dragged:
            self.delete(dragged)

    def load_image(self, cell, size):  # pylint disable=unused-argument
        """Loads an image

        Parameters:
            cell (model.Dot): The type of dot to load
            size (tuple<int, int>): The dimensions of the image to load
        """
        return self._image_manager.load(cell.get_view_id(), size)

    def draw_cell(self, position, cell):
        """Draws a cell at the given position

        Parameters:
            position (tuple<int, int>): The (row, column) position of the cell
            cell (AbstractCell): The cell to draw at the position
        """

        self.draw_dot(position, cell.get_dot())

    def draw_dot(self, position, dot):
        """Draws a dot at the given position

        Parameters:
            position (tuple<int, int>): The (row, column) position of the dot
            dot (AbstractCell): The dot to draw at the position
        """
        top_left, middle, bottom_right = self.calculate_bounds(position)

        size = ((bottom_right[0] - top_left[0]),
                (bottom_right[1] - top_left[1]))

        if dot is None or dot.will_be_removed():
            if self._dots.get(position) is not None:
                # Replace an image tile with a blank image
                image = tk.PhotoImage()
                self.itemconfig(self._dots[position], image=image)
            return

        image = self.load_image(dot, size)

        if self._dots.get(position) is None:
            self._dots[position] = self.create_image(*middle, image=image)
        else:
            self.itemconfig(self._dots[position], image=image)

    def draw(self, grid):
        """Draws all the cells in the grid at their corresponding position

        Parameters:
            grid (DotGrid): A grid of cells
        """
        # clear all the extra canvas items
        for extra in self._connections:
            self.delete(extra)
        # draw all the tiles
        for position, cell in grid.items():
            self.draw_cell(position, cell)


class ObjectivesView(GridView):
    """View component for objectives in a game of Dots & Co"""

    def __init__(self, master, width=4, align_right=True, dot_size=20, border=(10, 10), colours=None,
                 image_manager: ImageManager = None, **kwargs):
        """Constructor
        
        Parameters:
            width (int): The maximum number of objectives to display
            align_right (bool): If True, objectives are aligned to the right, else to the left
        """

        size = (2, width)
        super().__init__(master, size=size, dot_size=dot_size, border=border, colours=colours,
                         image_manager=image_manager, **kwargs)

        self._align_right = align_right

    def draw(self, objectives):
        """Draws all the cells in the grid at their corresponding position

        Parameters:
            objectives (list<tuple<AbstractDot, int>>): 
                    List of (objective, remaining) pairs, where remaining is the amount of progress
                    remaining before the corresponding objective is reached
                    
                    (see return type of ObjectiveManager.get_status)
        """
        self.delete(tk.ALL)
        self._dots = {}

        _, columns = self.size

        start = columns - len(objectives)

        if start < 0:
            raise ValueError(
                "Number of objectives cannot exceed width (see constructor); expected at most {}, but got {}".format(
                    columns, len(objectives)))

        if not self._align_right:
            start = 0

        for i, (objective, count) in enumerate(objectives, start=start):
            self.draw_dot((0, i), objective)

            _, middle, _ = self.calculate_bounds((1, i))
            self.create_text(middle, text=str(count))
