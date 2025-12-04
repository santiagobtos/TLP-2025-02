# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# tkinter_snake_tetris_full_py2.py
# Consola Retro 2000 — Snake & Tetris (convertido a Python 2.7)

# Ejecutar: python2 tkinter_snake_tetris_full_py2.py

import Tkinter as tk
import ttk
import tkFont as font
import tkMessageBox as messagebox
import time
import random

# -------------------- CONFIG --------------------
CELL_MIN = 12
CELL_MAX = 40
TICK_MS = 40

# -------------------- UTILIDADES --------------------
KEYMAP = {
    'w': 'w', 'a': 'a', 's': 's', 'd': 'd',
    'r': 'r', 'p': 'p',
    'Escape': 'esc',
    'Up': 'Up', 'Down': 'Down', 'Left': 'Left', 'Right': 'Right'
}

def clamp(v, a, b):
    return max(a, min(b, v))

# -------------------- JUEGOS --------------------
class JuegoSnake:
    """Snake con obstáculos y comidas especiales."""
    def __init__(self, cols=28, rows=20, velocidad=6.0, obstaculos_cantidad=8):
        self.cols = cols
        self.rows = rows
        self.base_speed = velocidad
        self.velocidad = velocidad
        self.obstaculos_cantidad = obstaculos_cantidad
        self.reiniciar()

    def reiniciar(self):
        cx, cy = self.cols // 2, self.rows // 2
        self.cuerpo = [(cx-2, cy), (cx-1, cy), (cx, cy)]
        self.dir = (1, 0)
        self.puntaje = 0
        self.muerto = False
        self.pausado = False
        self.comidas = []       # lista dicts: {'x','y','tipo','puntos','expira'}
        self.obstaculos = []
        self._acum = 0.0
        self.tiempo = 0.0
        self._special_timer = 0.0
        self._special_active = None
        self.velocidad = self.base_speed
        # generar obstaculos
        self._generar_obstaculos()
        # generar comida normal inicial
        for _ in range(2):
            self._nueva_comida_normal()

    def _pos_libre(self):
        tries = 0
        while tries < 5000:
            x = random.randrange(self.cols)
            y = random.randrange(self.rows)
            if (x,y) not in self.cuerpo and (x,y) not in self.obstaculos and not any((c['x'],c['y'])==(x,y) for c in self.comidas):
                return x,y
            tries += 1
        return 0,0

    def _generar_obstaculos(self):
        self.obstaculos = []
        tries = 0
        while len(self.obstaculos) < self.obstaculos_cantidad and tries < 10000:
            x,y = random.randrange(self.cols), random.randrange(self.rows)
            if (x,y) not in self.cuerpo:
                self.obstaculos.append((x,y))
            tries += 1

    def _nueva_comida_normal(self):
        fx, fy = self._pos_libre()
        self.comidas.append({'x':fx,'y':fy,'tipo':'normal','puntos':10,'expira':18.0})

    def _spawn_special(self):
        # probabilidades pequeñas para diferentes especiales
        r = random.random()
        fx, fy = self._pos_libre()
        if r < 0.08:
            # dorada (puntos extra)
            self.comidas.append({'x':fx,'y':fy,'tipo':'dorada','puntos':50,'expira':10.0})
        elif r < 0.14:
            # negra (pésima): resta puntos y reduce largo
            self.comidas.append({'x':fx,'y':fy,'tipo':'negra','puntos':-50,'expira':10.0})
        elif r < 0.20:
            # velocidad (acelera)
            self.comidas.append({'x':fx,'y':fy,'tipo':'velocidad','puntos':0,'expira':8.0})
        elif r < 0.26:
            # lenta (ralentiza)
            self.comidas.append({'x':fx,'y':fy,'tipo':'lenta','puntos':0,'expira':8.0})

    def manejar_input(self, key):
        if key is None:
            return
        if key == 'p':
            self.pausado = not self.pausado
            return
        if self.pausado:
            return
        # movimiento (proteger retorno)
        if key in ('w', 'Up') and self.dir != (0,1):
            self.dir = (0, -1)
        elif key in ('s', 'Down') and self.dir != (0,-1):
            self.dir = (0, 1)
        elif key in ('a', 'Left') and self.dir != (1,0):
            self.dir = (-1, 0)
        elif key in ('d', 'Right') and self.dir != (-1,0):
            self.dir = (1, 0)

    def paso(self, dt):
        if self.muerto or self.pausado:
            return True
        self.tiempo += dt
        self._acum += dt
        # efectos especiales temporales
        if self._special_active:
            self._special_timer -= dt
            if self._special_timer <= 0:
                # revertir efecto
                if self._special_active == 'velocidad':
                    self.velocidad = self.base_speed
                elif self._special_active == 'lenta':
                    self.velocidad = self.base_speed
                self._special_active = None

        # spawn specials occasionally
        if random.random() < 0.01:
            self._spawn_special()

        # decrementar expiraciones de comidas
        for c in list(self.comidas):
            c['expira'] -= dt
            if c['expira'] <= 0:
                try:
                    self.comidas.remove(c)
                except ValueError:
                    pass

        paso_t = 1.0 / max(1.0, self.velocidad)
        if self._acum < paso_t:
            return True
        self._acum -= paso_t

        hx, hy = self.cuerpo[-1]
        nx, ny = hx + self.dir[0], hy + self.dir[1]

        # colisiones con paredes
        if nx < 0 or nx >= self.cols or ny < 0 or ny >= self.rows:
            self.muerto = True
            return True
        # colision con cuerpo
        if (nx, ny) in self.cuerpo:
            self.muerto = True
            return True
        # colision con obstaculos
        if (nx, ny) in self.obstaculos:
            self.muerto = True
            return True

        # mover cabeza
        self.cuerpo.append((nx, ny))

        # ver si comió algo
        comida = None
        for c in list(self.comidas):
            if (nx,ny) == (c['x'], c['y']):
                comida = c
                break

        if comida:
            # aplicar efecto
            tipo = comida.get('tipo', 'normal')
            if tipo == 'normal':
                self.puntaje += comida.get('puntos', 10)
            elif tipo == 'dorada':
                self.puntaje += comida.get('puntos', 50)
            elif tipo == 'negra':
                self.puntaje += comida.get('puntos', -50)
                # eliminar primer segmento si existe (encoger)
                if len(self.cuerpo) > 1:
                    self.cuerpo.pop(0)
            elif tipo == 'velocidad':
                self._special_active = 'velocidad'
                self._special_timer = 5.0
                self.velocidad = min(self.base_speed * 1.8, 20.0)
            elif tipo == 'lenta':
                self._special_active = 'lenta'
                self._special_timer = 5.0
                self.velocidad = max(self.base_speed * 0.5, 0.5)

            try:
                self.comidas.remove(comida)
            except ValueError:
                pass
            # cuando come, añadir nueva comida normal
            self._nueva_comida_normal()
        else:
            # si no comió, se mueve: eliminar cola
            self.cuerpo.pop(0)

        # pequeño aumento de velocidad por tiempo/puntos (opcional)
        if self.puntaje and self.puntaje % 100 == 0:
            self.velocidad = min(self.base_speed + self.puntaje / 100.0, 18.0)

        return True

class JuegoTetris:
    """Tetris funcional y básico."""
    def __init__(self, cols=10, rows=20, fall_speed=1.0):
        self.cols = cols
        self.rows = rows
        self.fall_speed = fall_speed
        self.reiniciar()

    def reiniciar(self):
        self.tablero = [[0 for _ in range(self.cols)] for __ in range(self.rows)]
        self.puntaje = 0
        self.nivel = 1
        self._acc = 0.0
        self.terminado = False
        self.pausado = False
        self._spawn()

    def _pieces(self):
        return [
            {'name':'I','rots':[[[1,1,1,1]],[[1],[1],[1],[1]]]},
            {'name':'O','rots':[[[1,1],[1,1]]]},
            {'name':'T','rots':[[[0,1,0],[1,1,1]],[[1,0],[1,1],[1,0]],[[1,1,1],[0,1,0]],[[0,1],[1,1],[0,1]]]},
            {'name':'L','rots':[[[1,0],[1,0],[1,1]],[[0,0,1],[1,1,1]],[[1,1],[0,1],[0,1]],[[1,1,1],[1,0,0]]]},
            {'name':'J','rots':[[[0,1],[0,1],[1,1]],[[1,1,1],[0,0,1]],[[1,1],[1,0],[1,0]],[[1,0,0],[1,1,1]]]},
            {'name':'S','rots':[[[0,1,1],[1,1,0]],[[1,0],[1,1],[0,1]]]},
            {'name':'Z','rots':[[[1,1,0],[0,1,1]],[[0,1],[1,1],[1,0]]]},
        ]

    def _spawn(self):
        self.pieces = self._pieces()
        self.current = random.choice(self.pieces)
        self.rot = 0
        self.px = self.cols // 2 - 2
        self.py = 0
        if self._collide(self.px, self.py, self.rot):
            self.terminado = True

    def _shape(self, r=None):
        r = self.rot if r is None else r
        return self.current['rots'][r % len(self.current['rots'])]

    def _collide(self, x, y, r):
        m = self._shape(r)
        for j, row in enumerate(m):
            for i, v in enumerate(row):
                if v:
                    bx, by = x + i, y + j
                    if bx < 0 or bx >= self.cols or by < 0 or by >= self.rows:
                        return True
                    if self.tablero[by][bx]:
                        return True
        return False

    def _fix(self):
        m = self._shape()
        for j, row in enumerate(m):
            for i, v in enumerate(row):
                if v:
                    bx, by = self.px + i, self.py + j
                    if 0 <= bx < self.cols and 0 <= by < self.rows:
                        self.tablero[by][bx] = 1
        self._clear_lines()
        self._spawn()

    def _clear_lines(self):
        llenas = [y for y in range(self.rows) if all(self.tablero[y][x] for x in range(self.cols))]
        for y in reversed(llenas):
            del self.tablero[y]
            self.tablero.insert(0, [0 for _ in range(self.cols)])
        self.puntaje += len(llenas)

    def manejar_input(self, key):
        if key is None:
            return
        if key == 'p':
            self.pausado = not self.pausado
            return
        if self.pausado:
            return
        if key in ('Left', 'a') and not self._collide(self.px - 1, self.py, self.rot):
            self.px -= 1
        elif key in ('Right', 'd') and not self._collide(self.px + 1, self.py, self.rot):
            self.px += 1
        elif key in ('w', 'Up'):
            nuevo = (self.rot + 1) % len(self.current['rots'])
            if not self._collide(self.px, self.py, nuevo):
                self.rot = nuevo
            elif not self._collide(self.px + 1, self.py, nuevo):
                self.px += 1
                self.rot = nuevo
            elif not self._collide(self.px - 1, self.py, nuevo):
                self.px -= 1
                self.rot = nuevo
        elif key in ('s', 'Down'):
            if not self._collide(self.px, self.py + 1, self.rot):
                self.py += 1
            else:
                self._fix()

    def paso(self, dt):
        if self.terminado or self.pausado:
            return True
        cps = max(0.2, self.fall_speed)
        self._acc += dt
        paso_t = 1.0 / cps
        if self._acc >= paso_t:
            self._acc -= paso_t
            if not self._collide(self.px, self.py + 1, self.rot):
                self.py += 1
            else:
                self._fix()
        return True

# -------------------- GUI --------------------
class RetroApp(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(u"Consola Retro 2000 — 2 juegos y 1998 en desarrollo — Disponibles: Snake & Tetris")
        self.configure(bg="#0f0f10")
        self.minsize(900, 600)

        # fonts
        self.f_title = font.Font(family="Courier", size=18, weight="bold")
        self.f_m = font.Font(family="Courier", size=11)
        self.f_small = font.Font(family="Courier", size=9)

        # layout (left selection + main)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.left_panel = tk.Frame(self, bg="#171717", bd=2, relief="ridge")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_panel.grid_rowconfigure(6, weight=1)

        # main panel improved: thick ridge, nicer background
        self.main_panel = tk.Frame(self, bg="#0b0b0b", bd=4, relief="ridge", highlightbackground="#3b3b3b", highlightthickness=2)
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_panel.grid_rowconfigure(0, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        self._build_left()
        self._build_main()

        # state
        self.active_game = None
        self.game_type = None
        self.last_time = time.time()
        self.canvas_width = 800
        self.canvas_height = 500
        self.crt_enabled = False

        self.after(TICK_MS, self._loop)
        self.bind_all('<Key>', self._on_key)
        self.protocol("WM_DELETE_WINDOW", self.quit)

    def _build_left(self):
        tk.Label(self.left_panel, text=u"Consola Retro 2000", font=self.f_title, fg="#7CFFB2", bg="#171717").pack(pady=(12, 6))
        tk.Label(self.left_panel, text=u"(sí, 2 juegos y 1998 en desarrollo)", font=self.f_m, fg="#CFEFE3", bg="#171717").pack(pady=(0, 8))

        # <-- CAMBIO: reemplazamos el combobox por DOS BOTONES: Snake y Tetris -->
        btn_frame_top = tk.Frame(self.left_panel, bg="#171717")
        btn_frame_top.pack(padx=12, pady=(0,8), fill='x')
        # Botón Snake
        ttk.Button(btn_frame_top, text=u"Snake", command=self._start_snake).pack(side='left', expand=True, fill='x', padx=4)
        # Botón Tetris
        ttk.Button(btn_frame_top, text=u"Tetris", command=self._start_tetris).pack(side='left', expand=True, fill='x', padx=4)
        # <-- FIN CAMBIO -->

        btn_frame = tk.Frame(self.left_panel, bg="#171717")
        btn_frame.pack(pady=8, fill='x', padx=10)
        ttk.Button(btn_frame, text=u"Reiniciar", command=self._restart).pack(side='left', expand=True, fill='x', padx=4)

        ttk.Button(self.left_panel, text=u"Controles / Reglas", command=self._show_info).pack(fill='x', padx=12, pady=6)
        ttk.Button(self.left_panel, text=u"Efecto CRT", command=self._toggle_crt).pack(fill='x', padx=12, pady=6)

        # legend / explanations persistent
        lbl = tk.Label(self.left_panel, text=u"Leyenda (Snake):\n* rojo = comida normal (+10)\n* dorada = +50\n* negra = -50 y encoge\n* morada = acelera 5s\n* cyan = ralentiza 5s\n* gris = obstáculo (muerte)", justify='left', bg="#171717", fg="#E6F9EA", font=self.f_small, wraplength=220)
        lbl.pack(padx=10, pady=10, fill='x')

        self.status_var = tk.StringVar(value=u"Listo — elige Snake o Tetris arriba")
        tk.Label(self.left_panel, textvariable=self.status_var, bg="#171717", fg="#CFEFE3", font=self.f_small, wraplength=220, justify='left').pack(pady=(8,6), padx=8)

    def _build_main(self):
        # header
        header = tk.Frame(self.main_panel, bg="#111111")
        header.grid(row=0, column=0, sticky='ew')
        header.grid_columnconfigure(1, weight=1)
        self.lbl_game_title = tk.Label(header, text=u"Ningún juego activo", font=self.f_m, fg="#FFD27A", bg="#111111")
        self.lbl_game_title.grid(row=0, column=0, sticky='w', padx=8, pady=8)
        self.score_var = tk.StringVar(value=u"Puntos: 0")
        tk.Label(header, textvariable=self.score_var, font=self.f_small, fg="#CFEFE3", bg="#111111").grid(row=0, column=1, sticky='e', padx=8)

        # canvas area
        canvas_frame = tk.Frame(self.main_panel, bg="#000000")
        canvas_frame.grid(row=1, column=0, sticky='nsew')
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="#0d1720", highlightthickness=0)
        self.canvas.grid(sticky='nsew')

        # bottom legend / controls
        legend = tk.Frame(self.main_panel, bg="#0b0b0b")
        legend.grid(row=2, column=0, sticky='ew')
        tk.Label(legend, text=u"W/A/S/D or ↑/←/↓/→ — Mover | P — Pausa | R — Reiniciar | Esc — Volver al menú", font=self.f_small, fg="#BBBBBB", bg="#0b0b0b").pack(pady=6)

        # resize
        self.canvas.bind('<Configure>', self._on_canvas_resize)

    def _start_snake(self):
        self.game_type = 'snake'
        # Usamos un número de obstáculos fijo por defecto (minimización de cambios).
        obst_num = clamp(8, 6, 18)
        self.active_game = JuegoSnake(cols=28, rows=20, velocidad=6.0, obstaculos_cantidad=obst_num)
        self.lbl_game_title.config(text=u"Snake")
        self.status_var.set(u'Snake iniciado — usa W/A/S/D o flechas')

    def _start_tetris(self):
        self.game_type = 'tetris'
        self.active_game = JuegoTetris(cols=10, rows=20, fall_speed=1.0)
        self.lbl_game_title.config(text=u"Tetris")
        self.status_var.set(u'Tetris iniciado — usa W/A/S/D o flechas')

    def _restart(self):
        if not self.active_game:
            return
        self.active_game.reiniciar()
        self.status_var.set(u'Juego reiniciado')

    def _on_key(self, ev):
        # map keys safely
        key = getattr(ev, 'keysym', None)
        mapped = None
        if key in KEYMAP:
            mapped = KEYMAP[key]
        else:
            ch = (getattr(ev, 'char', '') or '').lower()
            mapped = KEYMAP.get(ch, None)
        if mapped == 'esc':
            if messagebox.askyesno(u'Volver', u'¿Deseas volver al menú principal?'):
                self.active_game = None
                self.game_type = None
                self.lbl_game_title.config(text=u'Ningún juego activo')
                self.score_var.set(u'Puntos: 0')
                self.status_var.set(u'Listo — elige Snake o Tetris arriba')
            return
        if mapped == 'r' and self.active_game:
            self.active_game.reiniciar()
            return
        if mapped == 'p' and self.active_game:
            if hasattr(self.active_game, 'pausado'):
                self.active_game.pausado = not self.active_game.pausado
            return
        if self.active_game:
            if self.game_type == 'snake':
                self.active_game.manejar_input(mapped)
            else:
                self.active_game.manejar_input(mapped)

    def _on_canvas_resize(self, ev):
        self.canvas_width = ev.width
        self.canvas_height = ev.height
        self._render()

    def _toggle_crt(self):
        self.crt_enabled = not self.crt_enabled
        if self.crt_enabled:
            self.status_var.set(u'CRT ON')
        else:
            self.status_var.set(u'CRT OFF')

    def _show_info(self):
        msg = (
            u"📘 CONTROLES:\n"
            u"  W/A/S/D o flechas — Mover\n"
            u"  P — Pausa / Reanudar\n"
            u"  R — Reiniciar juego\n"
            u"  Esc — Volver al menú principal\n\n"
            u"📗 REGLAS (resumen):\n"
            u"  Snake — Come comida roja para crecer. Evita chocar contra paredes, tu cuerpo u obstáculos.\n"
            u"  Tetris — Encaja las piezas para formar líneas completas y eliminarlas. No dejes que las piezas lleguen arriba.\n\n"
            u"📙 SIGNIFICADO DE ELEMENTOS (Snake):\n"
            u"  • rojo (normal) — +10 puntos\n"
            u"  • dorada — +50 puntos\n"
            u"  • negra — -50 puntos y encoge 1 segmento\n"
            u"  • morada — Acelera el juego 5 segundos (útil/arriesgado)\n"
            u"  • cyan — Ralentiza el juego 5 segundos (temporario)\n"
            u"  • gris — Obstáculo: bloqueo sólido (chocar = muerte)\n\n"
            u"🎮 Consola Retro 2000 — (sí, '2000 variantes' es sarcasmo) — Hecho por Santiago, Manuel y Juan"
        )
        messagebox.showinfo(u'Controles y Reglas', msg)

    def _loop(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        if self.active_game:
            try:
                self.active_game.paso(dt)
            except Exception as e:
                # evitar que un error rompa el loop; mostrar info mínima
                print "Error en paso:", e
            self._render()
            self.score_var.set(u'Puntos: {}'.format(getattr(self.active_game, "puntaje", 0)))
            # mostrar mensajes
            if hasattr(self.active_game, 'muerto') and self.active_game.muerto:
                self.canvas.create_text(self.canvas_width//2, self.canvas_height//2, text=u'GAME OVER', font=("Courier", 32, 'bold'), fill='#FF6666')
        else:
            self._render_welcome()

        self.after(TICK_MS, self._loop)

    def _render_welcome(self):
        self.canvas.delete('all')
        txt = (
            u"CONSOL A RETRO 2000\n"
            u"Snake & Tetris — Hecho por Santiago, Manuel y Juan\n\n"
            u"Elige Snake o Tetris arriba."
        )
        self.canvas.create_text(self.canvas_width//2, self.canvas_height//3, text=txt, font=("Courier", 22, 'bold'), fill='#88FFCC', justify='center')
        # subtle pattern
        i = 0
        max_range = max(200, self.canvas_width)
        while i < max_range:
            self.canvas.create_line(i, int(self.canvas_height*2/3), i+20, int(self.canvas_height*2/3) + 8, fill='#0f0f12')
            i += 40

    def _render(self):
        self.canvas.delete('all')
        if self.game_type == 'snake' and isinstance(self.active_game, JuegoSnake):
            self._render_snake(self.active_game)
        elif self.game_type == 'tetris' and isinstance(self.active_game, JuegoTetris):
            self._render_tetris(self.active_game)
        if self.crt_enabled:
            self._render_crt()

    def _compute_cell(self, cols, rows):
        cw, ch = max(100, self.canvas_width - 8), max(80, self.canvas_height - 8)
        cell_w = cw // cols
        cell_h = ch // rows
        cell = clamp(min(cell_w, cell_h), CELL_MIN, CELL_MAX)
        return cell

    def _rect_cell(self, ox, oy, cell, x, y, fill='#fff', pad=1):
        x1 = ox + x * cell + pad
        y1 = oy + y * cell + pad
        x2 = ox + (x + 1) * cell - pad
        y2 = oy + (y + 1) * cell - pad
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline='#06120f')

    def _render_snake(self, game):
        cols, rows = game.cols, game.rows
        cell = self._compute_cell(cols, rows)
        total_w, total_h = cols * cell, rows * cell
        ox = (self.canvas_width - total_w) // 2
        oy = (self.canvas_height - total_h) // 2

        # board background + border so limits visible
        self.canvas.create_rectangle(ox-3, oy-3, ox+total_w+3, oy+total_h+3, fill='#071316', outline='#215144', width=3)

        # grid faint
        for i in range(cols + 1):
            x = ox + i * cell
            color_line = '#082014' if (i % 5) else '#123d2b'
            self.canvas.create_line(x, oy, x, oy + total_h, fill=color_line)
        for j in range(rows + 1):
            y = oy + j * cell
            color_line = '#082014' if (j % 5) else '#123d2b'
            self.canvas.create_line(ox, y, ox + total_w, y, fill=color_line)

        # obstacles
        for (x, y) in game.obstaculos:
            self._rect_cell(ox, oy, cell, x, y, fill='#666666', pad=0)

        # comidas
        for c in game.comidas:
            t = c.get('tipo', 'normal')
            if t == 'normal':
                color = '#ff4d4d'
            elif t == 'dorada':
                color = '#FFD700'
            elif t == 'negra':
                color = '#222222'
            elif t == 'velocidad':
                color = '#B347FF'
            elif t == 'lenta':
                color = '#3FE0E0'
            else:
                color = '#ff4d4d'
            self._rect_cell(ox, oy, cell, c['x'], c['y'], fill=color, pad=max(1, cell//6))

        # snake body
        for idx, (x, y) in enumerate(game.cuerpo):
            if idx == len(game.cuerpo) - 1:
                color = '#00d0ff' if not game.muerto else '#ff4444'
            else:
                color = '#70ff9a'
            self._rect_cell(ox, oy, cell, x, y, fill=color, pad=1)

        # HUD: legenda small
        hud_x = ox + 20
        hud_y = oy + total_h + 30
        self.canvas.create_text(hud_x, hud_y, anchor='nw',
                                text=u"Puntos: {0}    Tiempo: {1}s".format(game.puntaje, int(game.tiempo)),
                                font=("Courier", max(10, cell//2)), fill='#DDEFE3')

    def _render_tetris(self, game):
        cols, rows = game.cols, game.rows
        cell = self._compute_cell(cols, rows)
        total_w, total_h = cols * cell, rows * cell
        ox = (self.canvas_width - total_w) // 2
        oy = (self.canvas_height - total_h) // 2

        # board background
        self.canvas.create_rectangle(ox-1, oy-1, ox+total_w+3, oy+total_h+3, fill='#071021', outline='#12304d', width=3)
        colors = ['#FF8A65','#FFD54F','#AED581','#4FC3F7','#BA68C8','#90A4AE','#FFF176']

        # fixed blocks
        for y in range(rows):
            for x in range(cols):
                if game.tablero[y][x]:
                    col = colors[(x+y) % len(colors)]
                    self._rect_cell(ox, oy, cell, x, y, fill=col, pad=1)

        # current piece
        m = game._shape()
        for j, row in enumerate(m):
            for i, v in enumerate(row):
                if v:
                    bx, by = game.px + i, game.py + j
                    if 0 <= bx < cols and 0 <= by < rows:
                        self._rect_cell(ox, oy, cell, bx, by, fill='#FFD27A', pad=1)

        # HUD
        hud_x = ox
        hud_y = oy + total_h + 8
        self.canvas.create_text(hud_x, hud_y, anchor='nw',
                                text=u"Puntos: {0}    Nivel: {1}".format(game.puntaje, game.nivel),
                                font=("Courier", max(10, cell//2)), fill='#DDEFE3')

    def _render_crt(self):
        # scanlines
        y = 0
        while y < self.canvas_height:
            self.canvas.create_line(0, y, self.canvas_width, y, fill='black', width=1)
            y += 2
        # top/bottom vignette
        self.canvas.create_rectangle(0, 0, self.canvas_width, 24, fill='#000000', stipple='gray25', outline='')
        self.canvas.create_rectangle(0, self.canvas_height-24, self.canvas_width, self.canvas_height, fill='#000000', stipple='gray25', outline='')

    def quit(self):
        if messagebox.askokcancel(u'Salir', u'¿Deseas cerrar la Consola Retro 2000?'):
            tk.Tk.quit(self)

# -------------------- Ejecutar --------------------
if __name__ == '__main__':
    app = RetroApp()
    app.mainloop()
