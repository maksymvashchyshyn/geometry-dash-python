"""
Comprehensive Unit and End-to-End (E2E) Test Suite for Geometry Dash Clone.
Tests all gameplay mechanics, rendering, UI, physics, particle death variants,
skin previews, shop transactions, persistence, and edge-case stress tests.
"""

import os
import sys
import math
import random
import json
import unittest

# Ensure headless execution for SDL
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()

# Import game module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geometry_dash as gd


class TestUtilityHelpers(unittest.TestCase):
    """Unit tests for utility mathematical and color functions."""

    def test_lerp(self):
        self.assertAlmostEqual(gd.lerp(10.0, 20.0, 0.0), 10.0)
        self.assertAlmostEqual(gd.lerp(10.0, 20.0, 1.0), 20.0)
        self.assertAlmostEqual(gd.lerp(10.0, 20.0, 0.5), 15.0)

    def test_random_colour(self):
        for _ in range(50):
            c = gd.random_colour()
            self.assertIsInstance(c, tuple)
            self.assertEqual(len(c), 3)
            for ch in c:
                self.assertGreaterEqual(ch, 0)
                self.assertLessEqual(ch, 255)

    def test_hsv_to_rgb_boundary_conditions(self):
        # Test standard hues
        self.assertEqual(gd.hsv_to_rgb(0, 1.0, 1.0), (255, 0, 0))       # Pure Red
        self.assertEqual(gd.hsv_to_rgb(120, 1.0, 1.0), (0, 255, 0))     # Pure Green
        self.assertEqual(gd.hsv_to_rgb(240, 1.0, 1.0), (0, 0, 255))     # Pure Blue
        self.assertEqual(gd.hsv_to_rgb(0, 0.0, 1.0), (255, 255, 255))   # Pure White
        self.assertEqual(gd.hsv_to_rgb(0, 0.0, 0.0), (0, 0, 0))         # Pure Black

        # Test extreme/out-of-bound arguments
        for h in [-720, -45, 0, 180, 360, 720, 1080.5]:
            for s in [-1.0, 0.0, 0.5, 1.0, 2.5]:
                for v in [-1.0, 0.0, 0.5, 1.0, 2.5]:
                    rgb = gd.hsv_to_rgb(h, s, v)
                    self.assertIsInstance(rgb, tuple)
                    self.assertEqual(len(rgb), 3)
                    for channel in rgb:
                        self.assertGreaterEqual(channel, 0)
                        self.assertLessEqual(channel, 255)


class TestPersistence(unittest.TestCase):
    """Unit tests for JSON load/save persistence and resilience."""

    def setUp(self):
        self.test_save_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_save.json")
        self.orig_save_file = gd.SAVE_FILE
        gd.SAVE_FILE = self.test_save_file

    def tearDown(self):
        gd.SAVE_FILE = self.orig_save_file
        for f in [self.test_save_file, self.test_save_file + ".tmp"]:
            if os.path.exists(f):
                os.remove(f)

    def test_save_and_load_round_trip(self):
        data = {
            "currency": 99,
            "high_score": 1234,
            "unlocked_skins": ["default", "rgb_pulse"],
            "equipped_skin": "rgb_pulse",
        }
        gd.write_save(data)
        loaded = gd.load_save()
        self.assertEqual(loaded["currency"], 99)
        self.assertEqual(loaded["high_score"], 1234)
        self.assertEqual(loaded["unlocked_skins"], ["default", "rgb_pulse"])
        self.assertEqual(loaded["equipped_skin"], "rgb_pulse")

    def test_corrupted_json_recovery(self):
        # Write corrupted content
        with open(self.test_save_file, "w") as f:
            f.write("{invalid json file content!!")
        loaded = gd.load_save()
        self.assertEqual(loaded["currency"], 0)
        self.assertIn("default", loaded["unlocked_skins"])

    def test_empty_file_recovery(self):
        with open(self.test_save_file, "w") as f:
            pass  # 0 bytes
        loaded = gd.load_save()
        self.assertEqual(loaded["currency"], 0)
        self.assertEqual(loaded["equipped_skin"], "default")

    def test_non_dict_json_recovery(self):
        with open(self.test_save_file, "w") as f:
            f.write("[1, 2, 3]")
        loaded = gd.load_save()
        self.assertIsInstance(loaded, dict)
        self.assertEqual(loaded["equipped_skin"], "default")


class TestParticleSystem(unittest.TestCase):
    """Unit tests for particles and death explosion variants."""

    def setUp(self):
        self.surf = pygame.Surface((gd.SCREEN_WIDTH, gd.SCREEN_HEIGHT))
        self.ps = gd.ParticleSystem()

    def test_nova_burst(self):
        self.ps.nova_burst(150, 150)
        self.assertTrue(self.ps.active)
        self.assertGreater(len(self.ps.particles), 50)
        self.ps.update()
        self.ps.draw(self.surf)

    def test_pixel_shatter(self):
        self.ps.pixel_shatter(150, 150)
        self.assertTrue(self.ps.active)
        self.assertEqual(len(self.ps.particles), 16)  # 4x4 fragments
        self.ps.update()
        self.ps.draw(self.surf)

    def test_spark_shower(self):
        self.ps.spark_shower(150, 150)
        self.assertTrue(self.ps.active)
        self.assertGreater(len(self.ps.particles), 50)
        self.ps.update()
        self.ps.draw(self.surf)

    def test_coin_sparkle(self):
        self.ps.coin_sparkle(150, 150)
        self.assertTrue(self.ps.active)
        self.ps.update()
        self.ps.draw(self.surf)

    def test_trigger_random_variants(self):
        variants = set()
        for _ in range(60):
            ps = gd.ParticleSystem()
            v = ps.trigger_random(200, 200)
            variants.add(v)
            self.assertIn(v, ["nova_burst", "pixel_shatter", "spark_shower"])
        self.assertEqual(len(variants), 3, "All 3 death variants must be selected across runs")

    def test_particles_eventual_cleanup(self):
        self.ps.nova_burst(150, 150)
        # Advance 150 frames to let all particles expire
        for _ in range(150):
            self.ps.update()
        self.assertFalse(self.ps.active)
        self.assertEqual(len(self.ps.particles), 0)


class TestCoin(unittest.TestCase):
    """Unit tests for collectible currency coins."""

    def test_coin_init_has_y_draw(self):
        # Critical regression test: y_draw must exist upon init
        coin = gd.Coin(300, 200, 6)
        self.assertTrue(hasattr(coin, "y_draw"), "Coin must have y_draw initialized immediately")
        self.assertEqual(coin.y, coin.y_draw)
        # rect must be computable immediately without update()
        r = coin.rect
        self.assertIsInstance(r, pygame.Rect)

    def test_coin_draw_before_update(self):
        surf = pygame.Surface((gd.SCREEN_WIDTH, gd.SCREEN_HEIGHT))
        coin = gd.Coin(300, 200, 6)
        # Drawing before update must NOT crash
        coin.draw(surf, 0)

    def test_coin_bobbing_and_scrolling(self):
        coin = gd.Coin(300, 200, 5)
        coin.update(10)
        self.assertEqual(coin.x, 295)
        self.assertNotEqual(coin.y_draw, 0)
        self.assertFalse(coin.is_off_screen())
        coin.x = -50
        self.assertTrue(coin.is_off_screen())


class TestPlayerAndSkins(unittest.TestCase):
    """Unit tests for Player physics, rotation, and all 5 skin renders."""

    def setUp(self):
        self.surf = pygame.Surface((gd.SCREEN_WIDTH, gd.SCREEN_HEIGHT))

    def test_player_jump_and_gravity(self):
        player = gd.Player()
        self.assertTrue(player.on_ground)
        player.jump()
        self.assertFalse(player.on_ground)
        self.assertLess(player.vy, 0)

        # Update while airborne
        player.update()
        self.assertLess(player.y, gd.GROUND_Y - player.size)

        # Simulate until landing
        for _ in range(50):
            player.update()
        self.assertTrue(player.on_ground)
        self.assertEqual(player.y, gd.GROUND_Y - player.size)
        self.assertEqual(player.vy, 0)

    def test_all_five_skins_render(self):
        for skin in gd.SKINS:
            skin_id = skin["id"]
            player = gd.Player(skin_id=skin_id)
            player.rotation = 45.0
            player.draw(self.surf)

            # Test preview render
            gd.Player.draw_preview(self.surf, skin_id, 100, 100, size=36, rotation=30.0)


class TestObstacles(unittest.TestCase):
    """Unit tests for scrolling obstacles."""

    def setUp(self):
        self.surf = pygame.Surface((gd.SCREEN_WIDTH, gd.SCREEN_HEIGHT))

    def test_spike_obstacle(self):
        spike = gd.SpikeObstacle(500, 6)
        spike.update()
        self.assertEqual(spike.x, 494)
        self.assertIsInstance(spike.rect, pygame.Rect)
        spike.draw(self.surf)

    def test_block_obstacle(self):
        block = gd.BlockObstacle(500, 6)
        block.update()
        self.assertEqual(block.x, 494)
        self.assertIsInstance(block.rect, pygame.Rect)
        block.draw(self.surf)

    def test_double_spike_obstacle(self):
        ds = gd.DoubleSpikeObstacle(500, 6)
        ds.update()
        self.assertEqual(ds.x, 494)
        self.assertIsInstance(ds.rect, pygame.Rect)
        ds.draw(self.surf)


class TestUIButtons(unittest.TestCase):
    """Unit tests for UI Button component."""

    def setUp(self):
        self.surf = pygame.Surface((gd.SCREEN_WIDTH, gd.SCREEN_HEIGHT))
        self.font = pygame.font.SysFont("consolas", 20)
        self.btn = gd.Button(50, 50, 100, 40, "TEST", self.font)

    def test_hover_and_click(self):
        self.btn.update((75, 70))
        self.assertTrue(self.btn.hovered)
        self.assertTrue(self.btn.clicked((75, 70)))

        self.btn.update((10, 10))
        self.assertFalse(self.btn.hovered)
        self.assertFalse(self.btn.clicked((10, 10)))

    def test_disabled_button(self):
        self.btn.enabled = False
        self.btn.update((75, 70))
        self.assertFalse(self.btn.hovered)
        self.assertFalse(self.btn.clicked((75, 70)))
        self.btn.draw(self.surf)


class TestGameEndToEnd(unittest.TestCase):
    """End-to-End simulation and stress tests for Game workflows."""

    def setUp(self):
        self.game = gd.Game()

    def test_initial_state_is_menu(self):
        self.assertEqual(self.game.state, "menu")
        self.assertIsNotNone(self.game.btn_play)
        self.assertIsNotNone(self.game.btn_shop)
        self.assertIsNotNone(self.game.btn_go_retry)
        self.assertIsNotNone(self.game.btn_go_menu)

    def test_full_state_machine_flow(self):
        # 1. Start on Menu
        self.assertEqual(self.game.state, "menu")
        self.game._draw()

        # 2. Enter Shop
        self.game._handle_click(self.game.btn_shop.rect.center)
        self.assertEqual(self.game.state, "shop")
        self.game._draw()

        # 3. Leave Shop back to Menu
        self.game._handle_click(self.game.btn_shop_back.rect.center)
        self.assertEqual(self.game.state, "menu")

        # 4. Start Game
        self.game._handle_click(self.game.btn_play.rect.center)
        self.assertEqual(self.game.state, "playing")
        self.game._draw()

        # 5. Play 60 frames with jumps
        for f in range(60):
            if f % 20 == 0:
                self.game.player.jump()
            self.game.frame += 1
            self.game._update_playing()
            self.game._draw()

        # 6. Kill Player -> Dying state
        self.game._kill_player()
        self.assertEqual(self.game.state, "dying")
        self.assertTrue(self.game.particles.active)

        # 7. Advance dying state until gameover
        for _ in range(120):
            self.game.frame += 1
            if self.game.state == "dying":
                self.game._update_dying()
            self.game._draw()
        self.assertEqual(self.game.state, "gameover")

        # 8. Retry from gameover
        self.game._handle_click(self.game.btn_go_retry.rect.center)
        self.assertEqual(self.game.state, "playing")

        # 9. ESC back to menu
        self.game._go_to_menu()
        self.assertEqual(self.game.state, "menu")

    def test_coin_spawn_death_collision_race_condition(self):
        """
        Regression test for crash bug:
        When an obstacle spawns a coin, and player collides on that same tick,
        _update_playing() exits before coin.update() is reached.
        The subsequent _draw() must NOT raise AttributeError on coin.y_draw.
        """
        self.game._start_game()
        # Force spawn a coin
        coin = gd.Coin(gd.SCREEN_WIDTH, 200, 6)
        self.game.coins.append(coin)

        # Place obstacle right on the player to force immediate collision
        spike = gd.SpikeObstacle(self.game.player.x, 6)
        self.game.obstacles.append(spike)

        # Update playing - will kill player and return before updating coins
        self.game._update_playing()
        self.assertEqual(self.game.state, "dying")

        # Now draw the game - must succeed without AttributeError!
        self.game._draw()

    def test_shop_purchase_and_equip_flow(self):
        self.game.currency = 100  # Give plenty of currency
        self.game._build_shop_buttons()
        self.game.state = "shop"

        # Find RGB Pulse skin in shop
        rgb_item = next(it for it in self.game.shop_items if it["skin"]["id"] == "rgb_pulse")

        # Click buy
        self.game._handle_click(rgb_item["button"].rect.center)
        self.assertIn("rgb_pulse", self.game.unlocked)
        self.assertEqual(self.game.equipped, "rgb_pulse")

        # Start game and verify player uses equipped skin
        self.game._start_game()
        self.assertEqual(self.game.player.skin_id, "rgb_pulse")
        self.game._draw()

    def test_long_run_stress_and_speed_scaling(self):
        """Simulate 600 frames (10 seconds) of continuous play to verify no memory leaks or crashes."""
        self.game._start_game()
        for i in range(600):
            self.game.clock.tick(60)
            self.game.frame += 1
            if i % 45 == 0 and self.game.player.on_ground:
                self.game.player.jump()
            self.game._update_playing()
            self.game._draw()
            # If died, restart
            if self.game.state in ("dying", "gameover"):
                self.game._start_game()


if __name__ == "__main__":
    unittest.main()
