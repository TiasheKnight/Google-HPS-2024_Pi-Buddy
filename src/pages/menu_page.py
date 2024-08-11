import multiprocessing
import time
import RPi.GPIO as GPIO


from pages.pages_utils import theme_colors, PageConfig, IconTextBox
from components.st7735s.st7735s import Screen
from value_manager import ValueManager

class MenuPageCursorDirection():
    NONE = 0
    UP = 1
    DOWN = -1
    
    
class MenuPageSelectTransitionStage():
    NONE = 0
    REMOVE_OTHERS = 1
    REVERSE_SELECTED_COLOR = 2
    COLOR_BACKGROUND = 3
    END_DISPLAY = 4


class OptionBoxConfig():
    ICON_TRUE_COLOR = PageConfig.ICON_TRUE_COLOR                    #
    ICON_FALSE_COLOR = PageConfig.ICON_FALSE_COLOR                  #
    BOX_HOVER_SCALE = 1.2                                           # The ratio the box is scaled at in hover mode 
    BORDER_HOVER_SCALE = 2                                          # The ratio the box border is scaled at in hover mode
    DEFAULT_COLOR = PageConfig.DEFAULT_COLOR                        # Default color for border box, icon, and text
    HOVERED_COLOR = PageConfig.HOVERED_COLOR                        # Hovered color for border box, icon, and text
    BACKGROUND_COLOR = PageConfig.BACKGROUND_COLOR                  # Background color of the screen
    DEFAULT_BOX_WIDTH = PageConfig.ICON_TEXT_BOX_WIDTH              # Box width in default mode, border width included
    DEFAULT_BOX_HEIGHT = PageConfig.ICON_TEXT_BOX_HEIGHT            # Box height in default mode, border width included
    DEFAULT_BORDER = PageConfig.ICON_TEXT_BOX_BORDER                # Default border width 
    Y_MARGIN = PageConfig.ICON_TEXT_BOX_ICON_X_MARGIN               # Box margin in vertical direction
    ICON_Y_RATIO = PageConfig.ICON_TEXT_BOX_ICON_Y_RATIO            # The amount of horizontal space the icon takes, border width exclusive
    DEFAULT_ICON_X_MARGIN = PageConfig.ICON_TEXT_BOX_ICON_X_MARGIN  # The x margin between border-icon and icon-text 
    DEFAULT_TEXT_SIZE = PageConfig.ICON_TEXT_BOX_TEXT_SIZE          # Default text size


class OptionBox(IconTextBox):
    def __init__(self, screen, default_x, default_y, text, icon_path):
        
        self.box_hover_scale = OptionBoxConfig.BOX_HOVER_SCALE
        self.border_hover_scale = OptionBoxConfig.BORDER_HOVER_SCALE
        self.default_color = OptionBoxConfig.DEFAULT_COLOR
        self.hovered_color = OptionBoxConfig.HOVERED_COLOR
        self.default_icon_color_replacements={
            OptionBoxConfig.ICON_TRUE_COLOR: self.default_color,
            OptionBoxConfig.ICON_FALSE_COLOR: OptionBoxConfig.BACKGROUND_COLOR
        }
        self.hovered_icon_color_replacements={
            OptionBoxConfig.ICON_TRUE_COLOR: self.hovered_color,
            OptionBoxConfig.ICON_FALSE_COLOR: OptionBoxConfig.BACKGROUND_COLOR
        }
        
        self.default_x = default_x
        self.default_y = default_y
        self.default_box_width = OptionBoxConfig.DEFAULT_BOX_WIDTH
        self.default_box_height = OptionBoxConfig.DEFAULT_BOX_HEIGHT
        self.default_border = OptionBoxConfig.DEFAULT_BORDER
        self.default_icon_x_margin = OptionBoxConfig.DEFAULT_ICON_X_MARGIN
        self.default_text_size = OptionBoxConfig.DEFAULT_TEXT_SIZE
        
        super().__init__(
            screen=screen, 
            x_marking=self.default_x, 
            y_marking=self.default_y, 
            box_width=self.default_box_width, 
            box_height=self.default_box_height,
            text=text,
            text_size=self.default_text_size,
            color=self.default_color,
            background_color=OptionBoxConfig.BACKGROUND_COLOR,
            icon_path=icon_path,
            icon_margin_x=self.default_icon_x_margin,
            icon_y_ratio=OptionBoxConfig.ICON_Y_RATIO,
            border=OptionBoxConfig.DEFAULT_BORDER,
            y_margin=OptionBoxConfig.Y_MARGIN,
            icon_color_replacements=self.default_icon_color_replacements
        )
    
    
    def reset(self):
        # Set parameters to default value
        self.box_width = self.default_box_width
        self.box_height = self.default_box_height
        self.border = self.default_border
        self.color = self.default_color
        self.icon_x_margin = self.default_icon_x_margin
        self.text_size = self.default_text_size
        self.x_marking = self.default_x
        self.y_marking = self.default_y
        self.icon_color_replacements = self.default_icon_color_replacements
        self._reset_dim()


    def scroll(self, y_incr, div):
        # Move y value, where y_incr is the amount to move and div keeps the value in range
        self.default_y += y_incr
        self.default_y %= div
        self.reset()
        
    
    def hover(self):
        # Set parameters to hover mode
        self.box_width = int(self.default_box_width * self.box_hover_scale)
        self.box_height = int(self.default_box_height * self.box_hover_scale)
        self.border = int(self.default_border * self.border_hover_scale)
        self.color = self.hovered_color
        self.icon_size = int((self.box_height - (2 * self.border)) * self.icon_y_ratio)
        self.icon_x_margin = int(self.default_icon_x_margin * self.box_hover_scale)
        self.text_size = int(self.default_text_size * self.box_hover_scale)
        self.x_marking = int(self.default_x - (self.box_width * (self.box_hover_scale - 1) / 2))
        self.y_marking = int(self.default_y - (self.box_height * (self.box_hover_scale - 1) / 2))
        self.icon_color_replacements = self.hovered_icon_color_replacements
        self._reset_dim()
        

    def reverse_color(self):
        self.color, self.background_color = self.background_color, self.color
        self.icon_color_replacements = {
            OptionBoxConfig.ICON_TRUE_COLOR: self.color,
            OptionBoxConfig.ICON_FALSE_COLOR: self.background_color
        }


class MenuPage():
    def __init__(self, screen):        
        self.screen = screen
        
        # Screen states
        self.cursor_direction = ValueManager(MenuPageCursorDirection.NONE)    
        self.select_triggered = ValueManager(int(False))
        self.select_transition_state = ValueManager(MenuPageSelectTransitionStage.NONE)
        self.display_completed = ValueManager(int(False))
        
        # Setting the options in the menu
        self.option_box_information = [
            ['Weather', './icons/menu_weather.png'],
            ['Battery', './icons/menu_battery.png'],
            ['Timer',    './icons/menu_timer.png'],
            ['???',     './icons/menu_surprise.png']
        ]
        self.background_color = theme_colors.Primary
        self.option_boxes = None 
        self.hovered_id = None
        self.option_box_height = None
        self.content_height = None
        self._initiate_option_boxes()
        
        
        # Start display process for menu page
        display_process = multiprocessing.Process(target=self._display)
        display_process.start()
    
    
    def handle_task(self, task_info):
        
        # Tasks will not be taken if a transition is ongoing
        if (self.cursor_direction.reveal() == MenuPageCursorDirection.NONE and
            self.select_triggered.reveal() == int(False)):

            if task_info['task'] == 'MOVE_CURSOR_LEFT_DOWN':
                self.cursor_direction.overwrite(MenuPageCursorDirection.DOWN)
                
            elif task_info['task'] == 'MOVE_CURSOR_RIGHT_UP':
                self.cursor_direction.overwrite(MenuPageCursorDirection.UP)
                
            elif task_info['task'] == 'ENTER_SELECT':
                self.select_triggered.overwrite(int(True))
                
                # Return message to go to next page after display is done
                while True:
                    if self.display_completed.reveal():
                        return self.option_box_information[self.hovered_id][0]
                
            elif task_info['task'] == 'OUT_RESUME':
                pass
            
    
    
    def _initiate_option_boxes(self):
        
        # Hover over the option box in the middle as default
        num_boxes = len(self.option_box_information)
        self.hovered_id = num_boxes // 2
        
        # Calculate x value of the first box
        screen_width = self.screen.get_col_dim()
        box_width = OptionBoxConfig.DEFAULT_BOX_WIDTH
        current_box_x = (screen_width // 2) - (box_width // 2)
        
        # Calculate y vlaue of the first box
        screen_height = self.screen.get_row_dim()
        option_box_height = OptionBoxConfig.DEFAULT_BOX_HEIGHT + (2 * OptionBoxConfig.Y_MARGIN)
        current_box_y = (screen_height // 2) - ((self.hovered_id * 2 + 1) / 2.0 * option_box_height) + OptionBoxConfig.Y_MARGIN
        
        # Initiate option boxes with information from self.option_box_information
        self.option_boxes = []
        for box_info in self.option_box_information:
            option_box_name, option_box_icon_path = box_info
            self.option_boxes.append(
                OptionBox(
                    self.screen, 
                    current_box_x, 
                    current_box_y, 
                    option_box_name, 
                    option_box_icon_path)
            )
            current_box_y += option_box_height
        
        # Update height values
        self.option_box_height = option_box_height
        self.content_height = option_box_height * len(self.option_box_information)
        
        # Hover 
        self.option_boxes[self.hovered_id].hover()
                
        
    def _display(self):
        while True:
            
            cursor_direction = self.cursor_direction.reveal()
            select_triggered = self.select_triggered.reveal()
            
            # Check if the cursor had been moved
            if cursor_direction:
                if cursor_direction == MenuPageCursorDirection.UP:
                    direction = -1
                elif cursor_direction == MenuPageCursorDirection.DOWN:    
                    direction = 1
                else:
                    raise ValueError(f'Invaid cursor direction {cursor_direction} was assigned to menu page')

                # Move option_boxes 
                for option_box in self.option_boxes:
                    option_box.scroll(direction * self.option_box_height, self.content_height)
                
                self.hovered_id = (self.hovered_id - direction) % len(self.option_box_information)
                self.option_boxes[self.hovered_id].hover()
                self.cursor_direction.overwrite(MenuPageCursorDirection.NONE)
            
            # Check if select had been triggered
            elif select_triggered:
                select_transition_state = self.select_transition_state.reveal()
                
                if select_transition_state == MenuPageSelectTransitionStage.REMOVE_OTHERS:
                    for option_box_id, option_box in enumerate(self.option_boxes):
                        if option_box_id != self.hovered_id:
                            option_box.display = False
                
                elif select_transition_state == MenuPageSelectTransitionStage.REVERSE_SELECTED_COLOR:
                    self.option_boxes[self.hovered_id].reverse_color()
                
                elif select_transition_state == MenuPageSelectTransitionStage.COLOR_BACKGROUND:
                    # self.option_boxes[self.hovered_id].hide_border()
                    self.option_boxes[self.hovered_id].show_border = False
                    self.background_color = OptionBoxConfig.HOVERED_COLOR
                
                elif select_transition_state == MenuPageSelectTransitionStage.END_DISPLAY:
                    break
                
                self.select_transition_state.overwrite(select_transition_state + 1)
                
            # Draw and update screen
            self.screen.fill_screen(self.background_color)
            for option_box in self.option_boxes:
                option_box.draw()
            self.screen.update()
            time.sleep(0.01)
            self.screen.clear()
        
        self.display_completed.overwrite(int(True))
