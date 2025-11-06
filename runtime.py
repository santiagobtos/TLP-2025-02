# runtime.py
# coding: utf-8
from __future__ import print_function
import sys
import os
import time
import json
import random

try:
    import msvcrt
    WINDOWS = True
except Exception:
    WINDOWS = False


MAX_COLS = 80
MAX_ROWS = 35

# ----------------- UTILIDADES -----------------
def limpiar():
    os.system('cls' if os.name == 'nt' else 'clear')

def ahora():
    return time.time()

KEYMAP = {
    'w': b'w', 'a': b'a', 's': b's', 'd': b'd',
    'r': b'r', 'p': b'p',
    'esc': b'\x1b',
    'arrow_up': b'\x00H', 'arrow_down': b'\x00P',
    'arrow_left': b'\x00K', 'arrow_right': b'\x00M',
}

def tecla_desde_json(nombre, por_defecto):
    if not isinstance(nombre, str):
        return por_defecto
    nombre = nombre.lower()
    return KEYMAP.get(nombre, por_defecto)

def leer_tecla():
    if not WINDOWS:
        return None
    if not msvcrt.kbhit():
        return None
    k = msvcrt.getch()
    if k in (b'\x00', b'\xe0'):
        k2 = msvcrt.getch()
        return k + k2
    return k.lower()


# ===================== JUEGO SNAKE =====================
class JuegoSnake(object):
    def __init__(self, cfg):
        dims = cfg.get('dimensiones_tablero', {})
        self.cols = int(dims.get('ancho', 20))
        self.rows = int(dims.get('alto', 20))

        vel = cfg.get('velocidad_inicial', {})
        if isinstance(vel, dict):
            self.velocidad = float(vel.get('valor', 5.0))
        else:
            try:
                self.velocidad = float(vel)
            except Exception:
                self.velocidad = 2.5

        c = cfg.get('controles', {})
        self.k_arriba    = tecla_desde_json(c.get('mover_arriba', 'w'), b'w')
        self.k_abajo     = tecla_desde_json(c.get('mover_abajo', 's'), b's')
        self.k_izq       = tecla_desde_json(c.get('mover_izquierda', 'a'), b'a')
        self.k_der       = tecla_desde_json(c.get('mover_derecha', 'd'), b'd')
        self.k_reiniciar = tecla_desde_json(c.get('reiniciar', 'r'), b'r')
        self.k_pausa     = tecla_desde_json(c.get('pausar', 'p'), b'p')
        self.k_salir     = KEYMAP['esc']

        self.reglas = {
            'fin': cfg.get('regla_fin_juego', {}),
            'velocidad': cfg.get('regla_velocidad', {}),
            'comida_normal': cfg.get('manzana_normal', {}),
            'comida_especial': cfg.get('regla_comida_especial', {}),
            'comida_nociva': cfg.get('regla_comida_nosiva', {}),
            'obstaculos': cfg.get('obstaculos', {})
        }

        self.terminar = False
        self.pausado = False
        self._acum = 0.0
        self.reiniciar()

    def reiniciar(self):
        cx, cy = self.cols // 2, self.rows // 2
        self.cuerpo = [(cx - 1, cy), (cx, cy)]
        self.dirx, self.diry = 1, 0
        self.puntaje = 0
        self.muerto = False
        self._fin_natural = False

        self.obstaculos = []
        obs_cfg = self.reglas.get('obstaculos', {})
        if str(obs_cfg.get('activos', 'false')).lower() in ('true', 'si'):
            cant = int(obs_cfg.get('cantidad_maxima', 10))
            for _ in range(cant):
                ox, oy = random.randrange(self.cols), random.randrange(self.rows)
                if (ox, oy) not in self.cuerpo:
                    self.obstaculos.append((ox, oy))

        self.comidas = []
        self._nueva_comida_normal()
        self.tiempo_total = 0.0

    def _posicion_libre(self):
        intentos = 0
        while intentos < 1000:
            x, y = random.randrange(self.cols), random.randrange(self.rows)
            if (x, y) not in self.cuerpo and (x, y) not in self.obstaculos:
                return x, y
            intentos += 1
        return 0, 0

    def _nueva_comida_normal(self):
        manzana = self.reglas.get('comida_normal', {})
        fx, fy = self._posicion_libre()
        self.comidas.append({
            'tipo': 'normal',
            'simbolo': '*',
            'puntos': int(manzana.get('puntuacion', 10)),
            'expira': float(manzana.get('duracion', 10.0)),
            'x': fx, 'y': fy
        })

    def _generar_comidas_especiales(self):
        if random.random() < 0.005:
            esp = self.reglas.get('comida_especial', {})
            fx, fy = self._posicion_libre()
            self.comidas.append({
                'tipo': 'dorada',
                'simbolo': '@',
                'puntos': int(esp.get('puntos_extra', 50)),
                'expira': float(esp.get('duracion', 8.0)),
                'x': fx, 'y': fy
            })
        if random.random() < 0.005:
            nociva = self.reglas.get('comida_nociva', {})
            fx, fy = self._posicion_libre()
            self.comidas.append({
                'tipo': 'negra',
                'simbolo': 'x',
                'puntos': int(nociva.get('puntos_extra', -50)),
                'expira': float(nociva.get('duracion', 10.0)),
                'x': fx, 'y': fy
            })

    def manejar_tecla(self, k):
        if k is None:
            return
        if k == self.k_pausa:
            self.pausado = not self.pausado
            return
        if self.pausado:
            return
        if self.muerto and k not in (self.k_reiniciar, self.k_salir):
            return
        if k == self.k_salir:
            self.terminar = True
            return
        if k == self.k_reiniciar:
            self.reiniciar()
            return
        if k == self.k_arriba and self.diry != 1:
            self.dirx, self.diry = 0, -1
        elif k == self.k_abajo and self.diry != -1:
            self.dirx, self.diry = 0, 1
        elif k == self.k_izq and self.dirx != 1:
            self.dirx, self.diry = -1, 0
        elif k == self.k_der and self.dirx != -1:
            self.dirx, self.diry = 1, 0

    def paso(self, dt):
        if self.terminar:
            return False
        if self.muerto or self.pausado:
            return True

        self.tiempo_total += dt
        self._acum += dt
        paso_t = 1.0 / max(1.0, self.velocidad)
        if self._acum < paso_t:
            return True
        self._acum -= paso_t

        for c in list(self.comidas):
            c['expira'] -= dt
            if c['expira'] <= 0:
                self.comidas.remove(c)
        self._generar_comidas_especiales()

        hx, hy = self.cuerpo[-1]
        nx, ny = hx + self.dirx, hy + self.diry

        conds = self.reglas.get('fin', {}).get('condicion', [])
        if isinstance(conds, str):
            conds = [conds]

        if 'choque_pared' in conds:
            if nx < 0 or nx >= self.cols or ny < 0 or ny >= self.rows:
                self.muerto = True
                return True
        else:
            nx %= self.cols
            ny %= self.rows

        if 'choque_cola' in conds and (nx, ny) in self.cuerpo:
            self.muerto = True
            return True

        if (nx, ny) in self.obstaculos:
            self.muerto = True
            return True

        self.cuerpo.append((nx, ny))

        comida_comida = None
        for c in list(self.comidas):
            if (nx, ny) == (c['x'], c['y']):
                comida_comida = c
                break

        if comida_comida:
            self.puntaje += comida_comida['puntos']
            self.comidas.remove(comida_comida)
            self._nueva_comida_normal()

            vel = self.reglas.get('velocidad', {})
            aum = str(vel.get('aumento_velocidad', 'no')).lower()
            if aum in ('si', 'true'):
                try:
                    mult = float(vel.get('multiplicador_velocidad', 1.1))
                except Exception:
                    mult = 1.1
                self.velocidad *= mult
        else:
            self.cuerpo.pop(0)
        return True

    def dibujar(self):
        buf = []
        buf.append('#' * (self.cols + 2))
        for y in range(self.rows):
            fila = [' '] * self.cols
            for (ox, oy) in self.obstaculos:
                if oy == y:
                    fila[ox] = '#'
            for c in self.comidas:
                if c['y'] == y:
                    fila[c['x']] = c['simbolo']
            for (x, yy) in self.cuerpo:
                if yy == y:
                    fila[x] = 'o'
            hx, hy = self.cuerpo[-1]
            if hy == y:
                fila[hx] = 'X' if self.muerto else 'O'
            buf.append('#' + ''.join(fila) + '#')
        buf.append('#' * (self.cols + 2))
        estado = 'PAUSADO' if self.pausado else 'EN JUEGO'
        buf.append(f'Puntos: {self.puntaje} | Estado: {estado} | Velocidad: {self.velocidad:.2f}')
        buf.append('Controles: W A S D | P pausa | R reiniciar | ESC salir')
        buf.append('Leyenda: * Verde (+10) | @ Dorada (+50) | x Negra (-50) | # Obstáculo')
        return '\n'.join(buf)


# ===================== JUEGO TETRIS (ESQUEMA) =====================
import random

# ===================== TETRIS FUNCIONAL =====================
# ===================== JUEGO TETRIS =====================
import random
import random
import time
import random

class JuegoTetris(object):
    def __init__(self, cfg):
        # Dimensiones
        self.cols = 10
        self.rows = 20

        vel = cfg.get('velocidad_inicial', 1.0)
        try:
            self.caida = float(vel)
        except Exception:
            self.caida = 1.0

        c = cfg.get('controles', {})
        self.k_izq      = tecla_desde_json(c.get('mover_izquierda', 'a'), b'a')
        self.k_der      = tecla_desde_json(c.get('mover_derecha', 'd'), b'd')
        self.k_bajar    = tecla_desde_json(c.get('acelerar_abajo', 's'), b's')
        self.k_rotar    = tecla_desde_json(c.get('evitar_caida', 'w'), b'w')
        self.k_reiniciar= tecla_desde_json(c.get('reiniciar', 'r'), b'r')
        self.k_pausa    = tecla_desde_json(c.get('pausa', 'p'), b'p')  # Nueva tecla de pausa
        self.k_salir    = KEYMAP['esc']

        self.regla_vel   = cfg.get('regla_niveles_velocidad', {})

        self.piezas = []
        for nombre in cfg.get('figuras_disponibles', []):
            data = cfg.get(nombre)
            if not data:
                continue
            rots = []
            for mat in data.get('rotaciones', []):
                rots.append([list(map(int, r)) for r in mat])
            self.piezas.append({'nombre': nombre, 'rot': rots})
        if not self.piezas:
            self.piezas = [{'nombre': 'I', 'rot': [[[1,1,1,1]], [[1],[1],[1],[1]]]}]

        self.terminar = False
        self.pausado = False
        self.reiniciar()

    def reiniciar(self):
        self.tablero = [[0 for _ in range(self.cols)] for __ in range(self.rows)]
        self.puntaje = 0
        self.nivel = 1
        self._acc = 0.0
        self._fin_natural = False
        self._nueva()

    def _nueva(self):
        self.actual = random.choice(self.piezas)
        self.rot = 0
        self.px = self.cols // 2 - 2
        self.py = 0
        if self._colision(self.px, self.py, self.rot):
            self._fin_natural = True
            self.terminar = True

    def _forma(self, r=None):
        i = self.rot if r is None else r
        return self.actual['rot'][i % len(self.actual['rot'])]

    def _colision(self, x, y, r):
        m = self._forma(r)
        for j, fila in enumerate(m):
            for i, v in enumerate(fila):
                if v:
                    bx, by = x + i, y + j
                    if bx < 0 or bx >= self.cols or by < 0 or by >= self.rows:
                        return True
                    if self.tablero[by][bx]:
                        return True
        return False

    def _fijar(self):
        m = self._forma()
        for j, fila in enumerate(m):
            for i, v in enumerate(fila):
                if v:
                    bx, by = self.px + i, self.py + j
                    if 0 <= bx < self.cols and 0 <= by < self.rows:
                        self.tablero[by][bx] = 1
        self._limpiar_lineas()
        self._nueva()

    def _limpiar_lineas(self):
        llenas = [y for y in range(self.rows) if all(self.tablero[y][x] for x in range(self.cols))]
        if not llenas:
            return
        for y in llenas:
            del self.tablero[y]
            self.tablero.insert(0, [0 for _ in range(self.cols)])
        self.puntaje += len(llenas)
        if str(self.regla_vel.get('aumento_velocidad', 'no')).lower() in ('si', 'true'):
            pts = int(self.regla_vel.get('puntos_por_nivel', 1000))
            if pts < 1:
                pts = 1
            self.nivel = max(1, 1 + self.puntaje // pts)

    def manejar_tecla(self, k):
        if k is None:
            return
        if k == self.k_salir:
            self.terminar = True
            return
        if k == self.k_reiniciar:
            self.reiniciar()
            return
        if k == self.k_pausa:
            self.pausado = not self.pausado
            return
        if self.pausado:
            return
        if k == self.k_izq and not self._colision(self.px - 1, self.py, self.rot):
            self.px -= 1
        elif k == self.k_der and not self._colision(self.px + 1, self.py, self.rot):
            self.px += 1
        elif k == self.k_rotar:
            nuevo = (self.rot + 1) % len(self.actual['rot'])
            if not self._colision(self.px, self.py, nuevo):
                self.rot = nuevo
            elif not self._colision(self.px + 1, self.py, nuevo):
                self.px += 1
                self.rot = nuevo
            elif not self._colision(self.px - 1, self.py, nuevo):
                self.px -= 1
                self.rot = nuevo

    def paso(self, dt):
        if self.terminar or self.pausado:
            return True
        mult = 1.0
        if str(self.regla_vel.get('aumento_velocidad', 'no')).lower() in ('si', 'true'):
            try:
                mult = float(self.regla_vel.get('multiplicador_velocidad', 1.2)) ** (self.nivel - 1)
            except Exception:
                mult = 1.0
        cps = self.caida * mult
        if cps < 0.2:
            cps = 0.2
        paso_t = 1.0 / cps

        k = leer_tecla()
        if k == self.k_bajar:
            paso_t *= 0.01  # Caída rápida al mantener S
        elif k is not None:
            self.manejar_tecla(k)

        self._acc += dt
        if self._acc >= paso_t:
            self._acc -= paso_t
            if not self._colision(self.px, self.py + 1, self.rot):
                self.py += 1
            else:
                self._fijar()
        return True

    def dibujar(self):
        buf = []
        buf.append('#' * (self.cols + 2))
        temp = [fila[:] for fila in self.tablero]
        m = self._forma()
        for j, fila in enumerate(m):
            for i, v in enumerate(fila):
                if v:
                    bx, by = self.px + i, self.py + j
                    if 0 <= bx < self.cols and 0 <= by < self.rows:
                        temp[by][bx] = 1
        for y in range(self.rows):
            linea = ''.join('X' if temp[y][x] else ' ' for x in range(self.cols))
            buf.append('#' + linea + '#')
        buf.append('#' * (self.cols + 2))
        estado = "PAUSADO" if self.pausado else f"Puntos: {self.puntaje}"
        buf.append(f'{estado} | W A S D para moverse | R reiniciar | P pausar')
        return '\n'.join(buf)

# ===================== EJECUTAR CUALQUIER JUEGO =====================
def ejecutar(cfg, tipo_juego):
    juego = None
    if tipo_juego == "snake":
        juego = JuegoSnake(cfg)
    elif tipo_juego == "tetris":
        juego = JuegoTetris(cfg)
    else:
        print("Juego desconocido")
        return

    t_anterior = ahora()
    limpiar()
    try:
        while True:
            k = leer_tecla()
            juego.manejar_tecla(k)
            t_actual = ahora()
            dt = t_actual - t_anterior
            t_anterior = t_actual
            if not juego.paso(dt):
                limpiar()
                print('Puntaje final:', getattr(juego, 'puntaje', 0))
                break
            limpiar()
            print(juego.dibujar())
            time.sleep(0.05)
    except KeyboardInterrupt:
        limpiar()
        print('Puntaje final:', getattr(juego, 'puntaje', 0))


# ===================== LECTOR INTERACTIVO =====================
def seleccionar_juego():
    print("=== SELECCIONA UN JUEGO ===")
    print("1. Snake")
    print("2. Tetris")
    eleccion = input("Elige (1 o 2): ").strip()
    if eleccion == "1":
        return "snake.ast.json", "snake"
    elif eleccion == "2":
        return "tetris.ast.json", "tetris"
    else:
        print("Opción inválida. Se usará Snake por defecto.")
        return "snake.ast.json", "snake"

def main():
    archivo_cfg, tipo_juego = seleccionar_juego()
    if not os.path.exists(archivo_cfg):
        print(f"No se encontró el archivo de configuración: {archivo_cfg}")
        sys.exit(1)
    try:
        with open(archivo_cfg, 'r') as f:
            cfg = json.load(f)
    except Exception as e:
        print("Error leyendo JSON:", e)
        sys.exit(1)

    ejecutar(cfg, tipo_juego)

if __name__ == "__main__":
    main()
