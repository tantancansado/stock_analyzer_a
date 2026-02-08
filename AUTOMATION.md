# 🔄 Automatización del Sistema de Tesis

## Actualización Manual

Para actualizar datos y regenerar tesis:

```bash
./auto_update_theses.sh 50
```

Esto hace:
1. Ejecuta `enrich_5d.py` para actualizar datos fundamentales y entry scores
2. Ejecuta `thesis_generator.py 50` para regenerar tesis del top 50
3. Guarda un log en `logs/auto_update_YYYYMMDD_HHMMSS.log`

## Automatización con Cron (Actualización Diaria)

### Opción 1: Actualización diaria después del cierre del mercado

```bash
# Editar crontab
crontab -e

# Añadir esta línea (ejecuta a las 18:00 de lunes a viernes):
0 18 * * 1-5 cd /Users/ale/Documents/stock_analyzer_a && ./auto_update_theses.sh 50
```

### Opción 2: Actualización semanal (Domingos)

```bash
0 20 * * 0 cd /Users/ale/Documents/stock_analyzer_a && ./auto_update_theses.sh 50
```

## Verificar Actualizaciones

```bash
# Ver último log
ls -lt logs/ | head -5

# Contenido del último log
tail -50 logs/auto_update_*.log
```
