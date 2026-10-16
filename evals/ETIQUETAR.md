# Cómo etiquetar tickets reales para medir el router

Objetivo: tener 100 mensajes de clientes con el área correcta, puesta por una persona, para medir si el router (y su umbral de
confianza) funciona con tu canal. Es la única medición que responde por tus clientes; las de Bitext y Banking77 no lo hacen
(`DECISIONES.md` §10 y §14).

## 1. Qué reunir

- **100 mensajes o más** del canal real (WhatsApp Business, correo de soporte, formulario), **sin elegir los fáciles**: toma los
  últimos que llegaron, tal cual. Si eliges a mano los que "se entienden", la medición sale optimista.
- Solo el **texto que escribió el cliente**: sin nombre, sin teléfono, sin respuestas de tu equipo. El conversor anonimiza correos,
  tarjetas, RUC, celulares y DNI, pero es mejor no copiar datos que no hacen falta.
- Una fila por mensaje, en `evals/plantilla-tickets.csv` (columnas `texto,area`). Guárdalo **fuera del repositorio**; el
  conversor deja el resultado en `evals/golden/privado/`, que git ignora.

## 2. Las 12 áreas (usa exactamente estos nombres)

| Área | Qué entra |
|---|---|
| ACCOUNT | crear, borrar o editar cuenta, recuperar contraseña, problemas de registro |
| ORDER | hacer, cambiar, cancelar o rastrear un pedido |
| REFUND | pedir un reembolso, ver su política o su estado |
| INVOICE | pedir o revisar una factura o comprobante |
| CONTACT | pedir hablar con una persona o con atención al cliente |
| PAYMENT | problemas de cobro o medios de pago |
| FEEDBACK | reclamo, queja u opinión sobre el servicio |
| DELIVERY | plazos y opciones de entrega |
| SHIPPING | cambiar o registrar la dirección de envío |
| SUBSCRIPTION | suscripción a boletín o novedades |
| CANCEL | cuánto cuesta cancelar (cargo por cancelación) |
| OTRO | saludos, charla, temas ajenos al negocio, soporte técnico de TI, RR. HH., ventas, producto, incidentes, mensajes ininteligibles |

Si tu negocio usa otras áreas ("Facturación", "Reclamos"), no las renombres: deja tus nombres y escribe un `mapa.json` que las
lleve a una de estas (`{"Facturación": "INVOICE"}`). Un área sin equivalente se mapea a `OTRO` solo si quieres que el router la
mande a una persona.

## 3. Reglas para no ensuciar la medición

1. **Etiqueta lo que el cliente pide**, no lo que crees que le pasó. "Me cobraron dos veces" es PAYMENT aunque termine en reembolso.
2. **Si dudas entre dos áreas**, elige la que resolvería quien atiende primero. Si de verdad no sabes, **déjala en blanco**: el
   conversor la omite. Un caso mal etiquetado miente más que un caso ausente.
3. **Un mensaje, un área.** Si trae dos pedidos, etiqueta el primero.
4. **No uses el router para etiquetar.** Si le preguntas a un modelo y copias su respuesta, mides al modelo contra sí mismo.
5. **Control de calidad:** que una segunda persona etiquete 30 al azar sin ver la primera. Si coinciden en menos del 80 %, las
   reglas no están claras: aclara antes de seguir.

## 4. Medir

```bash
uv run python evals/csv_a_golden.py ~/ruta/mis-tickets.csv --texto texto --area area --mapa ~/ruta/mapa.json --nombre mis-tickets
uv run python evals/evaluar.py --golden evals/golden/privado/golden-mis-tickets.jsonl --grabar
```

Lee tres números: **exactitud dentro de lo automatizado** (la meta es 95 %), **% automatizado** y **destino correcto**. Si la
primera queda bajo 95 %, hay que recalibrar el umbral con estos tickets antes de producción. Enviarlos a TypeSafe para la
cascada es decisión tuya: son datos de tus clientes (`evals/README.md`).
