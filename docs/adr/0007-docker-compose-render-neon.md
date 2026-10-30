# ADR-0007: Docker Compose en local; Render + Neon para la demo

- **Estado:** aceptado
- **Fecha:** 2026-10-26

## Contexto

Se quiere levantar todo con un comando y publicar una demo gratuita; no hay cuenta personal de nube de pago disponible.

## Decisión

**Docker Compose** (API + PostgreSQL + web) en local. Demo en **Render** (API y web, plan gratuito) con **Neon** (PostgreSQL gratuito).

## Consecuencias

La demo «se duerme» sin uso y tarda en despertar; los planes gratuitos pueden cambiar: se verifican al llegar a la fase F6.

## Alternativas consideradas

AWS o Azure (sin cuenta personal disponible), Fly.io (plan gratuito restringido para cuentas nuevas), base gratuita de Render (con vencimiento).

## Actualización (F6, 2026-10-30)

Planes gratuitos verificados el 2026-10-30:

- **Render:** un sitio estático es gratis y no se duerme. Un servicio web gratis (0.1 CPU,
  512 MB) acepta Docker, se duerme tras 15 minutos sin tráfico y tarda alrededor de un minuto
  en despertar; hay 750 horas gratis al mes por cuenta. Su base gratuita vence a los 30 días.
- **Neon:** 0.5 GB por proyecto (la base de la demo ocupa unos 11 MB). Se suspende tras 5
  minutos sin uso, despierta casi al instante y no pierde los datos.

Decisiones para la demo (`render.yaml`):

- **Web como sitio estático** que reenvía `/api` a la API con una regla de reescritura, igual
  que nginx en Docker Compose: misma dirección para las dos, sin CORS. Al no dormirse, la web
  abre al instante y puede avisar mientras la API despierta.
- **La web reintenta** cada 5 segundos, durante unos dos minutos, los errores típicos de una
  API dormida (sin respuesta, 502, 503, 504) y avisa de la espera.
- **Solo lectura** (`TEMPO_READ_ONLY=true`): la API no registra ni decide solicitudes (403).
  Consultar, simular y exportar siguen funcionando. Así nadie llena la base pública de datos
  de prueba; en local todo sigue disponible.
- **Despliegue solo con el CI en verde** (`autoDeployTrigger: checksPass`).
- **Región:** Virginia en Render y AWS US East 1 en Neon, cerca una de otra.
- **PostgreSQL 18:** es la versión del proyecto en Neon; Docker Compose y el CI usan la misma
  para que las pruebas corran contra lo que usa la demo.
- La URL de Neon se guarda como secreto en Render; la API acepta el formato con que Neon la
  entrega (`postgresql://...`).
