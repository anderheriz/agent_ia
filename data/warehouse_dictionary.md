# warehouse.csv

Dataset sintetico de Google Ads y KPIs de negocio para el proyecto de agente de IA **BI Reporter**.

## Alcance

- Rango de fechas: `2026-06-01` a `2026-07-03`.
- Fecha simulada actual: `2026-06-29`.
- Filas: `9900`.
- Granularidad: una fila por `fecha` + `id_cuenta_google` + `alias`.
- Cuentas de Google Ads por día: 10.
- Aliases por cuenta y día: 30.
- Filas futuras: se mantienen solo como recurso de demo del bootcamp y estan marcadas con `es_futuro_simulado=true`; el agente no debe generar outputs futuros antes de que llegue la fecha.

## Campos principales

- `id_cuenta_google`, `nombre_cuenta_google`: cuenta simulada de Google Ads.
- `id_alias`, `alias`: alias de adquisición simulado.
- `canal_anuncio`: canal de Google Ads, por ejemplo Busqueda, Performance Max, YouTube, Display, Demand Gen, Discovery o UAC.
- `codigo_pais`, `pais`, `region`: segmentación geográfica.
- `inversion`, `conversiones`, `cpa`: métricas de adquisición y coste.
- `arpu_esperado_7d`, `arpu_esperado_30d`, `ltr_esperado_365d`: ARPU esperado a 7 días, 30 días y 365 días. El ARPU a 365 días se interpreta como LTR.
- `roas_7d`, `roas_30d`, `roas_ltr`: ROAS esperado por horizonte de ingresos.
- `beneficio_esperado_30d`, `beneficio_esperado_ltr`: rentabilidad esperada por horizonte.
- `ratio_rentabilidad_ltr`, `margen_beneficio_ltr`: indicadores de rentabilidad a LTR.
- `evento_sintetico`: eventos o anomalías simuladas para que el agente pueda detectar información relevante.

## Nota

Este dataset no contiene datos reales de Basebone. Esta diseñado para imitar un extracto de warehouse de marketing preparado por BI y permitir una demo local del agente sin acceso a sistemas corporativos.


## Ajuste de realismo

El ratio LTR/CPA sintético se ha reescalado para evitar ROAS irreales. Los segmentos quedan aproximadamente entre `0.55x` y `3.10x`, manteniendo diferencias relativas entre canales, aliases y eventos.
