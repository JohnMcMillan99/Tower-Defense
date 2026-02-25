"""
Swarm FX - Pygame particle effects for Circuit Stronghold.

Handles visual effects for Swarm Latch mechanics including tendrils,
stack scaling, particle clusters, and corruption effects.
"""

import pygame
import random
import math
import sys

# pygbag compatibility - check if gfxdraw is available
try:
    import pygame.gfxdraw
    GFXDRAW_AVAILABLE = True
except ImportError:
    GFXDRAW_AVAILABLE = False

class ParticleEmitter:
    """Base particle emitter for swarm effects."""

    def __init__(self, pos, color, count, lifetime, velocity_range):
        self.pos = list(pos)
        self.color = color
        self.count = count
        self.lifetime = lifetime
        self.velocity_range = velocity_range
        self.particles = []
        self._generate_particles()

    def _generate_particles(self):
        """Generate initial particles."""
        for _ in range(self.count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*self.velocity_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            particle = {
                'x': self.pos[0],
                'y': self.pos[1],
                'vx': vx,
                'vy': vy,
                'life': random.uniform(0.5, 1.0) * self.lifetime,
                'max_life': self.lifetime,
                'size': random.uniform(1, 3)
            }
            self.particles.append(particle)

    def update(self, dt):
        """Update particle positions and lifetimes."""
        for particle in self.particles[:]:
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            particle['life'] -= dt

            # Remove dead particles
            if particle['life'] <= 0:
                self.particles.remove(particle)

    def draw(self, surface):
        """Draw particles to surface."""
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            color = (*self.color[:3], alpha)

            # Draw particle as circle - use gfxdraw if available, fallback to regular circle
            if GFXDRAW_AVAILABLE:
                pygame.gfxdraw.filled_circle(
                    surface,
                    int(particle['x']),
                    int(particle['y']),
                    int(particle['size']),
                    color
                )
            else:
                # Fallback: draw a small rectangle
                rect = pygame.Rect(
                    int(particle['x'] - particle['size']),
                    int(particle['y'] - particle['size']),
                    int(particle['size'] * 2),
                    int(particle['size'] * 2)
                )
                pygame.draw.rect(surface, color, rect)

class SwarmCluster:
    """Visual representation of latched assimilator swarm."""

    def __init__(self, pos, enemy_count, color=(100, 200, 255)):
        self.pos = pos
        self.enemy_count = enemy_count
        self.color = color
        self.pulse_timer = 0
        self.pulse_rate = 0.05

        # Calculate cluster size based on stack count
        self._calculate_cluster_size()

    def _calculate_cluster_size(self):
        """Calculate visual size based on enemy count."""
        if self.enemy_count <= 2:
            self.radius = 8
            self.intensity = 0.7
        elif self.enemy_count <= 6:
            self.radius = 12
            self.intensity = 0.85
        else:
            self.radius = 16
            self.intensity = 1.0

    def update(self, dt):
        """Update pulsing animation."""
        self.pulse_timer += self.pulse_rate
        if self.pulse_timer > 2 * math.pi:
            self.pulse_timer -= 2 * math.pi

    def draw(self, surface):
        """Draw the swarm cluster with pulsing effect."""
        pulse = math.sin(self.pulse_timer) * 0.3 + 0.7
        current_radius = int(self.radius * pulse * self.intensity)

        # Draw outer glow
        glow_color = (int(self.color[0] * 0.5), int(self.color[1] * 0.5), int(self.color[2] * 0.5))
        if GFXDRAW_AVAILABLE:
            pygame.gfxdraw.filled_circle(
                surface,
                self.pos[0],
                self.pos[1],
                current_radius + 3,
                (*glow_color, 100)
            )
        else:
            pygame.draw.circle(surface, glow_color, self.pos, current_radius + 3, 1)

        # Draw main cluster
        cluster_color = (
            int(self.color[0] * self.intensity),
            int(self.color[1] * self.intensity),
            int(self.color[2] * self.intensity)
        )
        if GFXDRAW_AVAILABLE:
            pygame.gfxdraw.filled_circle(
                surface,
                self.pos[0],
                self.pos[1],
                current_radius,
                (*cluster_color, 200)
            )
        else:
            pygame.draw.circle(surface, cluster_color, self.pos, current_radius)

        # Draw tendrils extending from cluster
        self._draw_tendrils(surface, current_radius)

    def _draw_tendrils(self, surface, cluster_radius):
        """Draw corruption tendrils extending from the cluster."""
        tendril_count = min(self.enemy_count, 8)  # Max 8 tendrils

        for i in range(tendril_count):
            angle = (i / tendril_count) * 2 * math.pi
            length = cluster_radius + random.uniform(5, 15)

            end_x = self.pos[0] + math.cos(angle) * length
            end_y = self.pos[1] + math.sin(angle) * length

            # Draw tendril line
            tendril_color = (*self.color[:3], 150)
            pygame.draw.line(
                surface,
                tendril_color,
                (self.pos[0], self.pos[1]),
                (end_x, end_y),
                2
            )

class TraceGlow:
    """Glowing effect for active circuit traces."""

    def __init__(self, path_segment, intensity):
        self.path_segment = path_segment  # ((x1,y1), (x2,y2))
        self.intensity = intensity
        self.glow_timer = 0
        self.glow_rate = 0.1

    def update(self, dt):
        """Update glow animation."""
        self.glow_timer += self.glow_rate

    def draw(self, surface):
        """Draw glowing trace segment."""
        start, end = self.path_segment
        glow_intensity = (math.sin(self.glow_timer) * 0.3 + 0.7) * self.intensity

        # Draw glow around the trace
        glow_color = (255, 255, 150, int(100 * glow_intensity))

        # Draw thicker line for glow effect
        pygame.draw.line(
            surface,
            glow_color,
            start,
            end,
            6  # Thicker than normal trace
        )

class DamageNumber:
    """Floating damage numbers for visual feedback."""

    def __init__(self, pos, value, lifetime=60, color=(255, 100, 100)):
        self.pos = list(pos)
        self.value = value
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.velocity = [random.uniform(-1, 1), random.uniform(-2, -1)]  # Float upward

    def update(self, dt):
        """Update position and lifetime."""
        self.pos[0] += self.velocity[0] * dt
        self.pos[1] += self.velocity[1] * dt
        self.lifetime -= dt

    def draw(self, surface):
        """Draw the damage number."""
        if self.lifetime <= 0:
            return

        alpha = int(255 * (self.lifetime / self.max_lifetime))
        color = (*self.color[:3], alpha)

        # Render text (use built-in font in browser - SysFont not available)
        font = pygame.font.Font(None, 16) if sys.platform == "emscripten" else pygame.font.SysFont('Arial', 16, bold=True)
        text = font.render(str(self.value), True, color)

        # Draw text with slight shadow for visibility
        shadow_color = (0, 0, 0, alpha // 2)
        shadow_text = font.render(str(self.value), True, shadow_color)

        surface.blit(shadow_text, (self.pos[0] + 1, self.pos[1] + 1))
        surface.blit(text, self.pos)

class SwarmFXManager:
    """Manages all swarm visual effects."""

    def __init__(self):
        self.particle_emitters = []
        self.swarm_clusters = []
        self.trace_glows = []
        self.damage_numbers = []

    def add_latch_effect(self, pos, stack_count):
        """
        Add visual effect for assimilator latching.

        Args:
            pos: (x, y) position of latch
            stack_count: Number of assimilators in stack
        """
        # Add particle burst
        color = (100, 200, 255)  # Blue for latch
        emitter = ParticleEmitter(pos, color, 10, 30, (20, 50))
        self.particle_emitters.append(emitter)

        # Add swarm cluster
        cluster = SwarmCluster(pos, stack_count, color)
        self.swarm_clusters.append(cluster)

    def add_corruption_effect(self, pos, intensity=1.0):
        """
        Add corruption visual effect.

        Args:
            pos: (x, y) position of corruption
            intensity: Effect intensity (0.0-1.0)
        """
        # Add red particle burst for corruption
        color = (255, 100, 100)
        emitter = ParticleEmitter(pos, color, 15, 45, (30, 70))
        self.particle_emitters.append(emitter)

    def add_damage_number(self, pos, damage):
        """
        Add floating damage number.

        Args:
            pos: (x, y) position to display damage
            damage: Damage value to display
        """
        number = DamageNumber(pos, damage)
        self.damage_numbers.append(number)

    def add_trace_glow(self, path_segment, intensity=0.8):
        """
        Add glowing effect to a path segment.

        Args:
            path_segment: ((x1,y1), (x2,y2)) segment to glow
            intensity: Glow intensity (0.0-1.0)
        """
        glow = TraceGlow(path_segment, intensity)
        self.trace_glows.append(glow)

    def update(self, dt):
        """Update all effects."""
        # Update and remove dead emitters
        for emitter in self.particle_emitters[:]:
            emitter.update(dt)
            if not emitter.particles:
                self.particle_emitters.remove(emitter)

        # Update clusters
        for cluster in self.swarm_clusters:
            cluster.update(dt)

        # Update and remove dead damage numbers
        for number in self.damage_numbers[:]:
            number.update(dt)
            if number.lifetime <= 0:
                self.damage_numbers.remove(number)

        # Update glows
        for glow in self.trace_glows:
            glow.update(dt)

    def draw(self, surface):
        """Draw all effects to surface."""
        # Draw glows first (background)
        for glow in self.trace_glows:
            glow.draw(surface)

        # Draw particle effects
        for emitter in self.particle_emitters:
            emitter.draw(surface)

        # Draw swarm clusters
        for cluster in self.swarm_clusters:
            cluster.draw(surface)

        # Draw damage numbers (foreground)
        for number in self.damage_numbers:
            number.draw(surface)

    def draw_latch(self, surface, assimilator_pos, target_pos, stack_count, world_to_screen):
        """
        Draw latch tendrils and effects from assimilator to target.

        Args:
            surface: Pygame surface to draw on
            assimilator_pos: (x, y) world position of assimilator
            target_pos: (x, y) world position of target (wall or tower)
            stack_count: Number of assimilators in stack
            world_to_screen: Function to convert world coords to screen coords
        """
        # Convert positions to screen coordinates
        assim_screen = world_to_screen(assimilator_pos[0], assimilator_pos[1])
        target_screen = world_to_screen(target_pos[0], target_pos[1])

        # Draw tendrils - red curved lines from assimilator to target
        if GFXDRAW_AVAILABLE:
            # Use pygame.gfxdraw for smoother arcs
            self._draw_tendrils_gfxdraw(surface, assim_screen, target_screen, stack_count)
        else:
            # Fallback to pygame.draw
            self._draw_tendrils_fallback(surface, assim_screen, target_screen, stack_count)

        # Draw scaling circles/particles at target
        self._draw_latch_particles(surface, target_screen, stack_count)

    def _draw_tendrils_gfxdraw(self, surface, start_pos, end_pos, stack_count):
        """Draw curved tendrils using pygame.gfxdraw.arc."""
        start_x, start_y = start_pos
        end_x, end_y = end_pos

        # Calculate direction and distance
        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.sqrt(dx*dx + dy*dy)

        if distance < 1:
            return  # Too close, skip

        # Number of tendrils based on stack count
        tendril_count = min(stack_count, 4)  # Max 4 tendrils

        # Red color with varying intensity
        base_color = (255, 50, 50)

        for i in range(tendril_count):
            # Offset each tendril slightly for spread effect
            offset_factor = (i - (tendril_count - 1) / 2) * 0.1
            perp_x = -dy / distance * offset_factor * 20
            perp_y = dx / distance * offset_factor * 20

            # Create control points for bezier-like curve
            mid_x = (start_x + end_x) / 2 + perp_x
            mid_y = (start_y + end_y) / 2 + perp_y

            # Draw multiple segments to approximate curve
            segments = 8
            for j in range(segments):
                t1 = j / segments
                t2 = (j + 1) / segments

                # Quadratic bezier interpolation
                x1 = (1-t1)**2 * start_x + 2*(1-t1)*t1 * mid_x + t1**2 * end_x
                y1 = (1-t1)**2 * start_y + 2*(1-t1)*t1 * mid_y + t1**2 * end_y
                x2 = (1-t2)**2 * start_x + 2*(1-t2)*t2 * mid_x + t2**2 * end_x
                y2 = (1-t2)**2 * start_y + 2*(1-t2)*t2 * mid_y + t2**2 * end_y

                # Draw line segment
                pygame.gfxdraw.line(surface, int(x1), int(y1), int(x2), int(y2), base_color)

    def _draw_tendrils_fallback(self, surface, start_pos, end_pos, stack_count):
        """Fallback tendril drawing using pygame.draw."""
        start_x, start_y = start_pos
        end_x, end_y = end_pos

        # Number of tendrils based on stack count
        tendril_count = min(stack_count, 4)

        # Red color
        color = (255, 50, 50)

        for i in range(tendril_count):
            # Simple straight lines with slight randomization
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)
            pygame.draw.line(surface, color,
                           (start_x + offset_x, start_y + offset_y),
                           (end_x + offset_x, end_y + offset_y), 2)

    def _draw_latch_particles(self, surface, center_pos, stack_count):
        """Draw particle effects at latch target."""
        center_x, center_y = center_pos

        # Scale particle count and size with stack
        particle_count = min(stack_count * 2, 20)  # Up to 20 particles
        base_radius = 5 + stack_count  # 5 + stack for radius scaling

        # Draw filled circles for dense swarm effect when stack >= 5
        if stack_count >= 5:
            # Outer glow circle
            glow_color = (255, 100, 100, 100)  # Semi-transparent red
            for r in range(base_radius + 5, base_radius - 1, -1):
                alpha = 255 - (r - base_radius) * 20
                color = (255, 100, 100, max(50, alpha))
                if GFXDRAW_AVAILABLE:
                    pygame.gfxdraw.filled_circle(surface, center_x, center_y, r, color)
                else:
                    pygame.draw.circle(surface, color, (center_x, center_y), r)

        # Draw individual particles
        for i in range(particle_count):
            angle = (i / particle_count) * 2 * math.pi
            distance = random.uniform(base_radius * 0.5, base_radius * 1.5)
            x = center_x + math.cos(angle) * distance
            y = center_y + math.sin(angle) * distance

            size = random.uniform(1, 3)
            color = (255, random.randint(50, 150), 50)

            if GFXDRAW_AVAILABLE:
                pygame.gfxdraw.filled_circle(surface, int(x), int(y), int(size), color)
            else:
                pygame.draw.circle(surface, color, (int(x), int(y)), int(size))

    def clear_latch_effects(self):
        """Clear all latch-related visual effects."""
        self.swarm_clusters.clear()
        # Keep other effects as they might be temporary

    def get_active_effects_count(self):
        """Get count of currently active effects."""
        return {
            'emitters': len(self.particle_emitters),
            'clusters': len(self.swarm_clusters),
            'glows': len(self.trace_glows),
            'damage_numbers': len(self.damage_numbers)
        }