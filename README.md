# Web → RSS para lectores online (feedreader.com y similares)

Genera feeds RSS de perfiles públicos de Instagram (vía imginn.com), de imginn.com
y de blogs sin feed, y los publica en URLs públicas de GitHub para que un lector
online como **feedreader.com** los pueda leer y actualizar automáticamente.

## Por qué así

Un lector online no puede leer archivos de tu ordenador: necesita una URL pública.
Este proyecto usa **GitHub Actions** (gratuito) para regenerar los feeds cada
6 horas y servirlos desde `raw.githubusercontent.com`.

## Puesta en marcha (unos 10 minutos, solo una vez)

1. Crea una cuenta en https://github.com si no tienes.
2. Crea un repositorio nuevo **público** (por ejemplo `mis-feeds`).
3. Sube a él estos archivos manteniendo la estructura:
   - `generar_feeds.py`
   - `fuentes.txt`
   - `.github/workflows/feeds.yml`
   (Puedes hacerlo desde la web de GitHub: *Add file → Upload files*.)
4. Edita `fuentes.txt` y pon una URL por línea (Instagram, imginn o blogs).
5. En el repositorio, ve a **Settings → Actions → General → Workflow permissions**
   y marca **Read and write permissions**. Guarda.
6. Ve a la pestaña **Actions**, elige "Generar feeds RSS" y pulsa
   **Run workflow** para la primera ejecución.

En 1-2 minutos aparecerá la carpeta `feeds/` con un `.xml` por cada fuente.

## Añadir los feeds a feedreader.com

Cada archivo tiene una URL pública con este formato:

```
https://raw.githubusercontent.com/TU_USUARIO/mis-feeds/main/feeds/NOMBRE.xml
```

Ejemplo: para `feeds/imginn.com-nasa.xml`:

```
https://raw.githubusercontent.com/juan/mis-feeds/main/feeds/imginn.com-nasa.xml
```

Copia esa URL y añádela en feedreader.com como una suscripción normal.
A partir de ahí, GitHub regenera los feeds cada 6 horas y tu lector verá
las novedades solo.

## Cambiar la frecuencia

Edita `.github/workflows/feeds.yml`, línea `cron`:
- Cada 3 horas: `"0 */3 * * *"`
- Una vez al día a las 7:00 UTC: `"0 7 * * *"`

## Uso local (opcional)

```
pip install requests beautifulsoup4
python generar_feeds.py
```

Genera los XML en `feeds/` a partir de `fuentes.txt`.

## Limitaciones

- Solo perfiles **públicos** de Instagram, y siempre a través de imginn.com
  (Instagram bloquea la lectura directa). Si imginn bloquea peticiones o cambia
  su HTML, ese feed fallará temporalmente; el resto se sigue generando.
- Webs que cargan el contenido con JavaScript no se pueden leer (el script
  solo procesa HTML estático).
- Muchos blogs ya tienen feed propio oculto (p. ej. `sitio.com/feed` en
  WordPress). El script te lo avisa en el registro: en ese caso usa esa URL
  directamente, siempre será más fiable.
