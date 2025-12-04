# Parser y lexer hecho por:
# Santiago Barrientos, Juan Esteban Rayo y Manuel Gutiérrez

import re
import json
import os

# ---------------------------
# LEXER
# ---------------------------
class Lexer:

    reglas = [
        ('STRING',   r'"[^"]*"|\'[^\']*\''), 
        ('NUMBER',   r'[0-9]+(\.[0-9]+)?'),
        ('BOOLEAN',  r'\b(true|false|si|no)\b'),
        ('IDENT',    r'[A-Za-z_][A-Za-z0-9_]*'),
        ('LBRACE',   r'\{'),
        ('RBRACE',   r'\}'),
        ('LBRACKET', r'\['),
        ('RBRACKET', r'\]'),
        ('COLON',    r':'),
        ('COMMA',    r','),
        ('NEWLINE',  r'\n'),
        ('SKIP',     r'[ \t]+'),
        ('MISMATCH', r'.'),
    ]

    partes = []
    for nombre, regla in reglas:
        partes.append("(?P<{}>{})".format(nombre, regla))

    master_pattern = re.compile("|".join(partes))

    def __init__(self, texto):
        self.texto = texto
        self.tokens = []

    def quitar_comentarios(self):
        resultado = []
        dentro_string = False
        comilla = None
        i = 0

        while i < len(self.texto):
            ch = self.texto[i]

            if not dentro_string and ch in ('"', "'"):
                dentro_string = True
                comilla = ch
                resultado.append(ch)

            elif dentro_string:
                resultado.append(ch)
                if ch == comilla:
                    dentro_string = False
                    comilla = None

            elif ch == '#':
                while i < len(self.texto) and self.texto[i] != '\n':
                    i += 1
                continue

            else:
                resultado.append(ch)

            i += 1

        return "".join(resultado)

    def tokenize(self):
        limpio = self.quitar_comentarios()

        for match in self.master_pattern.finditer(limpio):
            tipo = match.lastgroup
            valor = match.group(0)

            if tipo == 'NEWLINE' or tipo == 'SKIP':
                continue

            if tipo == 'STRING':
                self.tokens.append(('STRING', valor[1:-1]))

            elif tipo == 'NUMBER':
                if '.' in valor:
                    self.tokens.append(('NUMBER', float(valor)))
                else:
                    self.tokens.append(('NUMBER', int(valor)))

            elif tipo == 'BOOLEAN':
                self.tokens.append(('BOOLEAN', valor.lower() in ('true', 'si')))

            elif tipo == 'IDENT':
                self.tokens.append(('IDENTIFIER', valor))

            elif tipo in ('LBRACE','RBRACE','LBRACKET','RBRACKET','COLON','COMMA'):
                self.tokens.append((tipo, valor))

            elif tipo == 'MISMATCH':
                if valor == "=":
                    self.tokens.append(('COLON', ':'))

        return self.tokens


# ---------------------------
# PARSER
# ---------------------------
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def ver(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return (None, None)

    def avanzar(self):
        tok = self.ver()
        self.pos += 1
        return tok

    def esperar(self, tipo):
        if self.ver()[0] == tipo:
            return self.avanzar()[1]
        raise SyntaxError("Se esperaba {}, encontrado {}".format(tipo, self.ver()))

    def parsear(self):
        resultado = {}
        while self.pos < len(self.tokens):
            if self.ver()[0] == 'COMMA':
                self.avanzar()
                continue

            clave = self.parsear_clave()
            if clave is None:
                break

            self.esperar('COLON')
            resultado[clave] = self.parsear_valor()

        return resultado

    def parsear_clave(self):
        tipo, val = self.ver()

        if tipo == 'IDENTIFIER':
            self.avanzar()
            return val

        if tipo == 'LBRACKET':
            self.avanzar()
            nombre = self.esperar('IDENTIFIER')
            self.esperar('RBRACKET')
            return nombre

        return None

    def parsear_valor(self):
        tipo, val = self.ver()

        if tipo in ('STRING', 'NUMBER', 'BOOLEAN'):
            self.avanzar()
            return val

        if tipo == 'LBRACE':
            return self.parsear_objeto()

        if tipo == 'LBRACKET':
            return self.parsear_lista()

        self.avanzar()
        return val

    def parsear_objeto(self):
        self.esperar('LBRACE')
        obj = {}

        while True:
            if self.ver()[0] == 'RBRACE':
                self.avanzar()
                break

            if self.ver()[0] == 'COMMA':
                self.avanzar()
                continue

            clave = self.parsear_clave()
            if clave is None:
                raise SyntaxError("Se esperaba clave dentro de {}")

            self.esperar('COLON')
            obj[clave] = self.parsear_valor()

        return obj

    def parsear_lista(self):
        self.esperar('LBRACKET')
        lista = []

        while True:
            if self.ver()[0] == 'RBRACKET':
                self.avanzar()
                break

            if self.ver()[0] == 'COMMA':
                self.avanzar()
                continue

            lista.append(self.parsear_valor())

        return lista


# ---------------------------
# GUARDAR AST
# ---------------------------
def save_ast_to_file(ast, filepath):
    try:
        with open(filepath, 'w') as file:
            json.dump(ast, file, indent=4)
        print("AST guardado exitosamente en '{}'".format(filepath))
    except Exception as e:
        print("Error al guardar archivo: {}".format(e))


# ---------------------------
# PROGRAMA PRINCIPAL
# ---------------------------
archivos = ["snake.brik", "tetris.brik"]

for ruta in archivos:

    if not os.path.exists(ruta):
        print("No se encontró el archivo: {}".format(ruta))
        continue

    with open(ruta, 'r') as f:
        texto = f.read()

    lexer = Lexer(texto)
    tokens = lexer.tokenize()

    print("\n=== Tokens para {} ===".format(ruta))
    for i, tok in enumerate(tokens):
        print("{:03d}: {}".format(i, tok))

    parser = Parser(tokens)
    resultado = parser.parsear()

    print("\nResultado en JSON :")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    save_ast_to_file(resultado, ruta + ".ast.json")
