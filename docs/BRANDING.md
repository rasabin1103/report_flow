# Portadas y marca

El título y el logo se pueden definir en JSON, mediante opciones de la CLI o con campos multipart de la API. No se necesita una interfaz web.

## CLI

```sh
reportflow generate --input examples/qa_incidents.csv --config examples/report_config.json --output informe.pdf --title "Informe de calidad" --subtitle "Revisión semestral" --logo examples/demo_logo.png --cover-style full
```

Las mismas opciones de presentación están disponibles en `reportflow validate`. La ruta de `--logo` se usa solo en ejecución local. Los archivos JSON no admiten rutas de logo.

## API

```sh
curl -F "file=@examples/qa_incidents.csv" -F "config=<examples/report_config.json" -F "title=Informe de calidad" -F "subtitle=Revisión semestral" -F "cover_style=full" -F "logo=@examples/demo_logo.png" http://127.0.0.1:8000/api/v1/reports/generate --output informe.pdf
```

El endpoint de validación acepta los mismos campos. `config` sigue siendo un campo de texto JSON obligatorio. Los campos explícitos sustituyen los valores equivalentes del JSON; el archivo `logo` sustituye `branding.logo_base64`.

## Configuración documental

Fragmento para combinar con la configuración de datos y análisis:

```json
{
  "report": {
    "title": "Calidad de producto y seguimiento de incidencias",
    "subtitle": "Informe de gestión · Primer semestre de 2026",
    "author": "Equipo de Calidad",
    "prepared_for": "Comité de Dirección",
    "reporting_period": "Enero – junio de 2026",
    "document_reference": "CAL-2026-S1 · Versión 1.0",
    "confidentiality": "Uso interno",
    "language": "es",
    "cover_style": "full"
  },
  "branding": {
    "company_name": "Mi empresa",
    "primary_color": "#0B1929",
    "accent_color": "#167E91",
    "footer_text": "Mi empresa | Uso interno"
  }
}
```

`compact` comparte la primera página con los indicadores y la síntesis. `full` crea una portada independiente con identidad visual, título ajustado al espacio, ficha documental y alcance numérico. Los metadatos opcionales también quedan registrados en la metodología. La fecha de emisión se genera en UTC. El periodo del informe es una etiqueta aportada por el cliente; el periodo observado en los datos se calcula por separado.

## Logo

Se aceptan PNG y JPEG de hasta 500.000 bytes y 2000 × 2000 píxeles. Se valida el contenido real, se aplica orientación JPEG y se eliminan metadatos; los PNG mantienen su transparencia. El tamaño se ajusta sin alterar la proporción. No se descargan imágenes remotas ni se aceptan rutas en la API.

Para clientes que usan solo JSON, sigue disponible `branding.logo_base64`: bytes PNG/JPEG codificados como base64, sin prefijo de data URI. Si no se aporta logo, se utiliza el nombre de la empresa.

## Ejemplo reproducible

```sh
python scripts/generate_examples.py
python scripts/generate_branded_example.py
```

La segunda orden genera `examples/demo_logo.png`, `examples/branded_config.json` y `examples/branded_report.pdf`. Norte es una marca ficticia de demostración. El informe usa el mismo motor que API/CLI, no una maqueta.
