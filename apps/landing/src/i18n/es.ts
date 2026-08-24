// Arcadia — traducción al español (idioma por defecto).
// Los componentes reciben `t: Dict` (tipado derivado de aquí).

const es = {
  meta: {
    title: "ARCADIA — ArcheAge renacido, open source",
    description:
      "Arcadia es una plataforma ArcheAge open source: servidores propios por fases (1.2 hacia 1.7 y más), mundo vivo poblado por IA, contenido propio y web con perfiles, leaderboards y equipamiento.",
  },
  nav: {
    features: "El proyecto",
    servers: "Servidores",
    world: "Mundo vivo",
    compare: "Por qué Arcadia",
    portal: "Fuera del juego",
    benchmarks: "Rendimiento",
    roadmap: "Roadmap",
    download: "Descargar launcher",
  },
  hero: {
    kicker: "La era dorada",
    title: "ARCADIA",
    sub: "Volvemos a encender <strong>ArcheAge 1.2</strong> y ya vamos camino de la <strong>1.7</strong>. Plataforma open source: servidores propios por fases, actualizaciones constantes y contenido único.",
    ctaDownload: "Descargar launcher",
    ctaServers: "Ver servidores",
    chip1label: "Fase actual",
    chip1value: "1.2",
    chip2label: "Siguiente era",
    chip2value: "1.7",
    chip3label: "Mundo vivo",
    chip3value: "24/7",
    note: "Windows · Gratuito · Sin pay-to-win · La beta abre cuando el servidor esté listo.",
  },
  stats: {
    items: [
      { v: "1.2 → 1.7", l: "Primeras eras del viaje" },
      { v: "∞", l: "Contenido propio y updates" },
      { v: "24/7", l: "Mundo con pobladores IA" },
      { v: "100%", l: "Open source LGPL-3" },
    ],
  },
  features: {
    sec: "El proyecto",
    title: "Una plataforma completa, <em>no un emulador más</em>",
    sub: "Arcadia es la capa por encima del emulador: launcher, metaserver, servidores nuevos, plugins y contenido propio — todo open source y conectado.",
    cards: [
      {
        ic: "rocket",
        title: "Launcher todo-en-uno",
        desc: "Elige versión, ve servidores con jugadores en vivo, descarga y parcha el cliente con verificación SHA256 y pulsa Jugar.",
      },
      {
        ic: "cpu",
        title: "Servidores construidos desde cero",
        desc: "Rewrite en Go del login y del juego. Código limpio, testeado y auditable, sin archivos filtrados ni herencias cerradas.",
      },
      {
        ic: "layers",
        title: "Contenido propio y actualizaciones",
        desc: "Nuevas zonas, QoL, balance y eventos propios. El proyecto se actualiza cada semana y tú ves el changelog.",
      },
      {
        ic: "plugin",
        title: "Plugins de la comunidad",
        desc: "SDK público (ArcheaAge.Sdk): cualquiera compila un plugin sin clonar el servidor y lo propone a través del catálogo.",
      },
      {
        ic: "live",
        title: "Mundo vivo con pobladores IA",
        desc: "Ciudades con gente, comercio y rutinas 24/7. Nunca más un mundo vacío: la IA complementa a los jugadores reales.",
      },
      {
        ic: "globe",
        title: "Plataforma web",
        desc: "Registro, perfiles públicos, jugadores online, personajes, leaderboards y equipo verificable desde cualquier navegador.",
        soon: "En desarrollo",
      },
    ],
  },
  servers: {
    sec: "Servidores",
    title: "Multi-versión. <em>Cada fase, una era</em>",
    sub: "Vamos avanzando de versión en versión por fases: jugamos en la fase actual y, cuando llega la siguiente, migramos el mundo entero. Nada se queda congelado.",
    eraTag: "Ruta de versiones",
    eras: [
      { version: "1.2" },
      { version: "1.7" },
      { version: "2.0" },
      { version: "2.9" },
      { version: "3.0" },
    ],
    currentEra: 0,
    phase: "Fase actual: 1.2 · siguiente era: 1.7 — cada salto migra el mundo a la nueva versión.",
    status: { dev: "En desarrollo", soon: "Próximamente", planned: "Planificado" },
    rows: [
      { region: "EU · Norte", name: "Arcadia · Europa", status: "dev", note: "Servidor principal de la fase inicial" },
      { region: "NA · Este", name: "Arcadia · Norteamérica", status: "planned", note: "Cuando la fase esté estable" },
      { region: "APAC", name: "Arcadia · Asia-Pacífico", status: "planned", note: "Por demanda de comunidad" },
    ],
    note: "Aún no hay ningún servidor abierto: la lista se conectará a la telemetría real del Registry cuando llegue la beta. Reino/idioma se perfilarán con la comunidad.",
  },
  world: {
    sec: "Mundo vivo",
    title: "Un mundo que <em>se siente lleno</em>, siempre",
    sub: "La población es el alma de un MMO, y ya no existen los números de 2014. Arcadia lo soluciona con pobladores simulados que pueblan el mundo en tiempo real.",
    points: [
      {
        tag: "Vidas reales",
        t: "Habitantes con rutinas",
        d: "NPC-jugadores con nombres, clases y rutas: van al puerto, comercian, patrullan, descansan. Reaccionan al mundo y al clima.",
      },
      {
        tag: "Economía",
        t: "Mercados y actividad",
        d: "Compran y venden en las subastas, llenan los muelles, mantienen viva la oferta de bienes para los jugadores reales.",
      },
      {
        tag: "Eventos",
        t: "Siempre algo que hacer",
        d: "El calendario del server nunca se vacía: convoyes, tormentas y contiendas programadas por la propia plataforma.",
      },
      {
        tag: "Honestidad",
        t: "Visible y transparente",
        d: "Cada poblador es una entidad del server con su propio estado, y la telemetría pública muestra el mundo habitable y su población.",
      },
    ],
    statLabel: "Población simulada",
    statNote: "El sistema es complementario: cuando llegan jugadores reales, la IA los integra. Nunca compite contra ellos.",
    diaTitle: "Motor de población",
    diaBadge: "24/7",
    diaCore: "Núcleo de IA",
    diaCoreSub: "scheduler por zona · estado y personalidad por entidad",
    nodes: [
      { n: "Subastas vivas", d: "compradores IA pujan, piden y compran en tiempo real", v: "en vivo" },
      { n: "Gente en las calles", d: "se mueven por el mundo y te cruzas con ellos cada rato", v: "24/7" },
      { n: "Combates reales", d: "los que guardan su zona te plantan cara de verdad", v: "reales" },
      { n: "Chat y personalidad", d: "cada uno tiene nombre, charla y carácter propio", v: "—" },
    ],
    diaNote: "No son extras sueltos ni hordas infinitas: cada poblador es una entidad con rutina, personalidad y chat, y puedes verlas en la telemetría pública.",
  },
  compare: {
    sec: "El resto del ecosistema",
    title: "Frente a <em>lo que ya existe</em>",
    sub: "Los rivales de verdad: AAEmu (el emulador de referencia, open source), ArcheRage y AA Classic (dos de los mayores servidores privados). Solo marcamos lo verificable.",
    legend: { yes: "Sí", no: "No", part: "Parcial", na: "—" },
    cols: [
      "Arcadia",
      "AAEmu emulador",
      "ArcheRage",
      "AA Classic",
    ],
    rows: [
      { k: "Código abierto y auditable", d: "Todo el código y las decisiones, a la vista y forkables.", v: ["ok", "ok", "no", "no"] },
      { k: "Servidores sin archivos filtrados", d: "Emulador propio escrito desde cero, sin leaks ni llaves cerradas.", v: ["ok", "ok", "no", "no"] },
      { k: "API de plugins para la comunidad", d: "Cualquiera compila un plugin sin clonar el servidor.", v: ["ok", "no", "no", "no"] },
      { k: "Mundo vivo con habitantes IA", d: "Pobladores simulados 24/7 que llenan ciudades y rutas.", v: ["ok", "no", "no", "no"] },
      { k: "Web: perfiles, leaderboards y equipo", d: "Tu personaje vive también fuera del juego.", v: ["ok", "no", "no", "no"] },
      { k: "Contenido propio y actualizaciones", d: "Zonas, QoL y eventos nuevos con changelog público.", v: ["ok", "part", "ok", "ok"] },
      { k: "Moneda transparente · sin P2W", d: "Postura pública y verificable; compatible con donaciones.", v: ["ok", "na", "no", "part"] },
      { k: "Benchmarks y telemetría públicos", d: "Números del servidor publicados, no promesas.", v: ["ok", "no", "no", "no"] },
    ],
  },
  portal: {
    sec: "Fuera del juego",
    title: "Tu personaje vive <em>también en la web</em>",
    sub: "El mundo no termina en la pantalla. Arcadia expone el estado del server y de tu cuenta desde cualquier navegador.",
    features: [
      {
        t: "Registro y cuentas",
        d: "Crea tu cuenta o inicia sesión desde la web o el launcher. Una sola identidad para todo.",
      },
      {
        t: "Jugadores online en vivo",
        d: "Quién está conectado, en qué zona y desde hace cuánto, alimentado por el heartbeat del server.",
      },
      {
        t: "Ver tus personajes desde fuera",
        d: "Tu roster completo: raza, clase, nivel y progreso visibles sin abrir el juego.",
      },
      {
        t: "Perfiles públicos",
        d: "Público por defecto; tú decides qué se muestra. Comparte tu ficha con la comunidad.",
      },
      {
        t: "Leaderboards",
        d: "Rankings de nivel, PvP, economía y logros. Con estado público desde la web.",
      },
      {
        t: "Equipamiento y build",
        d: "Inspírate y copia equipamientos de otros jugadores. Para saber quién es quién en Arcadia.",
      },
    ],
    note: "Roadmap M2-M3: registro y online en vivo primero, después perfiles completos y leaderboards.",
    profileBadge: "Perfil público",
    profileName: "Kaelen",
    profileSub: "Firran · Reclamante de la Corte",
    profileMeta1: "Nv.",
    profileMeta2: "PvP",
    profileMeta3: "Arena",
    profileGuild: "Gremio",
    profileGear: "Equipamiento",
    profileView: "Ver perfil",
  },
  benchmarks: {
    sec: "Rendimiento",
    title: "Medimos, publicamos, <em>mejoramos</em>",
    sub: "El ecosistema de ArcheAge presume de todo menos de números. Aquí los publicamos: benchmarks, no promesas.",
    items: [
      { v: "8", u: "ms", k: "Presupuesto de tick" },
      { v: "20k", u: "px/s", k: "Paquetes por segundo" },
      { v: "100%", u: "uptime", k: "Objetivo con telemetría" },
      { v: "—", u: "", k: "Capacidad de mundo" },
      { v: "—", u: "", k: "Latencia de red" },
      { v: "—", u: "", k: "Consumo por server" },
    ],
    note: "Primer panel público en M2. Los valores actuales son objetivos de diseño; se medirán en el banco de pruebas y se publicarán.",
  },
  roadmap: {
    sec: "Roadmap",
    title: "El camino del mundo",
    sub: "Milestones del proyecto, de la primera piedra a la operación completa.",
    milestones: [
      { when: "M1", t: "Base operativa", d: "Registry en Go + launcher v1: versión única, servidores con jugadores y descarga de cliente completa.", done: true },
      { when: "M2", t: "Núcleo de juego", d: "Login en Go + núcleo de red del Game, mundo vivo con pobladores IA y primera jugabilidad end-to-end.", done: false },
      { when: "M3", t: "Mundo completo", d: "Zonas, plugins, línea 3.0, content packs y la plataforma web: perfiles, leaderboards y equipamiento.", done: false },
      { when: "M4", t: "Contenido avanzado", d: "Nuevo contenido masivo, edición del mundo, enemigos y eventos globales.", done: false },
    ],
  },
  cta: {
    title: "Tu mundo empieza hoy",
    em: "ARCADIA",
    sub: "Descarga el launcher, crea tu cuenta y entra cuando abra la beta. El código es open source desde ya.",
    launcher: "Descargar launcher",
    register: "Crear cuenta",
    hint: "Arcadia está en desarrollo: los servidores se abren por fases y el roadmap es público.",
  },
  footer: {
    tagline: "Arcadia — plataforma open source para preservar y revivir ArcheAge desde la 1.2 hacia las versiones futuras.",
    col1: "Proyecto",
    links1: [
      { t: "Código y docs", u: "https://github.com/ivan-cavero/ArcheaAge" },
      { t: "Issues y roadmap", u: "https://github.com/ivan-cavero/ArcheaAge/issues" },
      { t: "Licencia LGPL-3", u: "https://github.com/ivan-cavero/ArcheaAge/blob/main/LICENSE" },
    ],
    col2: "Comunidad",
    links2: [
      { t: "Discord", u: "#" },
      { t: "Estado de servidores", u: "/#status" },
    ],
    legal: "Arcadia no está afiliado ni respaldado por XLGAMES ni por ninguno de sus editores. ArcheAge, su cliente, arte, música y marcas son de XLGAMES. Este proyecto es un esfuerzo abierto de interoperabilidad con fines educativos y de preservación, y no distribuye activos del juego.",
    rights: "Código propio bajo LGPL-3. Hecho con Astro.",
  },
};

export type Dict = typeof es;
export default es;