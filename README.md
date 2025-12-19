# Black Stories AI

Juego de Black Stories donde modelos de IA compiten para resolver misterios.

## Requisitos

- Python 3.10 o superior
- `uv` (gestor de paquetes)

## Instalación

```bash
# Instalar dependencias
uv sync
```

## Configuración

Copia el archivo `.env.example` a `.env` y configura tus claves API:

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:
- `GOOGLE_API_KEY`: Tu clave API de Google Gemini
- `OLLAMA_BASE_URL`: URL base de Ollama (por defecto: http://localhost:11434)

## Ejecución

Para ejecutar el juego:

```bash
uv run main.py
```

O usando el script definido:

```bash
uv run blackstory
```

## Características

- Interfaz de terminal con Rich
- Interfaz gráfica con CustomTkinter
- Soporte para múltiples proveedores de IA (Google Gemini, Ollama)
- Modo moderador humano
- Registro de conversaciones
