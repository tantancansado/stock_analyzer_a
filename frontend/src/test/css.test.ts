import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Invariantes del CSS que ningún build comprueba.
 *
 * El caso que motivó esto: al quitar un bloque de overrides quedó un selector
 * colgando delante de un comentario —
 *
 *     [data-theme="noir"] [class*="rounded"],
 *     ／* comentario *／
 *     [data-theme="noir"] .glow-border::before { background: gris }
 *
 * El comentario no separa nada, así que la lista de selectores continuaba y la
 * regla se aplicaba a CADA elemento redondeado del tema. Tailwind compiló sin
 * una queja y habría llegado a producción.
 */

const HOJAS = ['index.css', 'nothing-theme.css'].map(f => ({
  nombre: f,
  css: readFileSync(join(__dirname, '..', f), 'utf-8'),
}))

/** Quita comentarios para poder razonar sobre la estructura. */
const sinComentarios = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, '')

describe.each(HOJAS)('$nombre', ({ css }) => {
  it('las llaves cuadran', () => {
    const limpio = sinComentarios(css)
    expect(limpio.split('{').length).toBe(limpio.split('}').length)
  })

  it('ningún selector se queda colgando antes de una llave', () => {
    // `foo, {` significa que algo se borró de la lista de selectores.
    const colgantes = [...sinComentarios(css).matchAll(/,\s*\{/g)]
    expect(colgantes, 'hay una coma justo antes de {').toHaveLength(0)
  })

  it('ninguna regla empieza por coma', () => {
    const colgantes = [...sinComentarios(css).matchAll(/\}\s*,/g)]
    expect(colgantes).toHaveLength(0)
  })
})

describe('deuda de temas', () => {
  // Estos números solo pueden BAJAR. Si un cambio los sube, es que se ha
  // vuelto a perseguir una clase de Tailwind en vez de declarar un token.
  // Medido sobre el CSS SIN comentarios, que es lo único que cuenta.
  //
  //                     !important   [class*=]
  //   punto de partida      35          86      index.css
  //                        118          26      nothing-theme.css
  //   tras quitar la piel Cybertruck del modo claro (295 líneas):
  //                          4          40      index.css
  const TECHO = {
    'index.css':         { important: 4, atributo: 40 },
    'nothing-theme.css': { important: 87, atributo: 13 },
  } as const

  it.each(HOJAS)('$nombre no acumula más !important ni selectores por atributo', ({ nombre, css }) => {
    const techo = TECHO[nombre as keyof typeof TECHO]
    // Sobre el CSS sin comentarios: si no, un comentario que EXPLICA por qué se
    // quitó un `!important` cuenta como si lo hubiera añadido. Pasó al escribir
    // la nota de la voz tipográfica.
    const limpio = sinComentarios(css)
    const important = (limpio.match(/!important/g) ?? []).length
    const atributo = (limpio.match(/\[class\*=/g) ?? []).length
    expect(important, `!important subió a ${important}`).toBeLessThanOrEqual(techo.important)
    expect(atributo, `selectores [class*=] subieron a ${atributo}`).toBeLessThanOrEqual(techo.atributo)
  })
})

/**
 * Los tokens de color son COLORES, no tripletes sueltos.
 *
 * Durante mucho tiempo se declararon como `--primary: 239 84% 57%` y cada uso
 * los envolvía: `hsl(var(--primary))`. Funciona mientras todo el que los toca
 * conozca la convención — y deja de funcionar en cuanto alguien no la conoce.
 *
 * Lo destapó el banco de pruebas de HeroUI: su hoja hace
 * `--button-bg: var(--accent)` y recibía «220 13% 92%», que no es un color, así
 * que la declaración se caía entera y el botón salía sin fondo. Nueve nombres
 * chocaban de frente y envenenaban otros 37 derivados, porque
 * `color-mix(in oklab, var(--success) 15%, transparent)` con un triplete dentro
 * también es inválido. 46 de sus 89 tokens rotos, y ni un aviso en el build.
 *
 * Un triplete es una declaración que no se puede validar y un uso que hay que
 * recordar. Un color se valida solo.
 */
describe('tokens de color', () => {
  const TODAS = ['index.css', 'noir-theme.css', 'nothing-theme.css'].map(f => ({
    nombre: f,
    css: sinComentarios(readFileSync(join(__dirname, '..', f), 'utf-8')),
  }))

  it.each(TODAS)('$nombre no declara ningún token como triplete suelto', ({ css }) => {
    const tripletes = [...css.matchAll(/^[ \t]*(--[a-z0-9-]+):[ \t]*[0-9.]+ [0-9.]+% [0-9.]+%[ \t]*;/gm)]
    expect(
      tripletes.map(m => m[1]),
      'un token de color debe valer hsl(...), no «H S% L%»',
    ).toEqual([])
  })

  it.each(TODAS)('$nombre no envuelve tokens en hsl(var(…))', ({ css }) => {
    const envueltos = [...css.matchAll(/hsl\(\s*var\((--[a-z0-9-]+)\)/g)]
    expect(
      envueltos.map(m => m[1]),
      'el token ya es un color: usar var(--x), y color-mix(…) para la opacidad',
    ).toEqual([])
  })

  // El CSS no es el único sitio donde se consumen: hay estilos en línea en los
  // .tsx (gradientes, colores de gráficas) que hacían lo mismo.
  it('ningún .tsx envuelve tokens en hsl(var(…))', () => {
    const raiz = join(__dirname, '..')
    const fuentes: string[] = []
    const recorrer = (dir: string) => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        const ruta = join(dir, e.name)
        if (e.isDirectory()) recorrer(ruta)
        else if (/\.tsx?$/.test(e.name)) fuentes.push(ruta)
      }
    }
    recorrer(raiz)

    const culpables = fuentes.flatMap(f => {
      const texto = readFileSync(f, 'utf-8')
        .replace(/\/\*[\s\S]*?\*\//g, '')   // comentarios de bloque
        .replace(/^[ \t]*\/\/.*$/gm, '')     // y de línea: documentan el patrón viejo
      return [...texto.matchAll(/hsl\(\s*var\((--[a-z0-9-]+)\)/g)]
        .map(m => `${f.slice(raiz.length + 1)}: ${m[1]}`)
    })
    expect(culpables, 'el token ya es un color: var(--x) a secas').toEqual([])
  })
})

/**
 * La opacidad no es un mando de volumen para el texto.
 *
 * El código usaba `text-muted-foreground/40`, `/50`, `/60`… —veinte posiciones
 * distintas— para decir «esto importa menos». Medido contra los tres fondos de
 * cada tema, NINGUNA llegaba al 4,5:1 que pide WCAG AA para texto pequeño, y no
 * solo en claro: en oscuro `/40` daba 1,78 y `/60` daba 2,65. Nunca se leyó
 * bien; parecía sutil porque nadie lo había medido. 1.058 usos en 59 ficheros.
 *
 * `--muted-foreground` YA es el color callado —está elegido para eso y
 * verificado— y los de paleta (`text-emerald-400`…) apuntan a los roles
 * semánticos. Rebajarlos otra vez encima siempre termina por debajo del mínimo.
 * La jerarquía se marca con tamaño y peso, que no tienen mínimo de contraste.
 *
 * `text-foreground/70` y por encima sí se leen en los dos temas (6,20 el peor),
 * así que esos se permiten.
 */
describe('opacidad sobre el color del texto', () => {
  const PALETA = 'red|emerald|green|blue|amber|yellow|violet|purple|sky|teal|orange|rose|cyan|indigo|pink|fuchsia|lime'

  const fuentes = (() => {
    const raiz = join(__dirname, '..')
    const out: { ruta: string; texto: string }[] = []
    const recorrer = (dir: string) => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        const ruta = join(dir, e.name)
        if (e.isDirectory()) { if (e.name !== 'test') recorrer(ruta) }
        else if (e.name.endsWith('.tsx')) out.push({ ruta: ruta.slice(raiz.length + 1), texto: readFileSync(ruta, 'utf-8') })
      }
    }
    recorrer(raiz)
    return out
  })()

  const buscar = (re: RegExp) =>
    fuentes.flatMap(({ ruta, texto }) =>
      [...texto.matchAll(re)].map(m => `${ruta}: ${m[0]}`))

  it('ningún text-muted-foreground lleva opacidad', () => {
    expect(buscar(/text-muted-foreground\/\d+/g), 'el token ya es el color callado').toEqual([])
  })

  it('ningún text-primary lleva opacidad', () => {
    // /80 se queda en 3,55 en claro y 3,18 en oscuro.
    expect(buscar(/text-primary\/\d+/g)).toEqual([])
  })

  it('ningún color de paleta lleva opacidad', () => {
    // Apuntan a --success/--danger/--warn vía @theme inline; rebajarlos los hunde.
    expect(buscar(new RegExp(`text-(?:${PALETA})-\\d{3}/\\d+`, 'g'))).toEqual([])
  })

  it('text-foreground solo con opacidad ≥70, que es donde se lee', () => {
    const bajos = buscar(/text-foreground\/\d+/g)
      .filter(s => Number(s.match(/\/(\d+)$/)?.[1] ?? 100) < 70)
    expect(bajos, 'por debajo de /70 no llega al mínimo en ningún tema').toEqual([])
  })
})

/**
 * Los velos blancos son idioma del tema oscuro.
 *
 * `bg-white/5` aclara una superficie casi negra. Sobre la tarjeta blanca del
 * modo claro es blanco sobre blanco: no se ve nada. Había 178 —bordes de fila,
 * fondos de panel, estados de pulsación— y en modo claro todos desaparecían.
 *
 * `foreground/N` es el equivalente exacto que se da la vuelta solo: en oscuro
 * `--foreground` es casi blanco (mismo efecto que antes) y en claro casi negro,
 * que es lo que un velo sutil debe ser sobre fondo claro.
 *
 * Se permiten las opacidades altas: `bg-white/90` es la placa de `TickerLogo`,
 * blanca a propósito porque los logos de empresa están dibujados para fondo
 * blanco.
 */
describe('velos de color', () => {
  it('ningún velo sutil usa blanco fijo', () => {
    const raiz = join(__dirname, '..')
    const fuentes: { ruta: string; texto: string }[] = []
    const recorrer = (dir: string) => {
      for (const e of readdirSync(dir, { withFileTypes: true })) {
        const ruta = join(dir, e.name)
        if (e.isDirectory()) { if (e.name !== 'test') recorrer(ruta) }
        else if (e.name.endsWith('.tsx')) fuentes.push({ ruta: ruta.slice(raiz.length + 1), texto: readFileSync(ruta, 'utf-8') })
      }
    }
    recorrer(raiz)

    const culpables = fuentes.flatMap(({ ruta, texto }) =>
      [...texto.matchAll(/(?:[a-z-]+:)?(?:bg|border|from|to|via|ring|divide|outline)-white\/(\d{1,3})\b/g)]
        .filter(m => Number(m[1]) <= 35)
        .map(m => `${ruta}: ${m[0]}`))

    expect(culpables, 'usar foreground/N: se da la vuelta con el tema').toEqual([])
  })
})

/**
 * Los colores semánticos llegan al mínimo legible sobre TODOS los fondos de su
 * tema.
 *
 * Esto no es una regla de estilo, es una trampa con memoria: los cinco colores
 * del modo claro estaban verificados contra el fondo y la tarjeta, y pasaban.
 * Luego `--muted` subió de #f5f5f7 a #e5e5ea —para que los skeletons de carga
 * dejaran de ser blancos sobre blanco— y eso creó un fondo NUEVO, más oscuro,
 * contra el que cuatro de los cinco caían a 4,11-4,34. Nadie tocó los colores;
 * se rompieron solos al mover otra cosa.
 *
 * Por eso el test calcula el contraste en vez de comprobar valores concretos:
 * cualquier cambio en un token de fondo vuelve a evaluarlos todos.
 */
describe('contraste de los colores semánticos', () => {
  const css = readFileSync(join(__dirname, '..', 'index.css'), 'utf-8')

  const hslARgb = (s: string): [number, number, number] => {
    const [h, sa, l] = s.match(/[\d.]+/g)!.map(Number)
    const a = (sa / 100) * Math.min(l / 100, 1 - l / 100)
    const f = (n: number) => {
      const k = (n + h / 30) % 12
      return l / 100 - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))
    }
    return [f(0) * 255, f(8) * 255, f(4) * 255]
  }
  const luminancia = (c: [number, number, number]) => {
    const [r, g, b] = c.map(v => {
      const x = v / 255
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4)
    })
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
  }
  const contraste = (a: string, b: string) => {
    const [la, lb] = [luminancia(hslARgb(a)), luminancia(hslARgb(b))]
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
  }

  /** Los `hsl(...)` declarados dentro de un bloque. */
  const tokensDe = (bloque: string) => {
    const out: Record<string, string> = {}
    for (const m of bloque.matchAll(/^\s*(--[a-z0-9-]+):\s*hsl\(([^)]+)\)\s*;/gm)) {
      if (/var\(/.test(m[2])) continue
      out[m[1]] = m[2].trim()
    }
    return out
  }

  const ROLES = ['--success', '--danger', '--warn', '--info', '--special']
  const SUPERFICIES = ['--background', '--card', '--muted']
  const MINIMO = 4.5   // AA para texto normal, que es casi todo en esta app

  const temas = [
    // El :root del modo claro es el que declara --background; hay otro con las fuentes.
    ['claro', [...css.matchAll(/^:root \{([\s\S]*?)^\}/gm)].map(m => m[1]).find(b => b.includes('--background:'))!],
    ['oscuro', css.match(/^\.dark \{([\s\S]*?)^\}/m)![1]],
  ] as const

  it.each(temas.map(([n, b]) => ({ nombre: n, bloque: b })))(
    'modo $nombre: ningún color semántico baja del mínimo en ningún fondo',
    ({ bloque }) => {
      const t = tokensDe(bloque)
      const fondos = SUPERFICIES.filter(s => t[s])
      expect(fondos.length, 'el tema declara sus superficies').toBeGreaterThan(1)

      const flojos: string[] = []
      for (const rol of ROLES) {
        if (!t[rol]) continue
        for (const fondo of fondos) {
          const c = contraste(t[rol], t[fondo])
          if (c < MINIMO) flojos.push(`${rol} sobre ${fondo}: ${c.toFixed(2)}`)
        }
      }
      expect(flojos, `mínimo ${MINIMO}:1`).toEqual([])
    },
  )
})
