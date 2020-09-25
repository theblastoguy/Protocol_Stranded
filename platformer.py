"""
Example of Pymunk Physics Engine Platformer
"""
import math
from typing import Optional
import arcade
import arcade.gui
import logging
import sys
import time

logging.basicConfig(level=logging.DEBUG)

VERSION = "v0.1"

GAMENAME = "Qwerty and Ruan's PyWeek 30 Entry"
SCREEN_TITLE = GAMENAME

# How big are our image tiles?
SPRITE_IMAGE_SIZE = 32

# Scale sprites up or down
SPRITE_SCALING_PLAYER = 2
SPRITE_SCALING_TILES = 1

# Scaled sprite size for tiles
SPRITE_SIZE = SPRITE_IMAGE_SIZE * SPRITE_SCALING_TILES

# Size of grid to show on screen, in number of tiles
SCREEN_GRID_WIDTH = 50
SCREEN_GRID_HEIGHT = 25

# Size of screen to show, in pixels
SCREEN_WIDTH = SPRITE_IMAGE_SIZE * SCREEN_GRID_WIDTH
SCREEN_HEIGHT = SPRITE_IMAGE_SIZE * SCREEN_GRID_HEIGHT

# How many pixels to keep as a minimum margin between the character
# and the edge of the screen.
VIEWPORT_MARGIN_LEFT_RIGHT = SPRITE_SIZE * 10
VIEWPORT_MARGIN_TOP_BOTTOM = SPRITE_SIZE * 6

# --- Physics forces. Higher number, faster accelerating.

# Gravity
GRAVITY = 800

# Damping - Amount of speed lost per second
DEFAULT_DAMPING = 1.0
PLAYER_DAMPING = 0.4

# Friction between objects
PLAYER_FRICTION = 1.0
WALL_FRICTION = 0.7
DYNAMIC_ITEM_FRICTION = 0.6

# Mass (defaults to 1)
PLAYER_MASS = 1

# Keep player from going too fast
PLAYER_MAX_HORIZONTAL_SPEED = 450
PLAYER_MAX_VERTICAL_SPEED = 1600

# Force applied while on the ground
PLAYER_MOVE_FORCE_ON_GROUND = 8000

# Force applied when moving left/right in the air
PLAYER_MOVE_FORCE_IN_AIR = 900

# Strength of a jump
PLAYER_JUMP_IMPULSE = 1800

# Close enough to not-moving to have the animation go to idle.
DEAD_ZONE = 0.1

# Constants used to track if the player is facing left or right
RIGHT_FACING = 0
LEFT_FACING = 1

# How many pixels to move before we change the texture in the walking animation
DISTANCE_TO_CHANGE_TEXTURE = 20

# Music file
MUSIC_FILE = "resources/sounds/level1.mp3"
MUSIC_VOLUME = 0.2

class PlayerSprite(arcade.Sprite):
    """ Player Sprite """
    def __init__(self, game, ladder_list=arcade.SpriteList):
        """ Init """
        # Let parent initialize
        super().__init__()

        # Set our scale
        self.scale = SPRITE_SCALING_PLAYER
        self.game = game
        self.dead = False

        # Images from Kenney.nl's Character pack
        # main_path = ":resources:images/animated_characters/female_adventurer/femaleAdventurer"
        # main_path = ":resources:images/animated_characters/female_person/femalePerson"
        # main_path = ":resources:images/animated_characters/male_person/malePerson"
        # main_path = ":resources:images/animated_characters/male_adventurer/maleAdventurer"
        # main_path = ":resources:images/animated_characters/zombie/zombie"
        # main_path = ":resources:images/animated_characters/robot/robot"
        main_path = "resources/images/characters/index"

        # Load textures for idle standing
        self.idle_texture_pair = arcade.load_texture_pair(f"{main_path}_idle.png")
        self.jump_texture_pair = arcade.load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = arcade.load_texture_pair(f"{main_path}_fall.png")
        self.splat_texture_pair = arcade.load_texture_pair(f"{main_path}_splat.png")

        self.TOTAL_WALK_ANIMATIONS = 4

        # Load textures for walking
        self.walk_textures = []
        for i in range(self.TOTAL_WALK_ANIMATIONS):
            texture = arcade.load_texture_pair(f"{main_path}_run{i}.png")
            self.walk_textures.append(texture)

        # Load textures for climbing
        self.climbing_textures = []
        texture = arcade.load_texture(f"{main_path}_climb0.png")
        self.climbing_textures.append(texture)
        texture = arcade.load_texture(f"{main_path}_climb1.png")
        self.climbing_textures.append(texture)

        # Set the initial texture
        self.texture = self.idle_texture_pair[0]

        # Hit box will be set based on the first image used.
        self.hit_box = self.texture.hit_box_points

        # Default to face-right
        self.character_face_direction = RIGHT_FACING

        # Index of our current texture
        self.cur_texture = 0

        # How far have we traveled:
        self.x_odometer = 0  # since changing texture
        self.y_odometer = 0  # since jumping

        self.ladder_list = ladder_list
        self.is_on_ladder = False


    def splat(self):
        if not self.dead:
            self.dead = True
            self.texture = self.splat_texture_pair[0]
            self.game.play_audio('splat.mp3')
        
    def pymunk_moved(self, physics_engine, dx, dy, d_angle):
        """ Handle being moved by the pymunk engine """
        # Figure out if we need to face left or right
        if dx < -DEAD_ZONE and self.character_face_direction == RIGHT_FACING:
            self.character_face_direction = LEFT_FACING
        elif dx > DEAD_ZONE and self.character_face_direction == LEFT_FACING:
            self.character_face_direction = RIGHT_FACING

        # Are we on the ground?
        is_on_ground = physics_engine.is_on_ground(self)

        # Are we on a ladder?
        if len(arcade.check_for_collision_with_list(self, self.ladder_list)) > 0:
            if not self.is_on_ladder:
                self.is_on_ladder = True
                self.pymunk.gravity = (0, 0)
                self.pymunk.damping = 0.0001
                self.pymunk.max_vertical_velocity = PLAYER_MAX_HORIZONTAL_SPEED
        else:
            if self.is_on_ladder:
                self.pymunk.damping = 1.0
                self.pymunk.max_vertical_velocity = PLAYER_MAX_VERTICAL_SPEED
                self.is_on_ladder = False
                self.pymunk.gravity = None

        # Add to the odometer how far we've moved
        self.x_odometer += dx

        if self.is_on_ladder and not is_on_ground:
            # Have we moved far enough to change the texture?
            if abs(self.y_odometer) > DISTANCE_TO_CHANGE_TEXTURE:

                # Reset the odometer
                self.y_odometer = 0

                # Advance the walking animation
                self.cur_texture += 1

            if self.cur_texture > 1:
                self.cur_texture = 0
            self.texture = self.climbing_textures[self.cur_texture]
            return

        # Jumping animation
        if not is_on_ground:
            if dy > DEAD_ZONE:
                self.texture = self.jump_texture_pair[self.character_face_direction]
                return
            elif dy < -DEAD_ZONE:
                self.texture = self.fall_texture_pair[self.character_face_direction]
                self.y_odometer += dy
                if self.y_odometer < -800:
                    self.splat()
                return

        if is_on_ground:
            self.y_odometer = 0

        # Idle animation
        if abs(dx) <= DEAD_ZONE:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Have we moved far enough to change the texture?
        if abs(self.x_odometer) > DISTANCE_TO_CHANGE_TEXTURE:

            # Reset the odometer
            self.x_odometer = 0

            # Advance the walking animation
            self.cur_texture += 1
            if self.cur_texture >= self.TOTAL_WALK_ANIMATIONS:
                self.cur_texture = 1
            self.texture = self.walk_textures[self.cur_texture][self.character_face_direction]

class GameView(arcade.View):
    """ Main Window """

    def __init__(self):
        """ Create the variables """

        # Init the parent class
        super().__init__()

        # Player sprite
        self.player_sprite: Optional[PlayerSprite] = None

        # Sprite lists we need
        self.player_list: Optional[arcade.SpriteList] = None
        self.wall_list: Optional[arcade.SpriteList] = None
        self.item_list: Optional[arcade.SpriteList] = None
        self.fruit_list: Optional[arcade.SpriteList] = None
        self.trees_list = None
        self.level_end_list: Optional[arcade.SpriteList] = None

        # Track the current state of what key is pressed
        self.left_pressed: bool = False
        self.right_pressed: bool = False
        self.up_pressed: bool = False
        self.down_pressed: bool = False

        # Is music playing
        self.music = None

        # Background image will be stored in this variable
        self.background = None

        # Fruit Power
        self.fruit_power = 0

        # Physics engine
        self.physics_engine = Optional[arcade.PymunkPhysicsEngine]

        # Set the viewport boundaries
        # These numbers set where we have 'scrolled' to.
        self.view_left = 0
        self.view_bottom = 0

        # Set background color
        arcade.set_background_color(arcade.color.AMAZON)

    def setup(self, map_name):
        """ Set up everything with the game """

        # Create the sprite lists
        self.player_list = arcade.SpriteList()
        self.cannon_list = arcade.SpriteList()
        self.fruit_list = arcade.SpriteList()
        self.map_name = map_name

        # Read in the tiled map
        my_map = arcade.tilemap.read_tmx(self.map_name)

        try:
            self.background = arcade.load_texture('resources/images/{}.png'.format(map_name))
        except FileNotFoundError:
            self.background = arcade.load_texture('resources/images/backgrounds/level1.tmx.png'.format(map_name))

        # Read in the map layers
        self.wall_list = arcade.tilemap.process_layer(my_map, 'Solid Platforms', SPRITE_SCALING_TILES)
        self.item_list = arcade.tilemap.process_layer(my_map, 'Movable Items', SPRITE_SCALING_TILES)
        self.cannon_list = arcade.tilemap.process_layer(my_map, 'Cannons', SPRITE_SCALING_TILES)
        self.fruit_list = arcade.tilemap.process_layer(my_map, 'Fruit', SPRITE_SCALING_TILES)
        self.trees_list = arcade.tilemap.process_layer(my_map, 'Trees', SPRITE_SCALING_TILES)
        self.level_end_list = arcade.tilemap.process_layer(my_map, 'Player End', SPRITE_SCALING_TILES)

        # Create player sprite
        self.player_sprite = PlayerSprite(game=self, ladder_list=self.trees_list)

        try:
            player_start_tilemap_objs = arcade.tilemap.get_tilemap_layer(my_map, 'Player Start').tiled_objects
            player_start_location = player_start_tilemap_objs[0].location
        except (IndexError, AttributeError, TypeError):
            raise Exception("Missing or duplicate Player Start location in map {}, please fix".format(my_map.tmx_file))

        # Set player location
        self.player_sprite.top = player_start_location.x
        self.player_sprite.left = player_start_location.y
        # Add to player sprite list

        # wierd workarounds below
        self.player_sprite.top = player_start_location.x + 1200
        self.player_sprite.left = player_start_location.y + 180

        #arcade.set_viewport(0, SCREEN_WIDTH, 700, SCREEN_HEIGHT)
        arcade.set_viewport(player_start_location.x - 300,
                            SCREEN_WIDTH + player_start_location.x - 300,
                            player_start_location.y + 800,
                            SCREEN_HEIGHT + player_start_location.y + 800)

        self.player_list.append(self.player_sprite)

        # --- Pymunk Physics Engine Setup ---

        # The default damping for every object controls the percent of velocity
        # the object will keep each second. A value of 1.0 is no speed loss,
        # 0.9 is 10% per second, 0.1 is 90% per second.
        # For top-down games, this is basically the friction for moving objects.
        # For platformers with gravity, this should probably be set to 1.0.
        # Default value is 1.0 if not specified.
        damping = DEFAULT_DAMPING

        # Set the gravity. (0, 0) is good for outer space and top-down.
        gravity = (0, -GRAVITY)

        # Create the physics engine
        self.physics_engine = arcade.PymunkPhysicsEngine(damping=damping,
                                                         gravity=gravity)

        # Add the player.
        # For the player, we set the damping to a lower value, which increases
        # the damping rate. This prevents the character from traveling too far
        # after the player lets off the movement keys.
        # Setting the moment to PymunkPhysicsEngine.MOMENT_INF prevents it from
        # rotating.
        # Friction normally goes between 0 (no friction) and 1.0 (high friction)
        # Friction is between two objects in contact. It is important to remember
        # in top-down games that friction moving along the 'floor' is controlled
        # by damping.
        self.physics_engine.add_sprite(self.player_sprite,
                                       friction=PLAYER_FRICTION,
                                       mass=PLAYER_MASS,
                                       moment=arcade.PymunkPhysicsEngine.MOMENT_INF,
                                       collision_type="player",
                                       max_horizontal_velocity=PLAYER_MAX_HORIZONTAL_SPEED,
                                       max_vertical_velocity=PLAYER_MAX_VERTICAL_SPEED)

        # Create the walls.
        # By setting the body type to PymunkPhysicsEngine.STATIC the walls can't
        # move.
        # Movable objects that respond to forces are PymunkPhysicsEngine.DYNAMIC
        # PymunkPhysicsEngine.KINEMATIC objects will move, but are assumed to be
        # repositioned by code and don't respond to physics forces.
        # Dynamic is default.
        self.physics_engine.add_sprite_list(self.wall_list,
                                            friction=WALL_FRICTION,
                                            collision_type="wall",
                                            body_type=arcade.PymunkPhysicsEngine.STATIC)

        # Create the items
        self.physics_engine.add_sprite_list(self.item_list,
                                            friction=DYNAMIC_ITEM_FRICTION,
                                            collision_type="item")

        # Create the cannons
        self.physics_engine.add_sprite_list(self.cannon_list,
                                            friction=WALL_FRICTION,
                                            collision_type="item")

        # Create the fruit
        self.physics_engine.add_sprite_list(self.fruit_list,
                                            collision_type="fruit",
                                            body_type=arcade.PymunkPhysicsEngine.STATIC)

        # Create the level end
        self.physics_engine.add_sprite_list(self.level_end_list,
                                            collision_type="level_end",
                                            body_type=arcade.PymunkPhysicsEngine.STATIC)

        # Play the background music
        self.play_song()

    def play_song(self):
        """Play background music"""

        if self.music:
            self.music.stop()
        self.music = arcade.Sound(MUSIC_FILE, streaming=True)
        self.music.play(volume=MUSIC_VOLUME)
        time.sleep(0.03)

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        if key == arcade.key.LEFT:
            self.left_pressed = True
        elif key == arcade.key.RIGHT:
            self.right_pressed = True
        elif key == arcade.key.UP:
            self.up_pressed = True
            # find out if player is standing on ground, and not on a ladder
            if self.physics_engine.is_on_ground(self.player_sprite) \
                    and not self.player_sprite.is_on_ladder:
                # She is! Go ahead and jump
                impulse = (0, PLAYER_JUMP_IMPULSE)
                self.physics_engine.apply_impulse(self.player_sprite, impulse)
                self.play_audio('jump.mp3')
        elif key == arcade.key.DOWN:
            self.up_pressed = True


    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """

        if key == arcade.key.LEFT:
            self.left_pressed = False
        elif key == arcade.key.RIGHT:
            self.right_pressed = False
        elif key == arcade.key.UP:
            self.up_pressed = False
        elif key == arcade.key.DOWN:
            self.up_pressed = False        

    def on_update(self, delta_time):
        """ Movement and game logic """

        if self.player_sprite.dead:
            return

        is_on_ground = self.physics_engine.is_on_ground(self.player_sprite)
        # Update player forces based on keys pressed
        if self.left_pressed and not self.right_pressed:
            # Create a force to the left. Apply it.
            if is_on_ground or self.player_sprite.is_on_ladder:
                force = (-PLAYER_MOVE_FORCE_ON_GROUND, 0)
            else:
                force = (-PLAYER_MOVE_FORCE_IN_AIR, 0)
            self.physics_engine.apply_force(self.player_sprite, force)
            # Set friction to zero for the player while moving
            self.physics_engine.set_friction(self.player_sprite, 0)
        elif self.right_pressed and not self.left_pressed:
            # Create a force to the right. Apply it.
            if is_on_ground or self.player_sprite.is_on_ladder:
                force = (PLAYER_MOVE_FORCE_ON_GROUND, 0)
            else:
                force = (PLAYER_MOVE_FORCE_IN_AIR, 0)
            self.physics_engine.apply_force(self.player_sprite, force)
            # Set friction to zero for the player while moving
            self.physics_engine.set_friction(self.player_sprite, 0)
        elif self.up_pressed and not self.down_pressed:
            # Create a force to the right. Apply it.
            if self.player_sprite.is_on_ladder:
                force = (0, PLAYER_MOVE_FORCE_ON_GROUND)
                self.physics_engine.apply_force(self.player_sprite, force)
                # Set friction to zero for the player while moving
                self.physics_engine.set_friction(self.player_sprite, 0)
        elif self.down_pressed and not self.up_pressed:
            # Create a force to the right. Apply it.
            if self.player_sprite.is_on_ladder:
                force = (0, -PLAYER_MOVE_FORCE_ON_GROUND)
                self.physics_engine.apply_force(self.player_sprite, force)
                # Set friction to zero for the player while moving
                self.physics_engine.set_friction(self.player_sprite, 0)
        else:
            # Player's feet are not moving. Therefore up the friction so we stop.
            self.physics_engine.set_friction(self.player_sprite, 1.0)

        # Check if we have have touched fruit
        fruit_collect_list = arcade.check_for_collision_with_list(
            self.player_sprite,
            self.fruit_list
        )

        if fruit_collect_list:
            self.collect_fruit(fruit_collect_list)

        # Check if we are touching the end of the level
        if arcade.check_for_collision_with_list(self.player_sprite, self.level_end_list):
            self.end_level()

        # Scroll the viewport if needed
        self.scroll_viewport()

        # Move items in the physics engine
        self.physics_engine.step()

    def collect_fruit(self, fruit_list):
        for fruit in fruit_list:
            fruit.remove_from_sprite_lists()
            self.fruit_power = self.fruit_power + 100
            self.play_audio('fruit.mp3')
            self.show_fruit_power()

    def show_fruit_power(self):
        print(self.fruit_power)

    def end_level(self):
        self.close()

    def play_audio(self, file):
        sound = arcade.load_sound("resources/sounds/{}".format(file))
        arcade.play_sound(sound, volume=0.3)

    def on_draw(self):
        """ Draw everything """
        arcade.start_render()
        self.wall_list.draw()
        self.trees_list.draw()
        self.item_list.draw()
        self.cannon_list.draw()
        self.fruit_list.draw()
        self.level_end_list.draw()
        self.player_list.draw()

        # score
        score_text = f"Fruit Power: {self.fruit_power}"
        arcade.draw_rectangle_filled(
            self.view_left,
            self.view_bottom,
            350,
            130,
            arcade.color.BLACK
        )
        arcade.draw_text(score_text,
                         10 + self.view_left,
                         20 + self.view_bottom,
                         arcade.color.WHITE,
                         15
        ) 

    def scroll_viewport(self, force_down=False, force_up=False):
        """ Manage scrolling of the viewport. """

        # Flipped to true if we need to scroll
        changed = False

        # Scroll left
        left_bndry = self.view_left + VIEWPORT_MARGIN_LEFT_RIGHT
        if self.player_sprite.left < left_bndry:
            self.view_left -= left_bndry - self.player_sprite.left
            changed = True

        # Scroll right
        right_bndry = self.view_left + SCREEN_WIDTH - VIEWPORT_MARGIN_LEFT_RIGHT
        if self.player_sprite.right > right_bndry:
            self.view_left += self.player_sprite.right - right_bndry
            changed = True

        # Scroll up
        top_bndry = self.view_bottom + SCREEN_HEIGHT - VIEWPORT_MARGIN_TOP_BOTTOM
        if force_up or self.player_sprite.top > top_bndry:
            self.view_bottom += self.player_sprite.top - top_bndry
            changed = True

        # Scroll down
        bottom_bndry = self.view_bottom + VIEWPORT_MARGIN_TOP_BOTTOM
        if force_down or self.player_sprite.bottom < bottom_bndry:
            self.view_bottom -= bottom_bndry - self.player_sprite.bottom
            changed = True

        if changed:
            arcade.set_viewport(self.view_left,
                                SCREEN_WIDTH + self.view_left,
                                self.view_bottom,
                                SCREEN_HEIGHT + self.view_bottom)

class LevelSelectButton(arcade.gui.UIFlatButton):
    """
    To capture a button click, subclass the button and override on_click.
    """
    def __init__(self, level, menu, **kwargs):
        self.map_name = level
        self.menu = menu
        super().__init__(text=level, **kwargs)

    def on_click(self):
        self.menu.run_level(self.map_name)
        
class MainMenu(arcade.View):
    def __init__(self):
        self.ui_manager = arcade.gui.UIManager()

        # Init the parent class
        super().__init__()

    def on_show(self):
        arcade.set_background_color(arcade.color.DARK_CANDY_APPLE_RED)

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text("{}: version {}".format(GAMENAME, VERSION), SCREEN_WIDTH/2, SCREEN_HEIGHT-50,
                         arcade.color.WHITE, font_size=20, anchor_x="center") 

        arcade.draw_text("Select Level To Load", SCREEN_WIDTH/2, SCREEN_HEIGHT-120,
                         arcade.color.WHITE, font_size=30, anchor_x="center")  

        from glob import glob
        levels = glob("resources/levels/*.tmx")

        start = 170
        level_select = []

        for level in levels:
            button = LevelSelectButton(
                level=level,
                menu=self,  # hack, passing in self
                center_x=SCREEN_WIDTH/2,
                center_y=SCREEN_HEIGHT-start,
                width=500,
                font_size=10,
                # height=20,
                anchor_x="center"
            )
            self.ui_manager.add_ui_element(button)  
            start = start + 40

    @staticmethod
    def quit_game():
        arcade.close_window()
        sys.exit()

    def run_level(self, map_name):
        game_view = GameView()
        game_view.setup(map_name=map_name)
        self.window.show_view(game_view)
        self.ui_manager.unregister_handlers()


def main():
    """ Main method """
    game_window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    main_menu = MainMenu()
    game_window.show_view(main_menu)
    arcade.run()


if __name__ == "__main__":
    main()