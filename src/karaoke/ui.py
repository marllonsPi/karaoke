from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame


@dataclass
class UIState:
    title: str
    artist: Optional[str]
    current_line: str
    next_line: str
    score_total: float
    score_pitch: float
    score_rhythm: float
    notes_done: int
    notes_total: int


class PygameUI:
    def __init__(self, fullscreen: bool = False, size: tuple[int, int] | None = None):
        pygame.init()
        flags = pygame.FULLSCREEN if fullscreen else 0
        if size is None:
            self.screen = pygame.display.set_mode((0, 0), flags)
        else:
            self.screen = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("Karaoke com Nota")

        self.clock = pygame.time.Clock()
        self.width, self.height = self.screen.get_size()
        self.font_title = pygame.font.SysFont("DejaVu Sans", 48, bold=True)
        self.font_line = pygame.font.SysFont("DejaVu Sans", 52, bold=True)
        self.font_next = pygame.font.SysFont("DejaVu Sans", 34)
        self.font_meta = pygame.font.SysFont("DejaVu Sans", 28)

    def update(self, state: UIState) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                return False

        self._draw_background()
        self._draw_header(state)
        self._draw_lyrics(state)
        self._draw_scores(state)

        pygame.display.flip()
        self.clock.tick(30)
        return True

    def _draw_background(self) -> None:
        self.screen.fill((10, 12, 18))
        top = pygame.Color(18, 30, 54)
        bottom = pygame.Color(6, 8, 14)
        for y in range(self.height):
            ratio = y / max(self.height - 1, 1)
            r = int(top.r * (1 - ratio) + bottom.r * ratio)
            g = int(top.g * (1 - ratio) + bottom.g * ratio)
            b = int(top.b * (1 - ratio) + bottom.b * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (self.width, y))

    def _draw_header(self, state: UIState) -> None:
        title = state.title
        if state.artist:
            title = f\"{state.title} - {state.artist}\"
        text = self.font_title.render(title, True, (240, 240, 240))
        self.screen.blit(text, (40, 24))

    def _draw_lyrics(self, state: UIState) -> None:
        line = state.current_line or \"\"
        next_line = state.next_line or \"\"
        line_surf = self.font_line.render(line, True, (255, 236, 156))
        next_surf = self.font_next.render(next_line, True, (190, 190, 190))

        line_rect = line_surf.get_rect(center=(self.width // 2, self.height // 2))
        next_rect = next_surf.get_rect(center=(self.width // 2, self.height // 2 + 70))

        self.screen.blit(line_surf, line_rect)
        self.screen.blit(next_surf, next_rect)

    def _draw_scores(self, state: UIState) -> None:
        score_text = f\"Total: {state.score_total:05.1f}  |  Afinacao: {state.score_pitch:05.1f}  |  Ritmo: {state.score_rhythm:05.1f}\"
        meta_text = f\"Notas: {state.notes_done}/{state.notes_total}\"

        score_surf = self.font_meta.render(score_text, True, (180, 220, 255))
        meta_surf = self.font_meta.render(meta_text, True, (150, 150, 150))

        self.screen.blit(score_surf, (40, self.height - 80))
        self.screen.blit(meta_surf, (40, self.height - 45))

    def close(self) -> None:
        pygame.quit()
